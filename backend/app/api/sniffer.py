"""API Sniffer (P12) endpoints."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.api_sniffer import SniffRequest, SniffResponse
from app.services.api_sniffer import (
    build_openapi,
    build_postman,
    sniff,
    strip_raw_for_storage,
)

logger = logging.getLogger("pyscrapr.api_sniffer")

router = APIRouter()


def _job_type():
    """Resolve JobType.API_SNIFF if available, else fall back gracefully."""
    return getattr(JobType, "API_SNIFF", JobType.TECH_DETECTOR)


@router.post("/scan")
async def sniffer_scan(
    req: SniffRequest, session: AsyncSession = Depends(get_session)
):
    """Start an API sniff job. Returns job_id immediately; poll /scan/{job_id}."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=422, detail="url wajib diisi")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=_job_type(),
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
            report = await sniff(
                req.url,
                wait_seconds=req.wait_seconds,
                max_requests=req.max_requests,
                filter_static=req.filter_static,
                use_stealth=req.use_stealth,
            )
            stored = {
                "report": report,  # keep _raw_requests for export endpoints
                "total_requests": report.get("stats", {}).get("total_requests", 0),
                "unique_endpoints": report.get("stats", {}).get("unique_endpoints", 0),
                "graphql_ops": report.get("stats", {}).get("graphql_ops", 0),
            }
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.DONE
                    j2.stats = stored
                    await s2.commit()
        except Exception as e:
            logger.exception("API sniff job %s gagal: %s", job_id, e)
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.ERROR
                    j2.error_message = str(e)
                    await s2.commit()

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": JobStatus.PENDING.value}


@router.get("/scan/{job_id}")
async def sniffer_get(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    # Don't leak _raw_requests to the API consumer
    if isinstance(report, dict):
        report = strip_raw_for_storage(report)
    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "config": job.config,
        "report": report,
        "error_message": job.error_message,
    }


def _load_report(job: Job) -> dict:
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    if not isinstance(report, dict):
        raise HTTPException(status_code=400, detail="Report belum tersedia")
    return report


@router.get("/scan/{job_id}/openapi.json")
async def sniffer_openapi(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    report = _load_report(job)
    spec = build_openapi(report)
    headers = {
        "Content-Disposition": f'attachment; filename="openapi_{job_id}.json"'
    }
    return StreamingResponse(
        iter([json.dumps(spec, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers=headers,
    )


@router.get("/scan/{job_id}/postman.json")
async def sniffer_postman(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    report = _load_report(job)
    coll = build_postman(report)
    headers = {
        "Content-Disposition": f'attachment; filename="postman_{job_id}.json"'
    }
    return StreamingResponse(
        iter([json.dumps(coll, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers=headers,
    )


_ = SniffResponse  # re-export marker for schema discovery tools
