"""Image Harvester endpoints — thin HTTP layer."""
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import (
    AssetDTO,
    HarvesterStartRequest,
    JobCreatedResponse,
    JobDTO,
)
from app.services.event_bus import event_bus
from app.services.image_harvester import image_harvester_service
from app.services.job_manager import job_manager

router = APIRouter()


@router.post("/start", response_model=JobCreatedResponse)
async def start_harvester(
    req: HarvesterStartRequest,
    session: AsyncSession = Depends(get_session),
):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.IMAGE_HARVESTER,
        url=str(req.url),
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    # Launch background task
    job_manager.submit(
        job_id,
        image_harvester_service.run,
        url=str(req.url),
        filters=req.filters,
        concurrency=req.concurrency,
        include_css_bg=req.include_background_css,
        deduplicate=req.deduplicate,
        use_playwright=req.use_playwright,
    )
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/stop/{job_id}")
async def stop_harvester(job_id: str):
    ok = job_manager.stop(job_id)
    if not ok:
        raise HTTPException(404, "Job not running")
    return {"ok": True}


@router.get("/jobs/{job_id}", response_model=JobDTO)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDTO.model_validate(job)


@router.get("/jobs/{job_id}/assets", response_model=list[AssetDTO])
async def list_assets(
    job_id: str,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
):
    repo = AssetRepository(session)
    assets = await repo.list_for_job(job_id, limit=limit)
    return [AssetDTO.model_validate(a) for a in assets]


@router.get("/jobs/{job_id}/events")
async def stream_events(job_id: str):
    """Server-Sent Events — consumed by EventSource in the frontend."""

    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
