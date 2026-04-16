"""In-process scheduler using APScheduler — persists schedules to SQLite.

Exposes simple CRUD: create/list/delete/toggle schedules.
Each schedule stores a tool + URL + config + cron expression.
When fired, it creates a new Job row and dispatches the runner.
"""
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services.job_manager import job_manager

# In-memory store of schedule metadata (APScheduler handles timing)
_schedules: dict[str, dict] = {}
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    return _scheduler


async def _run_scheduled(schedule_id: str) -> None:
    meta = _schedules.get(schedule_id)
    if not meta or not meta.get("enabled"):
        return

    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        jid = str(uuid.uuid4())
        job = Job(
            id=jid,
            type=meta["job_type"],
            url=meta["url"],
            status=JobStatus.PENDING,
            config=meta["config"],
            stats={},
        )
        await repo.create(job)
        await session.commit()

    # Dispatch (reuse bulk._dispatch logic inlined here for simplicity)
    from app.api.bulk import _dispatch
    _dispatch(jid, meta["job_type"], meta["config"])

    meta["last_run"] = datetime.utcnow().isoformat()
    meta["runs"] = meta.get("runs", 0) + 1


def create_schedule(
    *,
    tool: str,
    url: str,
    config: dict,
    cron_expr: str,
    label: str = "",
) -> dict:
    """Create a new scheduled job. cron_expr: '0 3 * * *' = daily at 3am."""
    from app.api.bulk import TYPE_MAP

    sid = str(uuid.uuid4())[:8]
    job_type = TYPE_MAP.get(tool)
    if not job_type:
        raise ValueError(f"Unknown tool: {tool}")

    merged_config = {**config, "url": url}

    meta = {
        "id": sid,
        "tool": tool,
        "url": url,
        "config": merged_config,
        "job_type": job_type,
        "cron": cron_expr,
        "label": label or f"{tool}: {url[:50]}",
        "enabled": True,
        "created_at": datetime.utcnow().isoformat(),
        "last_run": None,
        "runs": 0,
    }
    _schedules[sid] = meta

    sched = get_scheduler()
    sched.add_job(
        _run_scheduled,
        trigger=CronTrigger.from_crontab(cron_expr),
        args=[sid],
        id=sid,
        replace_existing=True,
    )
    return meta


def list_schedules() -> list[dict]:
    return list(_schedules.values())


def delete_schedule(sid: str) -> bool:
    if sid not in _schedules:
        return False
    sched = get_scheduler()
    try:
        sched.remove_job(sid)
    except Exception:
        pass
    del _schedules[sid]
    return True


def toggle_schedule(sid: str, enabled: bool) -> bool:
    meta = _schedules.get(sid)
    if not meta:
        return False
    meta["enabled"] = enabled
    sched = get_scheduler()
    if enabled:
        try:
            sched.resume_job(sid)
        except Exception:
            pass
    else:
        try:
            sched.pause_job(sid)
        except Exception:
            pass
    return True
