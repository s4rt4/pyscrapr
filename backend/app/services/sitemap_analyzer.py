"""Sitemap analyzer: auto-detect sitemap, parse, aggregate stats.

Supports plain XML and gzipped (.xml.gz) sitemaps, sitemap-index with sub-sitemaps
(recursion bounded to depth 2, max 50 sub-sitemaps), and robots.txt discovery.
"""
from __future__ import annotations

import gzip
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from lxml import etree  # type: ignore

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.sitemap")

MAX_SUB_SITEMAPS = 50
MAX_DEPTH = 2
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def _site_root(url: str) -> str:
    p = urlparse(url if "://" in url else f"https://{url}")
    return f"{p.scheme}://{p.netloc}"


def _is_sitemap_url(url: str) -> bool:
    u = url.lower()
    return u.endswith(".xml") or u.endswith(".xml.gz") or "sitemap" in u


async def _fetch_bytes(client: httpx.AsyncClient, url: str) -> Optional[bytes]:
    try:
        resp = await client.get(url)
    except httpx.HTTPError as e:
        logger.debug("sitemap fetch error %s: %s", url, e)
        return None
    if resp.status_code != 200:
        return None
    return resp.content


def _maybe_gunzip(url: str, data: bytes) -> bytes:
    if url.lower().endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except Exception as e:
            logger.warning("gunzip failed for %s: %s", url, e)
            return data
    return data


async def _discover(client: httpx.AsyncClient, input_url: str) -> tuple[Optional[str], str]:
    """Return (sitemap_url, source) where source in {direct, guessed, robots}."""
    if _is_sitemap_url(input_url):
        return input_url, "direct"

    root = _site_root(input_url)

    # 1) /sitemap.xml
    cand = f"{root}/sitemap.xml"
    data = await _fetch_bytes(client, cand)
    if data and (b"<urlset" in data[:2000] or b"<sitemapindex" in data[:2000] or data[:2] == b"\x1f\x8b"):
        return cand, "guessed"

    # 2) /sitemap_index.xml
    cand = f"{root}/sitemap_index.xml"
    data = await _fetch_bytes(client, cand)
    if data and (b"<sitemapindex" in data[:2000] or b"<urlset" in data[:2000]):
        return cand, "guessed"

    # 3) robots.txt
    robots_url = f"{root}/robots.txt"
    data = await _fetch_bytes(client, robots_url)
    if data:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        for line in text.splitlines():
            s = line.strip()
            if s.lower().startswith("sitemap:"):
                return s.split(":", 1)[1].strip(), "robots"

    return None, "not_found"


