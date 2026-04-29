"""OSINT Harvester API (Phase 9)."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.osint import OSINTRequest
from app.services.event_bus import event_bus
from app.services.osint_harvester import get_harvester

logger = logging.getLogger("pyscrapr.osint")

router = APIRouter()


@router.post("/scan")
async def osint_scan(req: OSINTRequest, session: AsyncSession = Depends(get_session)):
    """Start an OSINT harvest job. Returns job_id immediately."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=422, detail="url wajib diisi")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.OSINT_HARVEST,
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    async def _run():
        async with AsyncSessionLocal() as s2:
            r2 = JobRepository(s2)
            j2 = await r2.find_by_id(job_id)
            if j2:
                j2.status = JobStatus.RUNNING
                await s2.commit()
        try:
            report = await get_harvester().harvest(
                job_id=job_id,
                url=req.url,
                max_depth=req.max_depth,
                max_pages=req.max_pages,
                stay_on_domain=req.stay_on_domain,
                filters=req.filters,
                custom_patterns=req.custom_patterns,
            )
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.DONE
                    j2.stats = {
                        **(report.get("stats") or {}),
                        "pages_crawled": report.get("pages_crawled", 0),
                        "findings_count": len(report.get("findings") or []),
                        "report": report,
                    }
                    await s2.commit()
        except Exception as e:
            logger.exception("OSINT job %s gagal: %s", job_id, e)
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.ERROR
                    j2.error_message = str(e)
                    await s2.commit()

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": JobStatus.PENDING.value}


@router.get("/scan/events/{job_id}")
async def osint_events(job_id: str):
    """SSE stream of OSINT progress."""
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/scan/{job_id}")
async def osint_get(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.OSINT_HARVEST:
        raise HTTPException(status_code=400, detail="Job bukan osint_harvest")
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "config": job.config,
        "report": report,
        "stats": {k: v for k, v in stats.items() if k != "report"} if isinstance(stats, dict) else {},
        "error_message": job.error_message,
    }


@router.get("/export/{job_id}.{fmt}")
async def osint_export(job_id: str, fmt: str, session: AsyncSession = Depends(get_session)):
    if fmt not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="Format harus csv atau json")
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.OSINT_HARVEST:
        raise HTTPException(status_code=400, detail="Job bukan osint_harvest")
    stats = job.stats or {}
    report = stats.get("report") or {}

    if fmt == "json":
        body = json.dumps(report, indent=2, ensure_ascii=False, default=str)
        headers = {"Content-Disposition": f'attachment; filename="osint_{job_id}.json"'}
        return StreamingResponse(iter([body]), media_type="application/json", headers=headers)

    # CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "subcategory", "value", "source_url", "context_snippet"])
    for f in report.get("findings", []) or []:
        writer.writerow([
            f.get("category", ""),
            f.get("subcategory", "") or "",
            f.get("value", ""),
            f.get("source_url", ""),
            (f.get("context_snippet") or "").replace("\n", " ")[:200],
        ])
    headers = {"Content-Disposition": f'attachment; filename="osint_{job_id}.csv"'}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
