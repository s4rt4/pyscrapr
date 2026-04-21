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
from pydantic import BaseModel

from app.schemas.screenshot import VideoRequest, VideoResponse
from app.services.screenshot_video import get_video

logger = logging.getLogger("pyscrapr.screenshot")

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
# Allow optional _trim suffix before the extension
_FILE_RE = re.compile(
    r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(_trim)?$"
)
_EXT_RE = re.compile(r"^(mp4|gif|webm)$")


class VideoTrimRequest(BaseModel):
    job_id: str
    start_seconds: float = 0.0
    end_seconds: float | None = None
    output_format: str = "mp4"


class VideoTrimResponse(BaseModel):
    file_url: str
    file_path: str
    file_size_bytes: int
    duration_ms: int
    output_format: str
    start_seconds: float
    end_seconds: float | None = None


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


@router.get("/file/{name}.{ext}")
async def get_video_file(name: str, ext: str):
    """Serve original video or trimmed variant ({job_id} or {job_id}_trim)."""
    if not _FILE_RE.match(name):
        raise HTTPException(status_code=400, detail="Format nama file tidak valid")
    if not _EXT_RE.match(ext):
        raise HTTPException(status_code=400, detail="Ekstensi tidak didukung")
    path = _video_dir() / f"video_{name}.{ext}"
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
        filename=f"video_{name}.{ext}",
    )


@router.post("/trim", response_model=VideoTrimResponse)
async def trim_video(req: VideoTrimRequest) -> VideoTrimResponse:
    """Trim an existing video by start/end seconds, producing a _trim variant."""
    if not _UUID_RE.match(req.job_id):
        raise HTTPException(status_code=400, detail="Format job_id tidak valid")
    # Locate the source video: look for any of the 3 extensions
    vid_dir = _video_dir()
    source: Path | None = None
    for ext in ("mp4", "webm", "gif"):
        candidate = vid_dir / f"video_{req.job_id}.{ext}"
        if candidate.exists():
            source = candidate
            break
    if source is None:
        raise HTTPException(status_code=404, detail="Video asal tidak ditemukan")

    fmt = req.output_format.lower()
    if fmt not in {"mp4", "webm", "gif"}:
        raise HTTPException(status_code=422, detail="Format output tidak didukung")

    video = get_video()
    try:
        result = await video.trim(
            source_path=source,
            output_dir=vid_dir,
            job_id=req.job_id,
            start_seconds=max(0.0, float(req.start_seconds)),
            end_seconds=(
                float(req.end_seconds) if req.end_seconds is not None else None
            ),
            output_format=fmt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        err = str(exc) or f"{type(exc).__name__}: {exc.args!r}"
        logger.exception("Video trim failed for %s: %s", req.job_id, err)
        raise HTTPException(status_code=500, detail=f"Trim gagal: {err}")

    return VideoTrimResponse(
        file_url=result["file_url"],
        file_path=result["file_path"],
        file_size_bytes=result["file_size_bytes"],
        duration_ms=result["duration_ms"],
        output_format=result["output_format"],
        start_seconds=result["start_seconds"],
        end_seconds=result["end_seconds"],
    )
