"""Site Ripper orchestrator (Phase 3).

Flow:
  1. Seed frontier with start URL
  2. BFS crawl same-domain pages (respecting depth)
  3. For each HTML page: extract asset list + follow links
  4. Download all assets (within budget)
  5. Second pass: rewrite HTML and CSS to use local relative paths
  6. Generate PDF report
"""
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

import aiofiles
import certifi
import httpx

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job import JobStatus
from app.repositories.job_repository import JobRepository
from app.schemas.ripper import RipperStartRequest
from app.services.asset_extractor import (
    AssetRef,
    extract_css_urls,
    extract_html_assets,
)
from app.services.event_bus import event_bus
from app.services.mirror_path_mapper import to_local_path, url_to_relpath
from app.services.rate_limiter import HostRateLimiter
from app.services.report_generator import build_report
from app.services.robots_checker import RobotsChecker
from app.services.url_normalizer import get_host, normalize_url, same_domain
from app.services.url_rewriter import rewrite_css, rewrite_html
from app.utils.hash_helper import sha1_bytes
from app.utils.path_helper import domain_folder


@dataclass
class _DownloadedAsset:
    url: str
    kind: str
    local_rel: PurePosixPath
    local_abs: Path
    size: int
    status_code: int
    content_type: Optional[str]
    content: bytes  # in-memory copy for HTML/CSS rewrite pass
    error: Optional[str] = None


