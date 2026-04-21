"""Screenshot Generator endpoints."""
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
from app.schemas.screenshot import (
    ScreenshotDimensions,
    ScreenshotRequest,
    ScreenshotResponse,
    ViewportSpec,
    ViewportsResponse,
)
from app.services.screenshot_capture import ScreenshotCapture, get_capture

logger = logging.getLogger("pyscrapr.screenshot")

router = APIRouter()

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

_VIEWPORT_LABELS = {
    "desktop": "Desktop (1920x1080)",
    "desktop_hd": "Desktop HD (2560x1440)",
    "laptop": "Laptop (1366x768)",
    "tablet": "Tablet - iPad portrait (768x1024)",
    "mobile": "Mobile - iPhone 14 (390x844)",
    "mobile_sm": "Mobile kecil - iPhone SE (375x667)",
}


def _screenshot_dir() -> Path:
    d = app_config.data_dir / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/capture", response_model=ScreenshotResponse)
async def capture_screenshot(
    req: ScreenshotRequest,
    session: AsyncSession = Depends(get_session),
) -> ScreenshotResponse:
    """Capture a screenshot of the target URL and persist a Job row."""
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

    capture = get_capture()
    try:
        result = await capture.capture(
            url=req.url,
            output_dir=_screenshot_dir(),
            job_id=job_id,
            viewport=req.viewport,
            custom_width=req.custom_width,
            custom_height=req.custom_height,
            full_page=req.full_page,
            dark_mode=req.dark_mode,
            wait_until=req.wait_until,
            timeout_ms=req.timeout_ms,
        )
    except RuntimeError as e:
        # Surface non-empty diagnostic even if the exception has no message
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.error("Screenshot runtime error for %s: %s", req.url, err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=503, detail=err_detail)
    except Exception as e:
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.exception("Screenshot capture failed for %s: %s", req.url, err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Capture failed: {err_detail}")

    job.status = JobStatus.DONE
    job.output_dir = str(_screenshot_dir())
    job.stats = {
        "file_size_bytes": result["file_size_bytes"],
        "width": result["dimensions"]["width"],
        "height": result["dimensions"]["height"],
        "status": result["status"],
    }
    await session.commit()

    return ScreenshotResponse(
        job_id=job_id,
        file_path=result["file_path"],
        file_url=result["file_url"],
        dimensions=ScreenshotDimensions(**result["dimensions"]),
        file_size_bytes=result["file_size_bytes"],
        viewport_used=result["viewport_used"],
        dark_mode=result["dark_mode"],
        final_url=result["final_url"],
        title=result["title"],
        status=result["status"],
    )


@router.get("/file/{job_id}")
async def get_screenshot_file(job_id: str):
    """Return the captured PNG for ``job_id``."""
    if not _UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    path = _screenshot_dir() / f"screenshot_{job_id}.png"
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(
        path=str(path),
        media_type="image/png",
        filename=f"screenshot_{job_id}.png",
    )


@router.get("/viewports", response_model=ViewportsResponse)
async def list_viewports() -> ViewportsResponse:
    """Return available viewport presets (plus 'custom' option)."""
    out: list[ViewportSpec] = []
    for key, size in ScreenshotCapture.VIEWPORTS.items():
        out.append(
            ViewportSpec(
                key=key,
                label=_VIEWPORT_LABELS.get(key, key),
                width=size["width"],
                height=size["height"],
                custom=False,
            )
        )
    out.append(ViewportSpec(key="custom", label="Custom (tentukan sendiri)", custom=True))
    return ViewportsResponse(viewports=out)
