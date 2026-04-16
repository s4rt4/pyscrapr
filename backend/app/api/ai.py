"""AI Tools endpoints (Phase 5)."""
import json
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.ai import TaggingStartRequest, TaggingResponse, TagResult
from app.schemas.job import JobCreatedResponse, JobDTO
from app.services.ai_orchestrator import ai_orchestrator
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager

router = APIRouter()


@router.post("/tag/start", response_model=JobCreatedResponse)
async def start_tagging(
    req: TaggingStartRequest,
    session: AsyncSession = Depends(get_session),
):
    # Verify harvester job exists
    repo = JobRepository(session)
    harvester_job = await repo.find_by_id(req.harvester_job_id)
    if not harvester_job:
        raise HTTPException(404, "Harvester job not found")
    if harvester_job.type != JobType.IMAGE_HARVESTER:
        raise HTTPException(400, "Not an Image Harvester job")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.AI_TAGGING,
        url=harvester_job.url,
        status=JobStatus.PENDING,
        config={"harvester_job_id": req.harvester_job_id, "labels": req.labels},
        stats={},
    )
    await repo.create(job)
    await session.commit()

    job_manager.submit(
        job_id,
        ai_orchestrator.run,
        harvester_job_id=req.harvester_job_id,
        labels=req.labels,
    )
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/tag/stop/{job_id}")
async def stop_tagging(job_id: str):
    if not job_manager.stop(job_id):
        raise HTTPException(404, "Job not running")
    return {"ok": True}


@router.get("/tag/jobs/{job_id}", response_model=JobDTO)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDTO.model_validate(job)


@router.get("/tag/jobs/{job_id}/results", response_model=TaggingResponse)
async def get_results(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "Results not ready")
    p = Path(job.output_dir)
    if not p.exists():
        raise HTTPException(404, "Results file missing")
    data = json.loads(p.read_text())
    return TaggingResponse(
        job_id=data["job_id"],
        harvester_job_id=data["harvester_job_id"],
        total_images=data["total_images"],
        tagged=data["tagged"],
        results=[TagResult(**r) for r in data["results"]],
    )


@router.get("/tag/jobs/{job_id}/events")
async def stream_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/harvester-jobs", response_model=list[JobDTO])
async def list_harvester_jobs(session: AsyncSession = Depends(get_session)):
    """List completed Image Harvester jobs for selection."""
    repo = JobRepository(session)
    jobs = await repo.list_recent(limit=50, job_type=JobType.IMAGE_HARVESTER)
    return [JobDTO.model_validate(j) for j in jobs if j.status == JobStatus.DONE]
