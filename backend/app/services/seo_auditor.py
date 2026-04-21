"""SEO auditor - inspects on-page SEO signals and produces an issue list."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.seo_auditor")


_SEVERITY_WEIGHT = {"error": 15, "warning": 7, "info": 2}


def _text_len(s: str | None) -> int:
    return len(s.strip()) if s else 0


class SeoAuditor:
    async def audit(self, url: str, timeout: int = 20) -> dict[str, Any]:
        async with build_client(timeout=timeout, target_url=url) as client:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as e:
                logger.warning("SEO fetch failed: %s", e)
                raise
            final_url = str(resp.url)
            status_code = resp.status_code
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        def _meta(name: str, attr: str = "name") -> str | None:
            tag = soup.find("meta", attrs={attr: re.compile(f"^{re.escape(name)}$", re.I)})
            if tag and tag.get("content"):
                return tag["content"].strip()
            return None

        description = _meta("description")
        robots = _meta("robots")
        viewport = _meta("viewport")
        canonical_tag = soup.find("link", rel=lambda v: v and "canonical" in v)
        canonical = canonical_tag.get("href") if canonical_tag else None
        html_tag = soup.find("html")
        lang = html_tag.get("lang") if html_tag else None

        og: dict[str, str] = {}
        twitter: dict[str, str] = {}
        for tag in soup.find_all("meta"):
            prop = (tag.get("property") or "").lower()
            name = (tag.get("name") or "").lower()
            content = tag.get("content") or ""
            if prop.startswith("og:"):
                og[prop] = content
            elif name.startswith("twitter:"):
                twitter[name] = content

        def _collect(tag_name: str) -> list[str]:
            return [t.get_text(" ", strip=True) for t in soup.find_all(tag_name)]

        h1_list = _collect("h1")
        h2_list = _collect("h2")
        h3_list = _collect("h3")
        h4_list = _collect("h4")

        imgs = soup.find_all("img")
        img_total = len(imgs)
        img_no_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())

        host = urlparse(final_url).netloc.lower()
        a_internal = 0
        a_external = 0
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            try:
                h = urlparse(href).netloc.lower()
            except Exception:
                continue
            if not h or h == host:
                a_internal += 1
            else:
                a_external += 1

        structured_types: list[str] = []
        for s in soup.find_all("script", {"type": "application/ld+json"}):
            txt = s.string or ""
            for m in re.finditer(r'"@type"\s*:\s*"([^"]+)"', txt):
                structured_types.append(m.group(1))
        for tag in soup.find_all(attrs={"itemtype": True}):
            structured_types.append(tag.get("itemtype"))

        body_text = soup.body.get_text(" ", strip=True) if soup.body else soup.get_text(" ", strip=True)
        word_count = len(body_text.split())

        favicon_tag = soup.find("link", rel=lambda v: v and "icon" in v.lower()) if soup else None
        has_favicon = favicon_tag is not None

        issues: list[dict[str, str]] = []

        def _add(severity: str, code: str, message: str) -> None:
            issues.append({"severity": severity, "code": code, "message": message})

        if not title:
            _add("error", "missing_title", "Tag title tidak ditemukan")
        else:
            tl = _text_len(title)
            if tl < 30 or tl > 65:
                _add("warning", "title_length", f"Panjang title {tl} karakter, idealnya 30-65")
        if not description:
            _add("error", "missing_description", "Meta description tidak ditemukan")
        else:
            dl = _text_len(description)
            if dl < 70 or dl > 160:
                _add("warning", "desc_length", f"Panjang description {dl} karakter, idealnya 70-160")
        if not canonical:
            _add("error", "missing_canonical", "Canonical URL tidak ditemukan")
        if len(h1_list) == 0:
            _add("error", "no_h1", "Halaman tidak memiliki H1")
        elif len(h1_list) > 1:
            _add("error", "multiple_h1", f"Ada {len(h1_list)} H1, idealnya hanya 1")
        if img_no_alt > 0:
            _add("warning", "img_alt_missing", f"{img_no_alt} dari {img_total} gambar tidak punya atribut alt")
        if not viewport:
            _add("warning", "missing_viewport", "Meta viewport tidak ditemukan")
        if not structured_types:
            _add("info", "no_structured_data", "Tidak ada structured data (JSON-LD atau microdata)")
        if not og:
            _add("info", "no_og_tags", "Tidak ada Open Graph tags")
        if not has_favicon:
            _add("info", "no_favicon", "Favicon tidak ditemukan")
        if not lang:
            _add("warning", "no_lang", "Atribut lang pada tag html tidak di-set")

        penalty = sum(_SEVERITY_WEIGHT.get(i["severity"], 0) for i in issues)
        score = max(0, min(100, 100 - penalty))

        return {
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "score": score,
            "title": title,
            "title_length": _text_len(title),
            "description": description,
            "description_length": _text_len(description),
            "canonical": canonical,
            "robots": robots,
            "lang": lang,
            "viewport": viewport,
            "has_favicon": has_favicon,
            "og": og,
            "twitter": twitter,
            "h1": h1_list,
            "h2": h2_list,
            "h1_count": len(h1_list),
            "h2_count": len(h2_list),
            "h3_count": len(h3_list),
            "h4_count": len(h4_list),
            "img_total": img_total,
            "img_without_alt": img_no_alt,
            "a_internal": a_internal,
            "a_external": a_external,
            "structured_data": structured_types,
            "word_count": word_count,
            "issues": issues,
        }


_singleton: SeoAuditor | None = None


def get_auditor() -> SeoAuditor:
    global _singleton
    if _singleton is None:
        _singleton = SeoAuditor()
    return _singleton
