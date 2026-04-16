"""Media Downloader endpoints (Phase 4)."""
import json
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import AssetDTO, JobCreatedResponse, JobDTO
from app.schemas.media import (
    MediaProbeRequest,
    MediaProbeResponse,
    MediaStartRequest,
)
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.media_downloader import media_downloader_service
from app.services.media_probe import probe

router = APIRouter()


@router.post("/probe", response_model=MediaProbeResponse)
async def probe_media(req: MediaProbeRequest):
    """Preview what a media URL will download (playlist entries, title, etc.)."""
    try:
        return await probe(str(req.url), req.use_browser_cookies)
    except Exception as e:
        raise HTTPException(400, f"Probe failed: {e}")


@router.post("/start", response_model=JobCreatedResponse)
async def start_media(
    req: MediaStartRequest,
    session: AsyncSession = Depends(get_session),
):
    # Hijack JobType.SITE_RIPPER? No — we need a new enum. For Phase 4 we'll
    # use the existing URL_MAPPER slot? No — we added the MEDIA_DOWNLOADER type.
    # Need to update the Job model enum.
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.MEDIA_DOWNLOADER,
        url=str(req.url),
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    job_manager.submit(job_id, media_downloader_service.run, req=req)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/stop/{job_id}")
async def stop_media(job_id: str):
    if not job_manager.stop(job_id):
        raise HTTPException(404, "Job not running")
    return {"ok": True}


@router.get("/jobs/{job_id}", response_model=JobDTO)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDTO.model_validate(job)


@router.get("/jobs/{job_id}/items", response_model=list[AssetDTO])
async def list_items(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = AssetRepository(session)
    items = await repo.list_for_job(job_id, limit=5000)
    return [AssetDTO.model_validate(a) for a in items]


@router.get("/jobs/{job_id}/events")
async def stream_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/file/{asset_id}")
async def download_file(
    job_id: str,
    asset_id: int,
    session: AsyncSession = Depends(get_session),
):
    repo = AssetRepository(session)
    assets = await repo.list_for_job(job_id, limit=10000)
    asset = next((a for a in assets if a.id == asset_id), None)
    if not asset or not asset.local_path:
        raise HTTPException(404, "Asset not found")
    p = Path(asset.local_path)
    if not p.exists():
        raise HTTPException(404, "File missing on disk")
    return FileResponse(str(p), filename=p.name)


@router.post("/jobs/{job_id}/open-folder")
async def open_folder(job_id: str, session: AsyncSession = Depends(get_session)):
    """Open output folder in OS file manager (cross-platform)."""
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "No output folder")
    folder = Path(job.output_dir)
    if not folder.exists():
        raise HTTPException(404, "Folder missing")
    import subprocess
    import sys
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(folder)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return {"ok": True, "path": str(folder)}
