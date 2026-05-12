"""Job history listing + re-run + delete."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete as sql_delete
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


@router.delete("/{job_id}")
async def delete_job(job_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a single job. Refuses to delete RUNNING jobs (stop them first)."""
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status == JobStatus.RUNNING:
        raise HTTPException(409, "Hentikan job dulu sebelum hapus")
    await session.execute(sql_delete(Job).where(Job.id == job_id))
    await session.commit()
    return {"ok": True, "deleted": job_id}


@router.delete("")
async def bulk_delete_jobs(
    job_type: Optional[JobType] = None,
    status: Optional[JobStatus] = None,
    older_than_days: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    """Bulk delete jobs by filter. At least one filter is required to prevent
    accidental wipe. RUNNING jobs are always skipped."""
    if job_type is None and status is None and older_than_days is None:
        raise HTTPException(400, "Minimal satu filter wajib (job_type, status, atau older_than_days)")
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    conds = [Job.status != JobStatus.RUNNING]
    if job_type is not None:
        conds.append(Job.type == job_type)
    if status is not None:
        conds.append(Job.status == status)
    if older_than_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        conds.append(Job.created_at < cutoff)
    # Count first for response
    count_stmt = select(Job.id).where(and_(*conds))
    res = await session.execute(count_stmt)
    ids = [row[0] for row in res.all()]
    if ids:
        await session.execute(sql_delete(Job).where(Job.id.in_(ids)))
        await session.commit()
    return {"ok": True, "deleted_count": len(ids), "deleted_ids": ids}
