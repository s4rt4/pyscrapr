"""SSL certificate inspector endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.ssl_inspect import SslInspectRequest, SslInspectResponse
from app.services.ssl_inspector import get_inspector

logger = logging.getLogger("pyscrapr.ssl")

router = APIRouter()


@router.post("/inspect", response_model=SslInspectResponse)
async def inspect_ssl(
    req: SslInspectRequest,
    session: AsyncSession = Depends(get_session),
) -> SslInspectResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SSL_INSPECT,
        url=req.hostname,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    job.status = JobStatus.RUNNING
    await session.flush()

    try:
        result = await get_inspector().inspect(req.hostname, port=req.port, timeout=req.timeout)
    except Exception as e:
        logger.exception("SSL inspect failed for %s: %s", req.hostname, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Inspeksi gagal: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "days_until_expiry": result.get("days_until_expiry") or 0,
        "is_expired": 1 if result.get("is_expired") else 0,
        "san_count": len(result.get("san") or []),
    }
    await session.commit()
    return SslInspectResponse(**result)
