"""SEO auditor endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.seo import SeoAuditRequest, SeoAuditResponse
from app.services.seo_auditor import get_auditor

logger = logging.getLogger("pyscrapr.seo")

router = APIRouter()


@router.post("/audit", response_model=SeoAuditResponse)
async def audit_seo(
    req: SeoAuditRequest,
    session: AsyncSession = Depends(get_session),
) -> SeoAuditResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SEO_AUDIT,
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
        result = await get_auditor().audit(req.url, timeout=req.timeout)
    except Exception as e:
        logger.exception("SEO audit failed for %s: %s", req.url, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Audit gagal: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "score": result["score"],
        "issues_count": len(result["issues"]),
        "word_count": result["word_count"],
    }
    await session.commit()
    return SeoAuditResponse(**result)
