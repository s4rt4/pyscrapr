"""Website technology stack detector endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.tech import (
    TechMatch,
    TechScanRequest,
    TechScanResponse,
    TechStatsResponse,
)
from app.services.tech_detector import get_detector

logger = logging.getLogger("pyscrapr.tech_detector")

router = APIRouter()


@router.post("/scan", response_model=TechScanResponse)
async def scan_tech(
    req: TechScanRequest,
    session: AsyncSession = Depends(get_session),
) -> TechScanResponse:
    """Fetch a URL, match against Wappalyzer rules, persist a Job row."""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.TECH_DETECTOR,
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    job.status = JobStatus.RUNNING
    await session.flush()

    detector = get_detector()
    try:
        result = await detector.detect(
            req.url,
            timeout=req.timeout,
            use_playwright=req.use_playwright,
        )
    except Exception as e:
        logger.exception("Tech detection failed for %s: %s", req.url, e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")

    job.status = JobStatus.DONE
    job.stats = {
        "technologies_count": len(result["technologies"]),
        "categories_count": len(result["by_category"]),
        "status_code": result["status_code"],
    }
    await session.commit()

    techs = [TechMatch(**t) for t in result["technologies"]]
    by_cat = {k: [TechMatch(**t) for t in v] for k, v in result["by_category"].items()}

    return TechScanResponse(
        url=result["url"],
        final_url=result["final_url"],
        status_code=result["status_code"],
        fetched_at=result["fetched_at"],
        technologies=techs,
        by_category=by_cat,
    )


@router.get("/stats", response_model=TechStatsResponse)
async def tech_stats() -> TechStatsResponse:
    """Return counts of loaded Wappalyzer rules - used by UI tooltip."""
    detector = get_detector()
    return TechStatsResponse(
        technologies_count=len(detector.techs),
        categories_count=len(detector.categories),
    )
