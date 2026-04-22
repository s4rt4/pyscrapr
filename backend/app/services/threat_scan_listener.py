"""Auto-scan listener - triggers ThreatScanner on downloader/ripper/harvester done."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.threat.listener")

_TRIGGER_TYPES = {
    JobType.IMAGE_HARVESTER,
    JobType.SITE_RIPPER,
    JobType.MEDIA_DOWNLOADER,
}


async def _run_scan(job_id: str, stop_event, folder: str, depth: str) -> None:
    from app.services.threat_scanner import get_scanner
    scanner = get_scanner()
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        job = await repo.find_by_id(job_id)
        if job:
            job.status = JobStatus.RUNNING
            await session.commit()
    try:
        report = await scanner.scan_folder(Path(folder), job_id, depth=depth)
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(job_id)
            if job:
                job.status = JobStatus.DONE
                job.output_dir = folder
                job.stats = {
                    "files_total": report.get("files_total", 0),
                    "files_clean": report.get("files_clean", 0),
                    "files_suspicious": report.get("files_suspicious", 0),
                    "files_dangerous": report.get("files_dangerous", 0),
                }
                await session.commit()
        await event_bus.publish(job_id, {"type": "done", "stats": report})
    except Exception as e:
        logger.exception("auto-scan gagal: %s", e)
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(job_id)
            if job:
                job.status = JobStatus.ERROR
                job.error_message = str(e)
                await session.commit()
        await event_bus.publish(job_id, {"type": "error", "message": str(e)})


async def on_job_event(source_job_id: str, event: dict[str, Any]) -> None:
    if event.get("type") != "done":
        return
    if not get_setting("threat_auto_scan_downloads", False):
        return

    try:
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(source_job_id)
            if not job:
                return
            if job.type not in _TRIGGER_TYPES:
                return
            output_dir = job.output_dir
            if not output_dir or not Path(output_dir).exists():
                return

        # Spawn a THREAT_SCAN job
        new_id = str(uuid.uuid4())
        depth = get_setting("threat_scan_depth", "standard") or "standard"
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            new_job = Job(
                id=new_id,
                type=JobType.THREAT_SCAN,
                url=output_dir,
                status=JobStatus.PENDING,
                config={"triggered_by": source_job_id, "path": output_dir, "depth": depth},
                stats={},
            )
            await repo.create(new_job)
            await session.commit()

        job_manager.submit(new_id, _run_scan, folder=output_dir, depth=depth)
        logger.info("Auto threat-scan dispatched job %s untuk folder %s", new_id[:8], output_dir)
    except Exception as e:
        logger.warning("threat auto-scan listener error: %s", e)
