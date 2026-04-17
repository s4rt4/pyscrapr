"""Global EventBus listener that auto-runs pipelines on job completion.

When a job reaches "done" state, look up any enabled pipelines configured
to auto-run on that job_type, execute them against the job's data, and
save the output as artifacts in data/pipeline_runs/.
"""
import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job import JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository
from app.services.event_bus import event_bus
from app.services.pipeline_executor import find_pipelines_for_job_type, run_pipeline

logger = logging.getLogger("pyscrapr.pipeline_listener")

_PIPELINE_RUNS_DIR = settings.data_dir / "pipeline_runs"


async def _collect_job_data(session, job) -> list[dict]:
    """Extract data from a completed job for pipeline processing."""
    if job.type in (JobType.IMAGE_HARVESTER, JobType.SITE_RIPPER, JobType.MEDIA_DOWNLOADER):
        repo = AssetRepository(session)
        assets = await repo.list_for_job(job.id, limit=10000)
        return [
            {
                "url": a.url,
                "kind": a.kind.value if hasattr(a.kind, "value") else str(a.kind),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "size_bytes": a.size_bytes,
                "local_path": a.local_path,
                "alt_text": a.alt_text,
            }
            for a in assets
        ]
    elif job.type == JobType.URL_MAPPER:
        repo = CrawlNodeRepository(session)
        nodes = await repo.list_for_job(job.id, limit=10000)
        return [
            {
                "url": n.url,
                "depth": n.depth,
                "status_code": n.status_code,
                "title": n.title,
                "word_count": n.word_count,
            }
            for n in nodes
        ]
    return []


async def on_job_event(job_id: str, event: dict[str, Any]) -> None:
    """Handle job-done events — run matching pipelines."""
    if event.get("type") != "done":
        return

    try:
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(job_id)
            if not job:
                return

            job_type = job.type.value if hasattr(job.type, "value") else str(job.type)
            matching = find_pipelines_for_job_type(job_type)
            if not matching:
                return

            data = await _collect_job_data(session, job)
            logger.info("Running %d pipeline(s) for job %s (%s, %d items)",
                        len(matching), job_id[:8], job_type, len(data))

            _PIPELINE_RUNS_DIR.mkdir(parents=True, exist_ok=True)

            for p in matching:
                try:
                    result = run_pipeline(
                        p["code"], data, url=job.url, job_id=job_id
                    )
                    out_file = _PIPELINE_RUNS_DIR / f"{job_id[:8]}_{p['id']}.json"
                    out_file.write_text(
                        json.dumps({
                            "job_id": job_id,
                            "pipeline_id": p["id"],
                            "pipeline_name": p["name"],
                            "success": result.get("success"),
                            "output": result.get("output") if result.get("success") else None,
                            "error": result.get("error"),
                            "logs": result.get("logs", ""),
                        }, indent=2, default=str),
                        encoding="utf-8",
                    )
                    await event_bus.publish(job_id, {
                        "type": "log",
                        "message": f"Pipeline '{p['name']}' {'✓' if result.get('success') else '✗'} — saved to {out_file.name}",
                    })
                except Exception as e:
                    logger.warning("Pipeline '%s' failed on job %s: %s", p["name"], job_id[:8], e)
    except Exception as e:
        logger.warning("Pipeline listener error for job %s: %s", job_id[:8], e)
