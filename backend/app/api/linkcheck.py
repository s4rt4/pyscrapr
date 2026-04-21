"""Broken link checker endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.linkcheck import LinkCheckRequest, LinkCheckResponse
from app.services.link_checker import get_checker

logger = logging.getLogger("pyscrapr.linkcheck")

router = APIRouter()


@router.post("/scan", response_model=LinkCheckResponse)
async def scan_links(
    req: LinkCheckRequest,
    session: AsyncSession = Depends(get_session),
) -> LinkCheckResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.LINK_CHECK,
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
        result = await get_checker().check(
            req.url,
            max_pages=req.max_pages,
            timeout=req.timeout,
            stay_on_domain=req.stay_on_domain,
        )
    except Exception as e:
        logger.exception("Link check failed for %s: %s", req.url, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Scan gagal: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "total_pages": result["total_pages"],
        "total_links": result["total_links"],
        "broken_count": result["broken_count"],
    }
    await session.commit()
    return LinkCheckResponse(**result)
