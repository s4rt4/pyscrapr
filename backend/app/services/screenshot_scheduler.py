"""Scheduled screenshot capture with automatic change detection.

Hooks into APScheduler via ``scheduler.create_schedule``. Registered as tool
key ``screenshot`` in the TYPE_MAP extension below. When fired, runs a capture
and, if a prior screenshot job exists for the same URL+viewport, also
computes a diff_ratio against it (change detection).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import desc, select

from app.config import settings as app_config
from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services.screenshot_capture import get_capture
from app.services import screenshot_compare as compare_service

logger = logging.getLogger("pyscrapr.screenshot")


def _screenshot_dir() -> Path:
    d = app_config.data_dir / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _find_previous(url: str, viewport: str) -> Optional[Job]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Job)
            .where(Job.type == JobType.SCREENSHOT)
            .where(Job.url == url)
            .where(Job.status == JobStatus.DONE)
            .order_by(desc(Job.created_at))
            .limit(5)
        )
        res = await session.execute(stmt)
        for j in res.scalars().all():
            cfg = j.config or {}
            vp = cfg.get("viewport") or (cfg.get("viewports") or [None])[0]
            if vp == viewport:
                return j
    return None


async def scheduled_capture(url: str, options: dict[str, Any]) -> dict[str, Any]:
    """Run a scheduled screenshot capture with auto change-detection.

    Persists a new Job row. If a previous DONE screenshot exists for the same
    URL and viewport, runs a compare and stores the diff_ratio in stats.
    """
    viewport = options.get("viewport") or "desktop"
    options = dict(options or {})

    job_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        job = Job(
            id=job_id,
            type=JobType.SCREENSHOT,
            url=url,
            status=JobStatus.RUNNING,
            config={**options, "url": url, "viewport": viewport, "scheduled": True},
            stats={},
        )
        await JobRepository(session).create(job)
        await session.commit()

    capture = get_capture()
    out_dir = _screenshot_dir()
    try:
        result = await capture.capture(
            url=url,
            output_dir=out_dir,
            job_id=job_id,
            viewport=viewport,
            custom_width=options.get("custom_width"),
            custom_height=options.get("custom_height"),
            full_page=options.get("full_page", True),
            dark_mode=bool(options.get("dark_mode", False)),
            wait_until=options.get("wait_until", "networkidle"),
            timeout_ms=int(options.get("timeout_ms", 30000)),
        )
    except Exception as exc:
        err = str(exc) or type(exc).__name__
        logger.exception("Scheduled screenshot failed for %s: %s", url, err)
        async with AsyncSessionLocal() as session:
            job2 = await JobRepository(session).find_by_id(job_id)
            if job2:
                job2.status = JobStatus.ERROR
                job2.error_message = err
                await session.commit()
        return {"ok": False, "job_id": job_id, "error": err}

    diff_ratio: Optional[float] = None
    prev = await _find_previous(url, viewport)
    if prev is not None:
        prev_file = f"screenshot_{prev.id}.png"
        new_file = f"screenshot_{job_id}.png"
        try:
            cmp_out = _screenshot_dir() / "compare"
            cmp_out.mkdir(parents=True, exist_ok=True)
            cmp_result = await compare_service.compare(
                job_id_a=prev.id,
                filename_a=prev_file,
                job_id_b=job_id,
                filename_b=new_file,
                output_dir=cmp_out,
                mode="overlay",
                source_dir=_screenshot_dir(),
            )
            diff_ratio = float(cmp_result["stats"]["diff_ratio"])
        except Exception as exc:
            logger.warning("Auto-compare gagal untuk %s: %s", url, exc)

    stats = {
        "file_size_bytes": result["file_size_bytes"],
        "width": result["dimensions"]["width"],
        "height": result["dimensions"]["height"],
        "status": result["status"],
        "scheduled": True,
    }
    if diff_ratio is not None:
        stats["diff_ratio"] = diff_ratio
        stats["compared_against"] = prev.id if prev else None

    async with AsyncSessionLocal() as session:
        job3 = await JobRepository(session).find_by_id(job_id)
        if job3:
            job3.status = JobStatus.DONE
            job3.output_dir = str(out_dir)
            job3.stats = stats
            await session.commit()

    return {"ok": True, "job_id": job_id, "diff_ratio": diff_ratio}


def register_screenshot_tool() -> None:
    """Register 'screenshot' as an allowed tool in the shared TYPE_MAP.

    The existing scheduler dispatches via ``app.api.bulk._dispatch`` which
    keys off ``TYPE_MAP``. We extend it in-place and install a dispatch
    override that special-cases the screenshot job type.
    """
    from app.api import bulk as bulk_module

    bulk_module.TYPE_MAP.setdefault("screenshot", JobType.SCREENSHOT)

    original_dispatch = getattr(bulk_module, "_dispatch", None)

    def _dispatch_patched(job_id: str, job_type: JobType, config: dict) -> Any:
        if job_type == JobType.SCREENSHOT:
            import asyncio

            url = config.get("url", "")
            loop = asyncio.get_event_loop()
            return loop.create_task(scheduled_capture(url, config))
        if original_dispatch is not None:
            return original_dispatch(job_id, job_type, config)
        return None

    # Only wrap once
    if not getattr(bulk_module._dispatch, "_screenshot_wrapped", False):  # type: ignore[attr-defined]
        _dispatch_patched._screenshot_wrapped = True  # type: ignore[attr-defined]
        bulk_module._dispatch = _dispatch_patched  # type: ignore[assignment]