class SiteRipperService:
    async def run(
        self,
        job_id: str,
        stop_event: asyncio.Event,
        req: RipperStartRequest,
    ) -> None:
        start_url = normalize_url(str(req.url))

        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            await job_repo.update_status(job_id, JobStatus.RUNNING)
            await session.commit()
            await event_bus.publish(job_id, {"type": "status", "status": "running"})

            try:
                # Output dir
                domain = get_host(start_url)
                out_root = domain_folder(settings.download_dir, domain, "mirror").parent  # drop "originals"
                out_root = out_root / "site"
                out_root.mkdir(parents=True, exist_ok=True)

                from app.services.http_factory import build_client
                async with build_client(target_url=start_url, timeout=settings.default_timeout) as client:
                    robots = RobotsChecker(client, settings.default_user_agent)
                    limiter = HostRateLimiter(default_rps=req.rate_limit_per_host)
                    sem = asyncio.Semaphore(req.concurrency)

                    # ========== PASS 1: download everything ==========
                    pages: dict[str, _DownloadedAsset] = {}      # url → HTML page
                    assets: dict[str, _DownloadedAsset] = {}     # url → non-HTML asset
                    page_links: dict[str, list[str]] = {}        # page_url → child page URLs
                    page_assets: dict[str, list[str]] = {}       # page_url → asset URLs
                    broken: list[dict] = []
                    stats = {
                        "pages": 0,
                        "assets": 0,
                        "bytes_total": 0,
                        "broken": 0,
                        "failed": 0,
                        "by_kind": {},
                    }

                    # Frontier for pages (BFS)
                    queue: list[tuple[str, int]] = [(start_url, 0)]
                    queued: set[str] = {start_url}

                    while queue and not stop_event.is_set():
                        if stats["pages"] >= req.max_pages:
                            break
                        url, depth = queue.pop(0)

                        if req.respect_robots and not await robots.allowed(url):
                            continue
                        await limiter.wait(url)

                        # Route INITIAL page (seed) through Playwright when requested.
                        page = None
                        if getattr(req, "use_playwright", False) and url == start_url:
                            try:
                                from app.services.playwright_renderer import get_renderer
                                await event_bus.publish(job_id, {
                                    "type": "log",
                                    "message": "Rendering seed via Playwright (Chromium)",
                                })
                                renderer = await get_renderer()
                                html_text = await renderer.fetch_html(url)
                                content = html_text.encode("utf-8", errors="replace")
                                rel = url_to_relpath(url, default_html=True)
                                abs_path = to_local_path(out_root, rel)
                                abs_path.parent.mkdir(parents=True, exist_ok=True)
                                page = _DownloadedAsset(
                                    url=url,
                                    kind="html",
                                    local_rel=rel,
                                    local_abs=abs_path,
                                    size=len(content),
                                    status_code=200,
                                    content_type="text/html",
                                    content=content,
                                )
                            except Exception as pw_exc:
                                await event_bus.publish(job_id, {
                                    "type": "log",
                                    "message": f"Playwright unavailable, falling back to httpx: {pw_exc}",
                                })
                                page = None
                        if page is None:
                            page = await self._download(
                                client, url, out_root, kind="html", sem=sem, is_html=True
                            )
                        if not page:
                            stats["failed"] += 1
                            continue
                        if page.status_code >= 400:
                            broken.append({"url": url, "status": page.status_code})
                            stats["broken"] += 1
                            continue

                        pages[url] = page
                        stats["pages"] += 1
                        stats["bytes_total"] += page.size
                        self._tally_kind(stats, "html", page.size)
                        await event_bus.publish(job_id, {
                            "type": "page_done",
                            "url": url,
                            "depth": depth,
                            "size": page.size,
                            "stats": dict(stats),
                        })

                        # Parse HTML → collect assets + links
                        html = page.content.decode(errors="replace")
                        asset_refs, links = extract_html_assets(html, url)
                        page_assets[url] = [a.url for a in asset_refs]
                        page_links[url] = links

                        # Schedule child pages
                        if depth + 1 <= req.max_depth:
                            for link in links:
                                norm = normalize_url(link)
                                if norm in queued:
                                    continue
                                if req.stay_on_domain and not same_domain(norm, start_url):
                                    continue
                                queued.add(norm)
                                queue.append((norm, depth + 1))

                        # Download assets for this page (parallel batch)
                        async def fetch_asset(ref: AssetRef):
                            if stop_event.is_set():
                                return
                            if ref.url in assets:
                                return
                            if stats["assets"] >= req.max_assets:
                                return
                            if not req.include_external_assets and not same_domain(ref.url, start_url):
                                return
                            if req.respect_robots and not await robots.allowed(ref.url):
                                return
                            await limiter.wait(ref.url)
                            downloaded = await self._download(
                                client, ref.url, out_root, kind=ref.kind, sem=sem, is_html=False
                            )
                            if not downloaded:
                                stats["failed"] += 1
                                return
                            if downloaded.status_code >= 400:
                                broken.append({"url": ref.url, "status": downloaded.status_code})
                                stats["broken"] += 1
                                return
                            assets[ref.url] = downloaded
                            stats["assets"] += 1
                            stats["bytes_total"] += downloaded.size
                            self._tally_kind(stats, ref.kind, downloaded.size)
                            await event_bus.publish(job_id, {
                                "type": "asset_done",
                                "url": ref.url,
                                "kind": ref.kind,
                                "size": downloaded.size,
                                "stats": {k: v for k, v in stats.items() if k != "by_kind"} | {"by_kind": stats["by_kind"]},
                            })

                        _gather_results = await asyncio.gather(
                            *(fetch_asset(a) for a in asset_refs),
                            return_exceptions=True,
                        )
                        for _r in _gather_results:
                            if isinstance(_r, Exception):
                                stats["failed"] += 1
                                await event_bus.publish(job_id, {
                                    "type": "log", "message": f"Asset task error: {_r}",
                                })

                        # Recursively fetch CSS-referenced assets (one level deep)
                        css_items = [a for a in assets.values() if a.kind == "css"]
                        for css_item in list(css_items):
                            try:
                                css_text = css_item.content.decode(errors="replace")
                            except Exception:
                                continue
                            for nested in extract_css_urls(css_text):
                                nested_full = self._resolve(css_item.url, nested)
                                if nested_full in assets:
                                    continue
                                if stats["assets"] >= req.max_assets:
                                    break
                                if req.respect_robots and not await robots.allowed(nested_full):
                                    continue
                                await limiter.wait(nested_full)
                                nested_kind = self._guess_css_nested_kind(nested_full)
                                d = await self._download(
                                    client, nested_full, out_root, kind=nested_kind, sem=sem, is_html=False
                                )
                                if not d or d.status_code >= 400:
                                    continue
                                assets[nested_full] = d
                                stats["assets"] += 1
                                stats["bytes_total"] += d.size
                                self._tally_kind(stats, nested_kind, d.size)

                    # ========== PASS 2: rewrite + save ==========
                    if req.rewrite_links:
                        url_map: dict[str, PurePosixPath] = {}
                        for u, a in pages.items():
                            url_map[u] = a.local_rel
                        for u, a in assets.items():
                            url_map[u] = a.local_rel

                        # Rewrite HTML
                        for u, page in pages.items():
                            try:
                                html = page.content.decode(errors="replace")
                                new_html = rewrite_html(
                                    html, u, page.local_rel, url_map
                                )
                                page.local_abs.parent.mkdir(parents=True, exist_ok=True)
                                async with aiofiles.open(page.local_abs, "w", encoding="utf-8") as f:
                                    await f.write(new_html)
                            except Exception as e:
                                await event_bus.publish(job_id, {"type": "log", "message": f"rewrite html failed: {u} — {e}"})

                        # Rewrite CSS
                        for u, a in assets.items():
                            if a.kind != "css":
                                continue
                            try:
                                css = a.content.decode(errors="replace")
                                new_css = rewrite_css(css, u, a.local_rel, url_map)
                                async with aiofiles.open(a.local_abs, "w", encoding="utf-8") as f:
                                    await f.write(new_css)
                            except Exception as exc:
                                await event_bus.publish(job_id, {
                                    "type": "log",
                                    "message": f"CSS rewrite failed: {u} — {exc}",
                                })

                    # Generate report
                    if req.generate_report:
                        try:
                            report_path = out_root / "_report.pdf"
                            build_report(
                                report_path,
                                job_url=start_url,
                                stats=stats,
                                by_kind=stats["by_kind"],
                                broken=broken,
                            )
                            await event_bus.publish(job_id, {"type": "log", "message": "PDF report generated"})
                        except Exception as e:
                            await event_bus.publish(job_id, {"type": "log", "message": f"PDF failed: {e}"})

                # Finalize
                await job_repo.update_stats(job_id, stats)
                job = await job_repo.find_by_id(job_id)
                if job:
                    job.output_dir = str(out_root)
                if stop_event.is_set():
                    await job_repo.update_status(job_id, JobStatus.STOPPED)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "stopped", "stats": stats})
                else:
                    await job_repo.update_status(job_id, JobStatus.DONE)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "done", "stats": stats})

            except Exception as e:
                try:
                    await session.rollback()
                except Exception:
                    pass
                async with AsyncSessionLocal() as err_session:
                    err_repo = JobRepository(err_session)
                    await err_repo.update_status(job_id, JobStatus.ERROR, str(e))
                    await err_session.commit()
                await event_bus.publish(job_id, {"type": "error", "message": str(e)})

    # ─────────────── helpers ───────────────

    async def _download(
        self,
        client: httpx.AsyncClient,
        url: str,
        out_root: Path,
        kind: str,
        sem: asyncio.Semaphore,
        is_html: bool,
    ) -> Optional[_DownloadedAsset]:
        async with sem:
            try:
                t0 = time.monotonic()
                r = await client.get(url)
                content = r.content
                rel = url_to_relpath(url, default_html=is_html)
                abs_path = to_local_path(out_root, rel)
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                # Only pre-write non-HTML/CSS here; HTML + CSS get rewritten in pass 2
                if not (is_html or kind == "css"):
                    async with aiofiles.open(abs_path, "wb") as f:
                        await f.write(content)
                return _DownloadedAsset(
                    url=url,
                    kind=kind,
                    local_rel=rel,
                    local_abs=abs_path,
                    size=len(content),
                    status_code=r.status_code,
                    content_type=r.headers.get("content-type"),
                    content=content,
                )
            except Exception as e:
                return _DownloadedAsset(
                    url=url, kind=kind, local_rel=PurePosixPath("error"),
                    local_abs=out_root / "error", size=0, status_code=0,
                    content_type=None, content=b"", error=str(e),
                )

    @staticmethod
    def _tally_kind(stats: dict, kind: str, size: int) -> None:
        d = stats["by_kind"].setdefault(kind, {"count": 0, "bytes": 0})
        d["count"] += 1
        d["bytes"] += size

    @staticmethod
    def _resolve(base: str, relative: str) -> str:
        from urllib.parse import urljoin
        return urljoin(base, relative)

    @staticmethod
    def _guess_css_nested_kind(url: str) -> str:
        low = url.lower().split("?")[0]
        if low.endswith((".woff", ".woff2", ".ttf", ".otf", ".eot")):
            return "font"
        if low.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            return "image"
        if low.endswith(".css"):
            return "css"
        return "other"


site_ripper_service = SiteRipperService()
