"""Security headers scanner endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.security import SecurityScanRequest, SecurityScanResponse
from app.services.security_scanner import get_scanner

logger = logging.getLogger("pyscrapr.security")

router = APIRouter()


@router.post("/scan", response_model=SecurityScanResponse)
async def scan_security(
    req: SecurityScanRequest,
    session: AsyncSession = Depends(get_session),
) -> SecurityScanResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SECURITY_SCAN,
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
        result = await get_scanner().scan(req.url, timeout=req.timeout)
    except Exception as e:
        logger.exception("Security scan failed for %s: %s", req.url, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Scan gagal: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "score": result["score"],
        "grade": result["grade"],
        "headers_missing": len(result["headers_missing"]),
    }
    await session.commit()
    return SecurityScanResponse(**result)
