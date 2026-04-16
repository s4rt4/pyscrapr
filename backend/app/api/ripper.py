"""Site Ripper endpoints (Phase 3)."""
import io
import json
import uuid
import zipfile
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreatedResponse, JobDTO
from app.schemas.ripper import RipperStartRequest
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.site_ripper import site_ripper_service

router = APIRouter()


@router.post("/start", response_model=JobCreatedResponse)
async def start_ripper(
    req: RipperStartRequest,
    session: AsyncSession = Depends(get_session),
):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SITE_RIPPER,
        url=str(req.url),
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    job_manager.submit(job_id, site_ripper_service.run, req=req)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/stop/{job_id}")
async def stop_ripper(job_id: str):
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


@router.get("/jobs/{job_id}/events")
async def stream_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/report")
async def get_report(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "Job or output folder not found")
    report_path = Path(job.output_dir) / "_report.pdf"
    if not report_path.exists():
        raise HTTPException(404, "Report not generated yet")
    return FileResponse(
        str(report_path),
        media_type="application/pdf",
        filename=f"ripper-report-{job_id[:8]}.pdf",
    )


@router.get("/jobs/{job_id}/zip")
async def download_zip(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "Job or output folder not found")
    folder = Path(job.output_dir)
    if not folder.exists():
        raise HTTPException(404, "Output folder missing on disk")

    def iter_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in folder.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(folder))
        buf.seek(0)
        yield from iter(lambda: buf.read(65536), b"")

    return StreamingResponse(
        iter_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="mirror-{job_id[:8]}.zip"'},
    )
