"""Screenshot scroll-through video recording endpoints."""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_config
from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.screenshot import VideoRequest, VideoResponse
from app.services.screenshot_video import get_video

logger = logging.getLogger("pyscrapr.screenshot")

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_EXT_RE = re.compile(r"^(mp4|gif|webm)$")


def _video_dir() -> Path:
    d = app_config.data_dir / "screenshots" / "video"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("", response_model=VideoResponse)
async def record_video(
    req: VideoRequest,
    session: AsyncSession = Depends(get_session),
) -> VideoResponse:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SCREENSHOT,
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    job.status = JobStatus.RUNNING
    await session.flush()

    video = get_video()
    try:
        result = await video.record_scroll(
            url=req.url,
            job_id=job_id,
            output_dir=_video_dir(),
            viewport=req.viewport,
            custom_width=req.custom_width,
            custom_height=req.custom_height,
            scroll_duration_ms=req.scroll_duration_ms,
            fps=req.fps,
            output_format=req.output_format.value
            if hasattr(req.output_format, "value")
            else str(req.output_format),
            wait_until=req.wait_until,
            timeout_ms=req.timeout_ms,
            use_auth_vault=req.use_auth_vault,
        )
    except RuntimeError as exc:
        err = str(exc) or f"{type(exc).__name__}: {exc.args!r}"
        logger.error("Video runtime error for %s: %s", req.url, err)
        job.status = JobStatus.ERROR
        job.error_message = err
        await session.commit()
        raise HTTPException(status_code=503, detail=err)
    except Exception as exc:
        err = str(exc) or f"{type(exc).__name__}: {exc.args!r}"
        logger.exception("Video capture failed for %s: %s", req.url, err)
        job.status = JobStatus.ERROR
        job.error_message = err
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Perekaman gagal: {err}")

    job.status = JobStatus.DONE
    job.output_dir = str(_video_dir())
    job.stats = {
        "file_size_bytes": result["file_size_bytes"],
        "duration_ms": result["duration_ms"],
        "output_format": result["output_format"],
        "viewport_used": result["viewport_used"],
        "status": result["status"],
        "kind": "video",
    }
    await session.commit()

    return VideoResponse(
        job_id=job_id,
        file_url=result["file_url"],
        file_path=result["file_path"],
        file_size_bytes=result["file_size_bytes"],
        duration_ms=result["duration_ms"],
        output_format=result["output_format"],
        viewport_used=result["viewport_used"],
        final_url=result["final_url"],
        title=result["title"],
        status=result["status"],
    )


@router.get("/file/{job_id}.{ext}")
async def get_video_file(job_id: str, ext: str):
    if not _UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Format job_id tidak valid")
    if not _EXT_RE.match(ext):
        raise HTTPException(status_code=400, detail="Ekstensi tidak didukung")
    path = _video_dir() / f"video_{job_id}.{ext}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="File video tidak ditemukan")
    media_map = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "gif": "image/gif",
    }
    return FileResponse(
        path=str(path),
        media_type=media_map[ext],
        filename=f"video_{job_id}.{ext}",
    )
