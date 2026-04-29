"""OSINT Harvester service (Phase 9).

Extracts open-source intelligence artifacts from one or more web pages:
emails, social handles, phones, cloud links, optionally secret leaks, and
user supplied custom regex matches.

BFS crawl mode reuses url_normalizer primitives (normalize_url, same_domain)
and the link_extractor for HTML parsing. Page fetch is delegated to
http_factory.build_client(). The crawl logic itself is implemented locally,
NOT copied from url_crawler.UrlCrawlerService, because the OSINT use-case
does not need crawl_node persistence, robots, frontier resume, etc. — it
only needs in-memory BFS over a small page count.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import math
import re
from collections import Counter
from typing import Optional
from urllib.parse import urljoin

from app.services.event_bus import event_bus
from app.services.http_factory import build_client
from app.services.link_extractor import extract as extract_metadata
from app.services.url_normalizer import normalize_url, same_domain

logger = logging.getLogger("pyscrapr.osint")


# ─── Pre-compiled regex patterns ───────────────────────────────────────────

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_EMAIL_OBFUSCATED_RE = re.compile(
    r"\b([\w.+-]+)\s*[\[\(]\s*at\s*[\]\)]\s*([\w-]+(?:\s*[\[\(]\s*dot\s*[\]\)]\s*[\w-]+)+)\b",
    re.IGNORECASE,
)
_DOT_OBF_RE = re.compile(r"\s*[\[\(]\s*dot\s*[\]\)]\s*", re.IGNORECASE)

_IMG_EXT_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|bmp|ico|woff2?|ttf|eot)$", re.IGNORECASE)

_SOCIAL_PATTERNS: dict[str, re.Pattern] = {
    "twitter": re.compile(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,15})\b"),
    "linkedin": re.compile(r"linkedin\.com/in/([A-Za-z0-9_-]+)"),
    "facebook": re.compile(r"facebook\.com/([A-Za-z0-9.]{5,})"),
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]{1,30})"),
    "github": re.compile(r"github\.com/([A-Za-z0-9-]+)(?=[/\s\"'<>]|$)"),
    "youtube": re.compile(r"youtube\.com/(?:@|c/|channel/|user/)([A-Za-z0-9_.-]+)"),
    "tiktok": re.compile(r"tiktok\.com/@([A-Za-z0-9_.]+)"),
    "telegram": re.compile(r"(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)"),
    "discord": re.compile(r"discord\.gg/([A-Za-z0-9]+)"),
}
# At-handle (loose, last-resort). Skip if followed by a domain (likely email).
_AT_HANDLE_RE = re.compile(r"(?<![A-Za-z0-9_])@([A-Za-z0-9_]{3,15})\b(?!\.[A-Za-z])")

_PHONE_ID_RE = re.compile(r"(?:\+?62|0)8\d{1,3}[-\s]?\d{3,4}[-\s]?\d{3,5}")

_CLOUD_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("s3", re.compile(r"[A-Za-z0-9.\-_]{3,63}\.s3[.\-][A-Za-z0-9\-]+\.amazonaws\.com[\w/.\-]*")),
    ("s3", re.compile(r"s3://[A-Za-z0-9.\-_]+(?:/[\w./\-]*)?")),
    ("gdrive", re.compile(r"drive\.google\.com/(?:file|drive)/[\w/\-]+")),
    ("gdocs", re.compile(r"docs\.google\.com/(?:document|spreadsheets|presentation)/d/[\w\-]+")),
    ("dropbox", re.compile(r"dropbox\.com/(?:s|sh)/[\w./?=&\-]+")),
    ("pastebin", re.compile(r"pastebin\.com/[A-Za-z0-9]{6,}")),
    ("gist", re.compile(r"gist\.github\.com/[\w/\-]+")),
]

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("stripe_live_secret", re.compile(r"\bsk_live_[A-Za-z0-9]{24,}\b")),
    ("stripe_live_pub", re.compile(r"\bpk_live_[A-Za-z0-9]{24,}\b")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36}\b")),
    ("hex_high_entropy", re.compile(r"\b[a-fA-F0-9]{40,}\b")),
]

_FALSE_POS_CONTEXT = ("example", "xxxxx", "placeholder", "your_", "sample", "dummy")


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _snippet(content: str, start: int, end: int, span: int = 80) -> str:
    a = max(0, start - span // 2)
    b = min(len(content), end + span // 2)
    s = content[a:b].replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", s).strip()


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _redact(s: str) -> str:
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + ("*" * (len(s) - 8)) + s[-4:]


# ─── Extractors ────────────────────────────────────────────────────────────


def extract_emails(html: str, source_url: str) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for m in _EMAIL_RE.finditer(html):
        val = m.group(0).strip().rstrip(".")
        low = val.lower()
        if low in seen:
            continue
        if _IMG_EXT_RE.search(low):
            continue
        # Skip if entire local part looks like a hash artifact (e.g., font hashes)
        local, _, _ = low.partition("@")
        if len(local) > 64:
            continue
        seen.add(low)
        out.append({
            "category": "emails",
            "subcategory": None,
            "value": low,
            "source_url": source_url,
            "context_snippet": _snippet(html, m.start(), m.end()),
        })

    # Obfuscated forms: name [at] domain [dot] com
    for m in _EMAIL_OBFUSCATED_RE.finditer(html):
        local = m.group(1).strip()
        domain_obf = m.group(2).strip()
        domain = _DOT_OBF_RE.sub(".", domain_obf)
        candidate = f"{local}@{domain}".lower()
        if not _EMAIL_RE.fullmatch(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        out.append({
            "category": "emails",
            "subcategory": "obfuscated",
            "value": candidate,
            "source_url": source_url,
            "context_snippet": _snippet(html, m.start(), m.end()),
        })
    return out


def extract_socials(html: str, source_url: str) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for platform, pat in _SOCIAL_PATTERNS.items():
        for m in pat.finditer(html):
            handle = next((g for g in m.groups() if g), "").strip().lower()
            if not handle:
                continue
            # Skip well-known non-handle paths
            if platform == "twitter" and handle in {"share", "intent", "home", "search"}:
                continue
            if platform == "github" and handle in {"login", "search", "marketplace", "topics", "trending"}:
                continue
            key = (platform, handle)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "category": "socials",
                "subcategory": platform,
                "value": handle,
                "source_url": source_url,
                "context_snippet": _snippet(html, m.start(), m.end()),
            })
    # Loose @handle markers (lower confidence)
    for m in _AT_HANDLE_RE.finditer(html):
        h = m.group(1).lower()
        key = ("twitter", h)
        if key in seen:
            continue
        # Heuristic: skip if char before is a letter (would be a word like sm@spam)
        seen.add(key)
        out.append({
            "category": "socials",
            "subcategory": "twitter",
            "value": h,
            "source_url": source_url,
            "context_snippet": _snippet(html, m.start(), m.end()),
        })
    return out


def extract_phones(html: str, source_url: str, country: str = "ID") -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for m in _PHONE_ID_RE.finditer(html):
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("0"):
            normalized = "+62" + digits[1:]
        elif digits.startswith("62"):
            normalized = "+" + digits
        else:
            normalized = "+" + digits
        if not (10 <= len(digits) <= 14):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append({
            "category": "phones",
            "subcategory": country.lower(),
            "value": normalized,
            "source_url": source_url,
            "context_snippet": _snippet(html, m.start(), m.end()),
        })
    return out


def extract_cloud_artifacts(html: str, source_url: str) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for sub, pat in _CLOUD_PATTERNS:
        for m in pat.finditer(html):
            val = m.group(0).strip().rstrip(".,)\"'")
            key = (sub, val.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "category": "cloud",
                "subcategory": sub,
                "value": val,
                "source_url": source_url,
                "context_snippet": _snippet(html, m.start(), m.end()),
            })
    return out


def extract_secrets(content: str, source_url: str) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for sub, pat in _SECRET_PATTERNS:
        for m in pat.finditer(content):
            val = m.group(0)
            ctx = _snippet(content, m.start(), m.end()).lower()
            if any(fp in ctx for fp in _FALSE_POS_CONTEXT):
                continue
            if sub == "hex_high_entropy":
                if _shannon_entropy(val) < 4.0:
                    continue
                # Skip very long hex that's likely a SHA chain or font subresource hash inline
                if len(val) > 128:
                    continue
            key = (sub, val.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "category": "secrets",
                "subcategory": sub,
                "value": _redact(val),
                "source_url": source_url,
                "context_snippet": _snippet(content, m.start(), m.end()),
            })
    return out


def extract_custom(html: str, source_url: str, patterns: list[str]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for idx, raw in enumerate(patterns):
        try:
            pat = re.compile(raw)
        except re.error as e:
            logger.warning("custom pattern #%d invalid: %s (%s)", idx, raw, e)
            continue
        try:
            for m in pat.finditer(html):
                val = m.group(0)
                if len(val) > 500:
                    continue
                key = (idx, val.lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "category": "custom",
                    "subcategory": f"pattern_{idx}",
                    "value": val,
                    "source_url": source_url,
                    "context_snippet": _snippet(html, m.start(), m.end()),
                })
        except Exception as e:
            logger.warning("custom pattern #%d runtime error: %s", idx, e)
            continue
    return out


# ─── Orchestrator ──────────────────────────────────────────────────────────


_DEFAULT_FILTERS = {
    "emails": True,
    "socials": True,
    "cloud": True,
    "phones": True,
    "secrets": False,
    "custom": True,
}


class OSINTHarvester:
    async def harvest(
        self,
        job_id: str,
        url: str,
        max_depth: int = 0,
        max_pages: int = 50,
        stay_on_domain: bool = True,
        filters: Optional[dict[str, bool]] = None,
        custom_patterns: Optional[list[str]] = None,
    ) -> dict:
        flt = {**_DEFAULT_FILTERS, **(filters or {})}
        custom_patterns = custom_patterns or []
        start_url = normalize_url(url, strip_tracking=True)
        started_at = _now_iso()
        findings: list[dict] = []
        seen_pages: set[str] = set()
        pages_crawled = 0

        await event_bus.publish(job_id, {"type": "status", "status": "running"})

        try:
            async with build_client(target_url=start_url, timeout=30) as client:
                # BFS frontier (in-memory)
                frontier: list[tuple[str, int]] = [(start_url, 0)]
                while frontier and pages_crawled < max_pages:
                    cur_url, cur_depth = frontier.pop(0)
                    if cur_url in seen_pages:
                        continue
                    seen_pages.add(cur_url)

                    if stay_on_domain and not same_domain(cur_url, start_url):
                        continue

                    await event_bus.publish(job_id, {
                        "type": "log",
                        "message": f"Fetching: {cur_url}",
                    })

                    html = ""
                    try:
                        r = await client.get(cur_url)
                        ctype = r.headers.get("content-type", "")
                        if 200 <= r.status_code < 300 and "html" in ctype.lower():
                            html = r.text
                        elif 200 <= r.status_code < 300 and "text" in ctype.lower():
                            html = r.text
                    except Exception as e:
                        await event_bus.publish(job_id, {
                            "type": "log",
                            "message": f"Fetch error {cur_url}: {e}",
                        })
                        continue

                    pages_crawled += 1

                    if html:
                        # Run extractors per filter
                        if flt.get("emails", True):
                            findings.extend(extract_emails(html, cur_url))
                        if flt.get("socials", True):
                            findings.extend(extract_socials(html, cur_url))
                        if flt.get("phones", True):
                            findings.extend(extract_phones(html, cur_url))
                        if flt.get("cloud", True):
                            findings.extend(extract_cloud_artifacts(html, cur_url))
                        if flt.get("secrets", False):
                            findings.extend(extract_secrets(html, cur_url))
                        if flt.get("custom", True) and custom_patterns:
                            findings.extend(extract_custom(html, cur_url, custom_patterns))

                        # Enqueue child links if BFS crawling
                        if max_depth > 0 and cur_depth < max_depth:
                            try:
                                meta = extract_metadata(html, cur_url)
                                for link in meta.links:
                                    norm = normalize_url(link, strip_tracking=True)
                                    if norm in seen_pages:
                                        continue
                                    if stay_on_domain and not same_domain(norm, start_url):
                                        continue
                                    frontier.append((norm, cur_depth + 1))
                            except Exception as e:
                                logger.debug("link extract failed for %s: %s", cur_url, e)

                    await event_bus.publish(job_id, {
                        "type": "progress",
                        "pages_crawled": pages_crawled,
                        "findings_count": len(findings),
                    })

        except Exception as e:
            logger.exception("OSINT harvest failed: %s", e)
            await event_bus.publish(job_id, {"type": "error", "message": str(e)})
            raise

        # Stats per category
        stats = {"emails": 0, "socials": 0, "cloud": 0, "phones": 0, "secrets": 0, "custom": 0}
        for f in findings:
            c = f.get("category", "")
            if c in stats:
                stats[c] += 1

        report = {
            "job_id": job_id,
            "url": start_url,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "pages_crawled": pages_crawled,
            "findings": findings,
            "stats": stats,
        }
        await event_bus.publish(job_id, {"type": "done", "stats": stats, "pages_crawled": pages_crawled})
        return report


_harvester: Optional[OSINTHarvester] = None


def get_harvester() -> OSINTHarvester:
    global _harvester
    if _harvester is None:
        _harvester = OSINTHarvester()
    return _harvester
