"""URL Mapper orchestrator (Phase 2).

BFS crawl with:
  - depth limit
  - same-domain stay option
  - robots.txt compliance
  - per-host rate limiting
  - URL normalization + dedupe
  - pause/resume via persistent frontier in SQLite
  - broken link detection
  - SSE event publishing throughout
"""
import asyncio
import time
from fnmatch import fnmatch
from typing import Optional

import certifi
import httpx

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.crawl_node import CrawlNode
from app.models.job import JobStatus
from app.repositories.crawl_frontier_repository import CrawlFrontierRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository
from app.schemas.mapper import MapperStartRequest
from app.services.event_bus import event_bus
from app.services.link_extractor import extract as extract_metadata
from app.services.rate_limiter import HostRateLimiter
from app.services.robots_checker import RobotsChecker
from app.services.url_normalizer import get_host, normalize_url, same_domain


class UrlCrawlerService:
    async def run(
        self,
        job_id: str,
        stop_event: asyncio.Event,
        req: MapperStartRequest,
    ) -> None:
        start_url = normalize_url(str(req.url), strip_tracking=req.strip_tracking_params)

        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            node_repo = CrawlNodeRepository(session)
            frontier_repo = CrawlFrontierRepository(session)

            await job_repo.update_status(job_id, JobStatus.RUNNING)
            await session.commit()
            await event_bus.publish(job_id, {"type": "status", "status": "running"})

            # Seed frontier if empty (first run)
            if await frontier_repo.size(job_id) == 0 and await node_repo.count(job_id) == 0:
                await frontier_repo.add(job_id, start_url, depth=0, parent_node_id=None)
                await session.commit()

            try:
                async with httpx.AsyncClient(
                    timeout=settings.default_timeout,
                    headers={"User-Agent": settings.default_user_agent},
                    verify=certifi.where(),
                    follow_redirects=True,
                ) as client:
                    robots = RobotsChecker(client, settings.default_user_agent)
                    limiter = HostRateLimiter(default_rps=req.rate_limit_per_host)
                    sem = asyncio.Semaphore(req.concurrency)

                    stats = {
                        "discovered": 0,
                        "crawled": 0,
                        "broken": 0,
                        "redirected": 0,
                        "external_skipped": 0,
                        "avg_response_ms": 0,
                        "frontier_size": 0,
                    }

                    # Main BFS loop
                    while not stop_event.is_set():
                        if await node_repo.count(job_id) >= req.max_pages:
                            await event_bus.publish(
                                job_id, {"type": "log", "message": f"max_pages ({req.max_pages}) reached"}
                            )
                            break

                        batch = await frontier_repo.pop_batch(job_id, limit=req.concurrency)
                        await session.commit()
                        if not batch:
                            break  # empty frontier → done

                        async def handle(entry) -> None:
                            if stop_event.is_set():
                                return
                            url = entry.url
                            depth = entry.depth
                            parent_node_id = entry.parent_node_id

                            # Exclude patterns
                            for pat in req.exclude_patterns:
                                if fnmatch(url, pat):
                                    return

                            # Same-domain check
                            if req.stay_on_domain and not same_domain(url, start_url):
                                stats["external_skipped"] += 1
                                return

                            # robots.txt
                            if req.respect_robots and not await robots.allowed(url):
                                await event_bus.publish(
                                    job_id, {"type": "log", "message": f"robots denied: {url}"}
                                )
                                return

                            # Rate limit per host
                            await limiter.wait(url)

                            async with sem:
                                await self._crawl_one(
                                    session=session,
                                    node_repo=node_repo,
                                    frontier_repo=frontier_repo,
                                    job_id=job_id,
                                    url=url,
                                    depth=depth,
                                    parent_node_id=parent_node_id,
                                    client=client,
                                    req=req,
                                    start_url=start_url,
                                    stats=stats,
                                )

                        gather_results = await asyncio.gather(*(handle(e) for e in batch), return_exceptions=True)
                        for r in gather_results:
                            if isinstance(r, Exception):
                                await event_bus.publish(job_id, {
                                    "type": "log", "message": f"Crawl task error: {r}",
                                })
                        await session.commit()

                        # Publish progress snapshot
                        stats["frontier_size"] = await frontier_repo.size(job_id)
                        stats["broken"] = await node_repo.count_broken(job_id)
                        stats["crawled"] = await node_repo.count(job_id)
                        stats["avg_response_ms"] = await node_repo.avg_response_ms(job_id)
                        await event_bus.publish(job_id, {"type": "progress", "stats": dict(stats)})

                # Finalize — always persist stats so Resume can show accurate numbers.
                await job_repo.update_stats(job_id, stats)
                if stop_event.is_set():
                    await job_repo.update_status(job_id, JobStatus.STOPPED)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "stopped", "stats": stats})
                else:
                    await job_repo.update_status(job_id, JobStatus.DONE)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "done", "stats": stats})

            except Exception as e:
                # Main session may be poisoned — use a fresh one for status update.
                try:
                    await session.rollback()
                except Exception:
                    pass
                async with AsyncSessionLocal() as err_session:
                    err_repo = JobRepository(err_session)
                    await err_repo.update_status(job_id, JobStatus.ERROR, str(e))
                    await err_session.commit()
                await event_bus.publish(job_id, {"type": "error", "message": str(e)})

    async def _crawl_one(
        self,
        *,
        session,
        node_repo: CrawlNodeRepository,
        frontier_repo: CrawlFrontierRepository,
        job_id: str,
        url: str,
        depth: int,
        parent_node_id: Optional[int],
        client: httpx.AsyncClient,
        req: MapperStartRequest,
        start_url: str,
        stats: dict,
    ) -> None:
        # Skip if already crawled
        if await node_repo.exists(job_id, url):
            return

        t0 = time.monotonic()
        status_code: Optional[int] = None
        content_type: Optional[str] = None
        title: Optional[str] = None
        word_count: Optional[int] = None
        error: Optional[str] = None
        html_body: Optional[str] = None

        try:
            r = await client.get(url)
            status_code = r.status_code
            content_type = r.headers.get("content-type", "").split(";")[0].strip() or None
            if 200 <= r.status_code < 300 and "html" in (content_type or ""):
                html_body = r.text
            elif 300 <= r.status_code < 400:
                stats["redirected"] += 1
        except httpx.HTTPError as e:
            error = str(e)
            status_code = None
        except Exception as e:
            error = str(e)

        response_ms = int((time.monotonic() - t0) * 1000)

        # Parse metadata + follow links
        child_links: list[str] = []
        if html_body:
            meta = extract_metadata(html_body, url)
            title = meta.title
            word_count = meta.word_count
            child_links = meta.links

        # Persist node
        node = CrawlNode(
            job_id=job_id,
            url=url,
            parent_id=parent_node_id,
            depth=depth,
            status_code=status_code,
            content_type=content_type,
            title=title,
            word_count=word_count,
            response_ms=response_ms,
            error=error,
        )
        await node_repo.create(node)
        await session.flush()

        await event_bus.publish(job_id, {
            "type": "node",
            "id": node.id,
            "url": url,
            "depth": depth,
            "parent_id": parent_node_id,
            "status_code": status_code,
            "title": title,
        })

        # Enqueue children if below depth limit
        if depth + 1 <= req.max_depth and child_links and html_body:
            seen_in_batch: set[str] = set()
            for raw in child_links:
                norm = normalize_url(raw, strip_tracking=req.strip_tracking_params)
                if norm in seen_in_batch:
                    continue
                seen_in_batch.add(norm)
                if req.stay_on_domain and not same_domain(norm, start_url):
                    stats["external_skipped"] += 1
                    continue
                if await node_repo.exists(job_id, norm):
                    continue
                added = await frontier_repo.add(
                    job_id=job_id, url=norm, depth=depth + 1, parent_node_id=node.id
                )
                if added:
                    stats["discovered"] += 1


url_crawler_service = UrlCrawlerService()