def _parse_sitemap(data: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Return (kind, entries). kind in {urlset, sitemapindex, unknown}."""
    try:
        root = etree.fromstring(data)
    except Exception as e:
        logger.warning("sitemap xml parse failed: %s", e)
        return "unknown", []

    tag = etree.QName(root.tag).localname if root.tag else ""
    entries: list[dict[str, Any]] = []

    if tag == "sitemapindex":
        for sm in root.findall("sm:sitemap", NS) + root.findall("sitemap"):
            loc_el = sm.find("sm:loc", NS)
            if loc_el is None:
                loc_el = sm.find("loc")
            lastmod_el = sm.find("sm:lastmod", NS)
            if lastmod_el is None:
                lastmod_el = sm.find("lastmod")
            if loc_el is not None and loc_el.text:
                entries.append({
                    "loc": loc_el.text.strip(),
                    "lastmod": (lastmod_el.text or "").strip() if lastmod_el is not None and lastmod_el.text else None,
                })
        return "sitemapindex", entries

    if tag == "urlset":
        for u in root.findall("sm:url", NS) + root.findall("url"):
            loc_el = u.find("sm:loc", NS)
            if loc_el is None:
                loc_el = u.find("loc")
            if loc_el is None or not loc_el.text:
                continue
            lastmod_el = u.find("sm:lastmod", NS)
            if lastmod_el is None:
                lastmod_el = u.find("lastmod")
            changefreq_el = u.find("sm:changefreq", NS)
            if changefreq_el is None:
                changefreq_el = u.find("changefreq")
            priority_el = u.find("sm:priority", NS)
            if priority_el is None:
                priority_el = u.find("priority")
            entries.append({
                "loc": loc_el.text.strip(),
                "lastmod": (lastmod_el.text or "").strip() if lastmod_el is not None and lastmod_el.text else None,
                "changefreq": (changefreq_el.text or "").strip() if changefreq_el is not None and changefreq_el.text else None,
                "priority": (priority_el.text or "").strip() if priority_el is not None and priority_el.text else None,
            })
        return "urlset", entries

    return "unknown", entries


def _parse_lastmod(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    # Try a few common formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # ISO fallback
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _compute_stats(urls: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    buckets = {"24h": 0, "7d": 0, "30d": 0, "90d": 0, "older": 0, "unknown": 0}
    prio = {"0.0-0.2": 0, "0.3-0.5": 0, "0.6-0.8": 0, "0.9-1.0": 0, "unknown": 0}
    path_counter: Counter[str] = Counter()
    domains: set[str] = set()

    for u in urls:
        lm = _parse_lastmod(u.get("lastmod"))
        if lm is None:
            buckets["unknown"] += 1
        else:
            delta = now - lm
            if delta <= timedelta(hours=24):
                buckets["24h"] += 1
            elif delta <= timedelta(days=7):
                buckets["7d"] += 1
            elif delta <= timedelta(days=30):
                buckets["30d"] += 1
            elif delta <= timedelta(days=90):
                buckets["90d"] += 1
            else:
                buckets["older"] += 1

        p = u.get("priority")
        try:
            pv = float(p) if p else None
        except ValueError:
            pv = None
        if pv is None:
            prio["unknown"] += 1
        elif pv <= 0.2:
            prio["0.0-0.2"] += 1
        elif pv <= 0.5:
            prio["0.3-0.5"] += 1
        elif pv <= 0.8:
            prio["0.6-0.8"] += 1
        else:
            prio["0.9-1.0"] += 1

        loc = u.get("loc") or ""
        try:
            pr = urlparse(loc)
            domains.add(pr.netloc.lower())
            parts = [p for p in pr.path.split("/") if p]
            first = f"/{parts[0]}" if parts else "/"
            path_counter[first] += 1
        except Exception:
            pass

    top_paths = [{"path": p, "count": c} for p, c in path_counter.most_common(10)]
    return {
        "lastmod_distribution": buckets,
        "priority_distribution": prio,
        "by_path": top_paths,
        "unique_domains": sorted(domains),
    }


async def analyze(url_or_site: str) -> dict[str, Any]:
    async with build_client(timeout=30, target_url=url_or_site) as client:
        sitemap_url, source = await _discover(client, url_or_site)
        if not sitemap_url:
            return {
                "sitemap_url": None,
                "source": source,
                "total_urls": 0,
                "stats": {},
                "sample_urls": [],
                "sub_sitemaps": [],
                "error": "no sitemap found",
            }

        collected: list[dict[str, Any]] = []
        sub_meta: list[dict[str, Any]] = []

        queue: list[tuple[str, int]] = [(sitemap_url, 0)]
        visited: set[str] = set()
        sub_count = 0

        while queue:
            cur_url, depth = queue.pop(0)
            if cur_url in visited:
                continue
            visited.add(cur_url)

            data = await _fetch_bytes(client, cur_url)
            if data is None:
                sub_meta.append({"url": cur_url, "depth": depth, "status": "fetch_failed", "urls": 0})
                continue
            data = _maybe_gunzip(cur_url, data)
            kind, entries = _parse_sitemap(data)

            if kind == "sitemapindex":
                sub_meta.append({"url": cur_url, "depth": depth, "kind": "index", "sub_count": len(entries)})
                if depth < MAX_DEPTH:
                    for e in entries:
                        if sub_count >= MAX_SUB_SITEMAPS:
                            break
                        sub_count += 1
                        queue.append((e["loc"], depth + 1))
            elif kind == "urlset":
                sub_meta.append({"url": cur_url, "depth": depth, "kind": "urlset", "urls": len(entries)})
                collected.extend(entries)
            else:
                sub_meta.append({"url": cur_url, "depth": depth, "kind": "unknown", "urls": 0})

    stats = _compute_stats(collected)

    return {
        "sitemap_url": sitemap_url,
        "source": source,
        "total_urls": len(collected),
        "stats": stats,
        "sample_urls": collected[:100],
        "sub_sitemaps": sub_meta,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def collect_all_urls(url_or_site: str) -> list[dict[str, Any]]:
    """Return full URL list (not truncated) - used by download/export endpoint."""
    result = await analyze(url_or_site)
    # analyze truncates sample; re-run quickly for full (cheap when cached, but simple here)
    # For export we want full data: re-fetch with same logic.
    async with build_client(timeout=30, target_url=url_or_site) as client:
        sitemap_url, _ = await _discover(client, url_or_site)
        if not sitemap_url:
            return []
        collected: list[dict[str, Any]] = []
        queue: list[tuple[str, int]] = [(sitemap_url, 0)]
        visited: set[str] = set()
        sub_count = 0
        while queue:
            cur_url, depth = queue.pop(0)
            if cur_url in visited:
                continue
            visited.add(cur_url)
            data = await _fetch_bytes(client, cur_url)
            if data is None:
                continue
            data = _maybe_gunzip(cur_url, data)
            kind, entries = _parse_sitemap(data)
            if kind == "sitemapindex" and depth < MAX_DEPTH:
                for e in entries:
                    if sub_count >= MAX_SUB_SITEMAPS:
                        break
                    sub_count += 1
                    queue.append((e["loc"], depth + 1))
            elif kind == "urlset":
                collected.extend(entries)
        _ = result  # keep analyze called for stats consistency
        return collected
