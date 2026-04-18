"""Image Harvester orchestrator (Phase 1).

Flow:
  1. Fetch HTML
  2. Parse images
  3. Filter by URL hints
  4. Download in parallel with concurrency limit
  5. Validate dimensions via Pillow
  6. Persist Asset rows + update Job stats
  7. Emit SSE events throughout
"""
import asyncio
from datetime import datetime
from io import BytesIO
from pathlib import Path

import certifi
import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.job import JobStatus
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import ImageFilterConfig
from app.services.deduplicator import Deduplicator
from app.services.downloader import Downloader
from app.services.event_bus import event_bus
from app.services.filter_engine import FilterEngine, ImageCandidate
from app.services.image_parser import parse_images
from app.utils.path_helper import domain_folder, safe_filename
from app.utils.url_helper import extract_domain


class ImageHarvesterService:
    async def run(
        self,
        job_id: str,
        stop_event: asyncio.Event,
        url: str,
        filters: ImageFilterConfig,
        concurrency: int,
        include_css_bg: bool,
        deduplicate: bool,
        use_playwright: bool = False,
    ) -> None:
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            asset_repo = AssetRepository(session)

            await self._set_status(session, job_repo, job_id, JobStatus.RUNNING)
            await event_bus.publish(job_id, {"type": "status", "status": "running"})

            try:
                stats = {"discovered": 0, "downloaded": 0, "skipped": 0, "failed": 0, "bytes_total": 0}
                domain = extract_domain(url)
                out_dir = domain_folder(settings.download_dir, domain, "images")
                out_dir.mkdir(parents=True, exist_ok=True)

                from app.services.http_factory import build_client, build_downloader
                async with build_client(target_url=url) as client:
                    downloader = build_downloader(client, max_concurrency=concurrency)
                    filter_engine = FilterEngine(filters)
                    dedup = Deduplicator()

                    # 1. Fetch HTML (optionally via Playwright)
                    await event_bus.publish(job_id, {"type": "log", "message": f"Fetching {url}"})
                    html: str | None = None
                    if use_playwright:
                        try:
                            from app.services.playwright_renderer import get_renderer
                            await event_bus.publish(job_id, {"type": "log", "message": "Rendering via Playwright (Chromium)"})
                            renderer = await get_renderer()
                            html = await renderer.fetch_html(url)
                        except Exception as pw_exc:
                            await event_bus.publish(job_id, {
                                "type": "log",
                                "message": f"Playwright unavailable, falling back to httpx: {pw_exc}",
                            })
                    if html is None:
                        html = await downloader.fetch_html(url)

                    # 2. Parse
                    candidates = parse_images(html, url, include_css_bg=include_css_bg)
                    stats["discovered"] = len(candidates)
                    await event_bus.publish(job_id, {
                        "type": "discovered",
                        "count": len(candidates),
                    })

                    # 3. Pre-filter by URL / dedupe
                    passing: list[ImageCandidate] = []
                    for c in candidates:
                        if deduplicate and dedup.seen_url(c.url):
                            stats["skipped"] += 1
                            continue
                        ok, _ = filter_engine.accept_url(c)
                        if not ok:
                            stats["skipped"] += 1
                            continue
                        passing.append(c)

                    # 4. Parallel download
                    async def handle_one(idx: int, cand: ImageCandidate):
                        if stop_event.is_set():
                            return
                        filename = safe_filename(cand.url, index=idx)
                        result = await downloader.download(cand.url, out_dir, filename)
                        if not result.ok:
                            stats["failed"] += 1
                            await event_bus.publish(job_id, {
                                "type": "asset_failed",
                                "url": cand.url,
                                "error": result.error,
                            })
                            return

                        # Size filter
                        ok, reason = filter_engine.accept_bytes(result.size_bytes)
                        if not ok:
                            self._unlink_safe(result.local_path)
                            stats["skipped"] += 1
                            return

                        # Dimension filter (Pillow)
                        width = height = None
                        try:
                            with Image.open(BytesIO(result.local_path.read_bytes())) as im:
                                width, height = im.size
                        except Exception as exc:
                            await event_bus.publish(job_id, {
                                "type": "log",
                                "message": f"Pillow parse skipped: {cand.url} — {exc}",
                            })
                        if width and height:
                            ok, _ = filter_engine.accept_dimensions(width, height)
                            if not ok:
                                self._unlink_safe(result.local_path)
                                stats["skipped"] += 1
                                return

                        # Hash dedupe
                        if deduplicate and dedup.seen_hash(result.sha1 or ""):
                            self._unlink_safe(result.local_path)
                            stats["skipped"] += 1
                            return

                        stats["downloaded"] += 1
                        stats["bytes_total"] += result.size_bytes

                        asset = Asset(
                            job_id=job_id,
                            url=cand.url,
                            kind=AssetKind.IMAGE,
                            status=AssetStatus.DONE,
                            local_path=str(result.local_path),
                            content_type=result.content_type,
                            size_bytes=result.size_bytes,
                            width=width,
                            height=height,
                            sha1=result.sha1,
                            alt_text=cand.alt,
                        )
                        await asset_repo.create(asset)

                        await event_bus.publish(job_id, {
                            "type": "asset_done",
                            "url": cand.url,
                            "size": result.size_bytes,
                            "width": width,
                            "height": height,
                            "stats": dict(stats),
                        })

                    # Run with task group
                    tasks = [handle_one(i, c) for i, c in enumerate(passing)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Surface any hidden task exceptions
                    for r in results:
                        if isinstance(r, Exception):
                            stats["failed"] += 1
                            await event_bus.publish(job_id, {
                                "type": "log",
                                "message": f"Task error: {r}",
                            })

                if stop_event.is_set():
                    await self._set_status(session, job_repo, job_id, JobStatus.STOPPED)
                    await event_bus.publish(job_id, {"type": "stopped", "stats": stats})
                else:
                    await job_repo.update_stats(job_id, stats)
                    job = await job_repo.find_by_id(job_id)
                    if job:
                        job.output_dir = str(out_dir)
                    await self._set_status(session, job_repo, job_id, JobStatus.DONE)
                    await event_bus.publish(job_id, {"type": "done", "stats": stats})

                await session.commit()

            except Exception as e:
                await self._set_status(session, job_repo, job_id, JobStatus.ERROR, str(e))
                await session.commit()
                await event_bus.publish(job_id, {"type": "error", "message": str(e)})

    async def _set_status(
        self,
        session: AsyncSession,
        repo: JobRepository,
        job_id: str,
        status: JobStatus,
        error: str | None = None,
    ):
        await repo.update_status(job_id, status, error)
        await session.commit()

    @staticmethod
    def _unlink_safe(path: Path | None) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


image_harvester_service = ImageHarvesterService()
