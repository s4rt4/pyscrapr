"""Exposure Scanner endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.exposure import ExposureScanRequest, ExposureScanResponse
from app.services.exposure_scanner import get_scanner

logger = logging.getLogger("pyscrapr.exposure")

router = APIRouter()


@router.post("/scan", response_model=ExposureScanResponse)
async def scan_exposure(
    req: ExposureScanRequest,
    session: AsyncSession = Depends(get_session),
) -> ExposureScanResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.EXPOSURE_SCAN,
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    job.status = JobStatus.RUNNING
    await session.flush()

    try:
        result = await get_scanner().scan(
            req.url, throttle_seconds=max(0.0, req.throttle_seconds)
        )
    except Exception as e:
        logger.exception("Exposure scan failed for %s: %s", req.url, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Scan gagal: {e}")

    job.status = JobStatus.DONE
    severities = [f["severity"] for f in result.get("findings", [])]
    job.stats = {
        "total_checked": result.get("total_checked", 0),
        "total_found": result.get("total_found", 0),
        "critical": sum(1 for s in severities if s == "critical"),
        "high": sum(1 for s in severities if s == "high"),
        "findings": result.get("findings", []),
        "base_url": result.get("base_url"),
        "scanned_at": result.get("scanned_at"),
        "error": result.get("error"),
    }
    await session.commit()
    return ExposureScanResponse(**result)


@router.get("/scan/{job_id}", response_model=ExposureScanResponse)
async def get_scan(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> ExposureScanResponse:
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or job.type != JobType.EXPOSURE_SCAN:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    return ExposureScanResponse(
        base_url=stats.get("base_url") or job.url,
        scanned_at=stats.get("scanned_at") or "",
        total_checked=stats.get("total_checked", 0),
        total_found=stats.get("total_found", 0),
        findings=stats.get("findings", []),
        error=stats.get("error"),
    )
