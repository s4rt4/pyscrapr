"""Broken link checker - BFS crawl lalu validasi setiap link via HEAD/GET."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.link_checker")


def _norm(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path or '/'}"


class LinkChecker:
    async def check(
        self,
        url: str,
        max_pages: int = 50,
        timeout: int = 10,
        stay_on_domain: bool = True,
    ) -> dict[str, Any]:
        started = time.time()
        start_host = urlparse(url).netloc.lower()

        visited_pages: set[str] = set()
        queue: deque[str] = deque([url])
        link_results: list[dict[str, Any]] = []
        seen_links: dict[str, dict[str, Any]] = {}
        by_status: dict[int, int] = {}
        by_page: dict[str, list[dict[str, Any]]] = {}

        async with build_client(timeout=timeout, target_url=url) as client:
            while queue and len(visited_pages) < max_pages:
                page = queue.popleft()
                np = _norm(page)
                if np in visited_pages:
                    continue
                visited_pages.add(np)

                try:
                    resp = await client.get(page)
                except httpx.HTTPError as e:
                    logger.debug("page fetch failed %s: %s", page, e)
                    continue

                try:
                    soup = BeautifulSoup(resp.text, "html.parser")
                except Exception:
                    continue

                page_links: list[dict[str, Any]] = []
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                        continue
                    absolute = urljoin(str(resp.url), href)
                    parsed = urlparse(absolute)
                    if parsed.scheme not in ("http", "https"):
                        continue
                    target_host = parsed.netloc.lower()

                    key = _norm(absolute)
                    if key in seen_links:
                        cached = seen_links[key]
                        entry = {**cached, "source_page": page}
                    else:
                        entry = await self._check_link(client, absolute)
                        seen_links[key] = entry
                        entry = {**entry, "source_page": page}
                        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1

                    link_results.append(entry)
                    page_links.append(entry)

                    # Enqueue internal pages for crawl
                    same_domain = target_host == start_host
                    if same_domain and entry.get("ok") and len(visited_pages) + len(queue) < max_pages:
                        nk = _norm(absolute)
                        if nk not in visited_pages and nk not in {_norm(q) for q in queue}:
                            queue.append(absolute)

                by_page[page] = page_links

        ok_count = sum(1 for r in link_results if r.get("ok"))
        broken_count = sum(1 for r in link_results if not r.get("ok"))
        redirect_count = sum(1 for r in link_results if 300 <= r.get("status", 0) < 400)
        broken_list = [r for r in link_results if not r.get("ok")]

        return {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": round(time.time() - started, 2),
            "total_pages": len(visited_pages),
            "total_links": len(link_results),
            "unique_links": len(seen_links),
            "ok_count": ok_count,
            "broken_count": broken_count,
            "redirect_count": redirect_count,
            "by_status": {str(k): v for k, v in by_status.items()},
            "broken_list": broken_list,
            "all_links": link_results[:2000],
        }

    async def _check_link(self, client: httpx.AsyncClient, link: str) -> dict[str, Any]:
        t0 = time.time()
        chain: list[str] = []
        status = 0
        reason = ""
        try:
            r = await client.head(link, follow_redirects=True)
            status = r.status_code
            chain = [str(h.url) for h in r.history]
            if status in (405, 501, 403):
                # HEAD not supported, fallback to GET
                r = await client.get(link, follow_redirects=True)
                status = r.status_code
                chain = [str(h.url) for h in r.history]
        except httpx.HTTPError as e:
            try:
                r = await client.get(link, follow_redirects=True)
                status = r.status_code
                chain = [str(h.url) for h in r.history]
            except httpx.HTTPError as e2:
                reason = str(e2)[:160]
        latency = int((time.time() - t0) * 1000)
        ok = 200 <= status < 400
        return {
            "url": link,
            "status": status,
            "ok": ok,
            "latency_ms": latency,
            "redirect_chain": chain,
            "reason": reason,
        }


_singleton: LinkChecker | None = None


def get_checker() -> LinkChecker:
    global _singleton
    if _singleton is None:
        _singleton = LinkChecker()
    return _singleton
