"""System monitor - CPU, RAM, network speed, traffic counters, dashboard summary."""
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType

router = APIRouter()

# Track traffic since app start
_start_time: float = time.time()
_start_counters = psutil.net_io_counters()
_prev_counters = _start_counters
_prev_time: float = _start_time


@router.get("/stats")
async def system_stats():
    global _prev_counters, _prev_time

    now = time.time()
    dt = now - _prev_time
    if dt < 0.1:
        dt = 0.1  # prevent division by zero

    current = psutil.net_io_counters()

    # Speed (bytes/sec since last poll) — clamp to 0 if counters reset
    up_speed = max(0, (current.bytes_sent - _prev_counters.bytes_sent)) / dt
    down_speed = max(0, (current.bytes_recv - _prev_counters.bytes_recv)) / dt

    # Traffic since app start — clamp to 0
    up_total = max(0, current.bytes_sent - _start_counters.bytes_sent)
    down_total = max(0, current.bytes_recv - _start_counters.bytes_recv)

    _prev_counters = current
    _prev_time = now

    # CPU + RAM
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(logical=True),
        },
        "ram": {
            "percent": mem.percent,
            "used_gb": round(mem.used / 1073741824, 2),
            "total_gb": round(mem.total / 1073741824, 2),
        },
        "network": {
            "upload_speed": round(up_speed),       # bytes/sec
            "download_speed": round(down_speed),   # bytes/sec
            "upload_today": up_total,               # bytes since app start
            "download_today": down_total,           # bytes since app start
        },
        "uptime_seconds": round(now - _start_time),
    }


def _dir_size(path: Path) -> int:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except Exception:
        return 0


@router.get("/dashboard")
async def dashboard_summary(session: AsyncSession = Depends(get_session)):
    """Aggregate stats for the dashboard page."""
    # Jobs by type + status
    stmt = select(Job.type, Job.status, func.count()).group_by(Job.type, Job.status)
    result = await session.execute(stmt)
    by_type: dict[str, dict] = {}
    for job_type, status, count in result.all():
        t = job_type.value if hasattr(job_type, "value") else str(job_type)
        s = status.value if hasattr(status, "value") else str(status)
        by_type.setdefault(t, {"total": 0, "done": 0, "error": 0, "running": 0})
        by_type[t]["total"] += count
        if s == "done":
            by_type[t]["done"] += count
        elif s == "error":
            by_type[t]["error"] += count
        elif s == "running":
            by_type[t]["running"] += count

    # Recent 5 jobs
    stmt2 = select(Job).order_by(Job.created_at.desc()).limit(5)
    result2 = await session.execute(stmt2)
    recent = [
        {
            "id": j.id,
            "type": j.type.value if hasattr(j.type, "value") else str(j.type),
            "url": j.url,
            "status": j.status.value if hasattr(j.status, "value") else str(j.status),
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "stats": j.stats or {},
        }
        for j in result2.scalars().all()
    ]

    # Disk usage
    dl_size = _dir_size(settings.download_dir)
    data_size = _dir_size(settings.data_dir)
    disk = psutil.disk_usage(str(settings.base_dir))

    return {
        "jobs_by_type": by_type,
        "recent_jobs": recent,
        "disk": {
            "downloads_bytes": dl_size,
            "data_bytes": data_size,
            "disk_free_gb": round(disk.free / 1073741824, 2),
            "disk_total_gb": round(disk.total / 1073741824, 2),
        },
    }


@router.get("/dashboard/timeseries")
async def dashboard_timeseries(
    days: int = 14,
    session: AsyncSession = Depends(get_session),
):
    """Return job counts per day for the last N days, grouped by status.

    Response: {"days": [{"date": "YYYY-MM-DD", "total": int, "done": int, "error": int}, ...]}
    """
    days = max(1, min(days, 90))
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    day_col = func.date(Job.created_at)
    stmt = (
        select(day_col, Job.status, func.count())
        .where(Job.created_at >= start_dt)
        .group_by(day_col, Job.status)
    )
    result = await session.execute(stmt)

    buckets: dict[str, dict] = {}
    for d in (start_date + timedelta(days=i) for i in range(days)):
        buckets[d.isoformat()] = {"date": d.isoformat(), "total": 0, "done": 0, "error": 0}

    for raw_day, status, count in result.all():
        # SQLite returns string from func.date(); other backends may return date object
        if isinstance(raw_day, date):
            key = raw_day.isoformat()
        else:
            key = str(raw_day)[:10]
        if key not in buckets:
            continue
        s = status.value if hasattr(status, "value") else str(status)
        buckets[key]["total"] += count
        if s == "done":
            buckets[key]["done"] += count
        elif s == "error":
            buckets[key]["error"] += count

    return {"days": list(buckets.values())}
