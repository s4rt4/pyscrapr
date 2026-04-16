"""Job history listing + re-run."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreatedResponse, JobDTO
from app.services.job_manager import job_manager

router = APIRouter()


@router.get("", response_model=list[JobDTO])
async def list_history(
    limit: int = 50,
    job_type: Optional[JobType] = None,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    jobs = await repo.list_recent(limit=limit, job_type=job_type)
    return [JobDTO.model_validate(j) for j in jobs]


@router.post("/rerun/{job_id}", response_model=JobCreatedResponse)
async def rerun_job(job_id: str, session: AsyncSession = Depends(get_session)):
    """Clone a job's config and start a new run."""
    repo = JobRepository(session)
    original = await repo.find_by_id(job_id)
    if not original:
        raise HTTPException(404, "Job not found")

    new_id = str(uuid.uuid4())
    new_job = Job(
        id=new_id,
        type=original.type,
        url=original.url,
        status=JobStatus.PENDING,
        config=original.config or {},
        stats={},
    )
    await repo.create(new_job)
    await session.commit()

    # Dispatch to the right service based on type
    if original.type == JobType.IMAGE_HARVESTER:
        from app.schemas.job import HarvesterStartRequest
        from app.services.image_harvester import image_harvester_service
        req = HarvesterStartRequest.model_validate(original.config)
        job_manager.submit(
            new_id, image_harvester_service.run,
            url=str(req.url), filters=req.filters,
            concurrency=req.concurrency,
            include_css_bg=req.include_background_css,
            deduplicate=req.deduplicate,
        )
    elif original.type == JobType.URL_MAPPER:
        from app.schemas.mapper import MapperStartRequest
        from app.services.url_crawler import url_crawler_service
        req = MapperStartRequest.model_validate(original.config)
        job_manager.submit(new_id, url_crawler_service.run, req=req)
    elif original.type == JobType.SITE_RIPPER:
        from app.schemas.ripper import RipperStartRequest
        from app.services.site_ripper import site_ripper_service
        req = RipperStartRequest.model_validate(original.config)
        job_manager.submit(new_id, site_ripper_service.run, req=req)
    elif original.type == JobType.MEDIA_DOWNLOADER:
        from app.schemas.media import MediaStartRequest
        from app.services.media_downloader import media_downloader_service
        req = MediaStartRequest.model_validate(original.config)
        job_manager.submit(new_id, media_downloader_service.run, req=req)
    elif original.type == JobType.AI_TAGGING:
        from app.services.ai_orchestrator import ai_orchestrator
        config = original.config or {}
        job_manager.submit(
            new_id, ai_orchestrator.run,
            harvester_job_id=config.get("harvester_job_id", ""),
            labels=config.get("labels", []),
        )
    else:
        raise HTTPException(400, f"Re-run not supported for {original.type}")

    return JobCreatedResponse(job_id=new_id, status=JobStatus.PENDING)
