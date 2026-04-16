"""Bulk URL queue — submit multiple URLs as separate jobs."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services.job_manager import job_manager

router = APIRouter()


class BulkSubmitRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=100)
    tool: str = Field(description="harvester | mapper | ripper | media")
    config: dict = Field(default_factory=dict, description="Shared config for all URLs")


class BulkSubmitResponse(BaseModel):
    job_ids: list[str]
    count: int


TYPE_MAP = {
    "harvester": JobType.IMAGE_HARVESTER,
    "mapper": JobType.URL_MAPPER,
    "ripper": JobType.SITE_RIPPER,
    "media": JobType.MEDIA_DOWNLOADER,
}


@router.post("/submit", response_model=BulkSubmitResponse)
async def bulk_submit(
    req: BulkSubmitRequest,
    session: AsyncSession = Depends(get_session),
):
    job_type = TYPE_MAP.get(req.tool)
    if not job_type:
        from fastapi import HTTPException
        raise HTTPException(400, f"Unknown tool: {req.tool}")

    repo = JobRepository(session)
    job_ids: list[str] = []

    for url in req.urls:
        url = url.strip()
        if not url:
            continue
        jid = str(uuid.uuid4())
        config = {**req.config, "url": url}
        job = Job(
            id=jid,
            type=job_type,
            url=url,
            status=JobStatus.PENDING,
            config=config,
            stats={},
        )
        await repo.create(job)
        job_ids.append(jid)

    await session.commit()

    # Launch jobs sequentially — dispatch runners
    for jid in job_ids:
        job = await repo.find_by_id(jid)
        if not job:
            continue
        _dispatch(jid, job.type, job.config or {})

    return BulkSubmitResponse(job_ids=job_ids, count=len(job_ids))


def _dispatch(job_id: str, job_type: JobType, config: dict) -> None:
    if job_type == JobType.IMAGE_HARVESTER:
        from app.schemas.job import HarvesterStartRequest
        from app.services.image_harvester import image_harvester_service
        req = HarvesterStartRequest.model_validate(config)
        job_manager.submit(
            job_id, image_harvester_service.run,
            url=str(req.url), filters=req.filters,
            concurrency=req.concurrency,
            include_css_bg=req.include_background_css,
            deduplicate=req.deduplicate,
        )
    elif job_type == JobType.URL_MAPPER:
        from app.schemas.mapper import MapperStartRequest
        from app.services.url_crawler import url_crawler_service
        req = MapperStartRequest.model_validate(config)
        job_manager.submit(job_id, url_crawler_service.run, req=req)
    elif job_type == JobType.SITE_RIPPER:
        from app.schemas.ripper import RipperStartRequest
        from app.services.site_ripper import site_ripper_service
        req = RipperStartRequest.model_validate(config)
        job_manager.submit(job_id, site_ripper_service.run, req=req)
    elif job_type == JobType.MEDIA_DOWNLOADER:
        from app.schemas.media import MediaStartRequest
        from app.services.media_downloader import media_downloader_service
        req = MediaStartRequest.model_validate(config)
        job_manager.submit(job_id, media_downloader_service.run, req=req)
