"""Screenshot Generator endpoints."""
from __future__ import annotations

import logging
import re
import time
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
    BatchResult,
    BatchScreenshotRequest,
    BatchScreenshotResponse,
    CaptureResult,
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
_FNAME_RE = re.compile(r"^[a-zA-Z0-9_\-.]+\.(png|jpeg|jpg|webp|pdf)$")

_VIEWPORT_LABELS = {
    "desktop": "Desktop (1920x1080)",
    "desktop_hd": "Desktop HD (2560x1440)",
    "laptop": "Laptop (1366x768)",
    "tablet": "Tablet - iPad portrait (768x1024)",
    "mobile": "Mobile - iPhone 14 (390x844)",
    "mobile_sm": "Mobile kecil - iPhone SE (375x667)",
}

_MEDIA_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "pdf": "application/pdf",
}


def _screenshot_dir() -> Path:
    d = app_config.data_dir / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_capture_results(raw: list[dict]) -> list[CaptureResult]:
    return [
        CaptureResult(
            file_path=c["file_path"],
            file_url=c["file_url"],
            file_size_bytes=c["file_size_bytes"],
            dimensions=ScreenshotDimensions(**c["dimensions"]),
            viewport_used=c["viewport_used"],
            color_scheme_used=c["color_scheme_used"],
            format=c["format"],
            element_index=c.get("element_index"),
        )
        for c in raw
    ]


@router.post("/capture", response_model=ScreenshotResponse)
async def capture_screenshot(
    req: ScreenshotRequest,
    session: AsyncSession = Depends(get_session),
) -> ScreenshotResponse:
    """Capture one or more screenshots of the target URL."""
    if not req.url:
        raise HTTPException(status_code=422, detail="URL wajib diisi")

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
    started = time.monotonic()
    try:
        result = await capture.capture(
            url=req.url,
            output_dir=_screenshot_dir(),
            job_id=job_id,
            viewports=req.viewports,
            custom_width=req.custom_width,
            custom_height=req.custom_height,
            full_page=req.full_page,
            color_scheme=req.color_scheme.value,
            device_scale=req.device_scale,
            output_format=req.output_format.value,
            jpeg_quality=req.jpeg_quality,
            element_selector=req.element_selector,
            multiple_elements=req.multiple_elements,
            hide_selectors=req.hide_selectors,
            wait_for_selector=req.wait_for_selector,
            wait_until=req.wait_until,
            scroll_through=req.scroll_through,
            timeout_ms=req.timeout_ms,
            custom_css=req.custom_css,
            watermark_text=req.watermark_text,
            watermark_position=req.watermark_position.value,
            watermark_opacity=req.watermark_opacity,
            use_auth_vault=req.use_auth_vault,
        )
    except RuntimeError as e:
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.error("Screenshot runtime error untuk %s: %s", req.url, err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=503, detail=err_detail)
    except Exception as e:
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.exception("Screenshot capture gagal untuk %s: %s", req.url, err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Capture gagal: {err_detail}")

    duration_ms = int((time.monotonic() - started) * 1000)
    captures = _to_capture_results(result["captures"])

    job.status = JobStatus.DONE
    job.output_dir = str(_screenshot_dir())
    job.stats = {
        "files_total": len(captures),
        "total_size_bytes": sum(c.file_size_bytes for c in captures),
        "status": result.get("status", 0),
        "duration_ms": duration_ms,
    }
    await session.commit()

    return ScreenshotResponse(
        job_id=job_id,
        url=req.url,
        final_url=result.get("final_url", req.url),
        title=result.get("title", ""),
        status=result.get("status", 0),
        captures=captures,
        duration_ms=duration_ms,
    )


@router.post("/batch", response_model=BatchScreenshotResponse)
async def capture_batch(
    req: BatchScreenshotRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchScreenshotResponse:
    """Capture screenshots for many URLs using one shared browser."""
    urls = [u.strip() for u in req.urls if u and u.strip()]
    if not urls:
        raise HTTPException(status_code=422, detail="Daftar URL kosong")

    job_id = str(uuid.uuid4())
    cfg = req.model_dump(mode="json")
    job = Job(
        id=job_id,
        type=JobType.SCREENSHOT,
        url=urls[0],
        status=JobStatus.RUNNING,
        config=cfg,
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.flush()

    capture = get_capture()
    started = time.monotonic()
    try:
        raw_results = await capture.capture_batch(
            urls=urls,
            output_dir=_screenshot_dir(),
            job_id=job_id,
            concurrency=3,
            viewports=req.viewports,
            custom_width=req.custom_width,
            custom_height=req.custom_height,
            full_page=req.full_page,
            color_scheme=req.color_scheme.value,
            device_scale=req.device_scale,
            output_format=req.output_format.value,
            jpeg_quality=req.jpeg_quality,
            element_selector=req.element_selector,
            multiple_elements=req.multiple_elements,
            hide_selectors=req.hide_selectors,
            wait_for_selector=req.wait_for_selector,
            wait_until=req.wait_until,
            scroll_through=req.scroll_through,
            timeout_ms=req.timeout_ms,
            custom_css=req.custom_css,
            watermark_text=req.watermark_text,
            watermark_position=req.watermark_position.value,
            watermark_opacity=req.watermark_opacity,
            use_auth_vault=req.use_auth_vault,
        )
    except RuntimeError as e:
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.error("Batch screenshot runtime error: %s", err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=503, detail=err_detail)
    except Exception as e:
        err_detail = str(e) or f"{type(e).__name__}: {e.args!r}"
        logger.exception("Batch screenshot gagal: %s", err_detail)
        job.status = JobStatus.ERROR
        job.error_message = err_detail
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Batch gagal: {err_detail}")

    duration_ms = int((time.monotonic() - started) * 1000)
    results: list[BatchResult] = []
    ok = 0
    err = 0
    total_files = 0
    for r in raw_results:
        caps = _to_capture_results(r.get("captures") or [])
        total_files += len(caps)
        if r.get("error"):
            err += 1
        else:
            ok += 1
        results.append(
            BatchResult(
                url=r["url"],
                captures=caps,
                final_url=r.get("final_url", r["url"]),
                status=r.get("status", 0),
                error=r.get("error"),
            )
        )

    job.status = JobStatus.DONE
    job.output_dir = str(_screenshot_dir())
    job.stats = {
        "urls_total": len(urls),
        "urls_ok": ok,
        "urls_error": err,
        "total_files": total_files,
        "duration_ms": duration_ms,
    }
    await session.commit()

    return BatchScreenshotResponse(
        job_id=job_id,
        total_urls=len(urls),
        ok_count=ok,
        error_count=err,
        results=results,
        duration_ms=duration_ms,
    )


@router.get("/file/{job_id}/{filename}")
async def get_screenshot_file_named(job_id: str, filename: str):
    """Serve a named screenshot sub-file for a job."""
    if not _UUID_RE.match(job_id.split("_")[0]):
        raise HTTPException(status_code=400, detail="Format job_id tidak valid")
    if not _FNAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Nama file tidak valid")
    # Prevent traversal: filename must not contain separators (regex already blocks).
    path = _screenshot_dir() / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File screenshot tidak ditemukan")
    ext = filename.rsplit(".", 1)[-1].lower()
    return FileResponse(
        path=str(path),
        media_type=_MEDIA_TYPES.get(ext, "application/octet-stream"),
        filename=filename,
    )


@router.get("/file/{job_id}")
async def get_screenshot_file(job_id: str):
    """Backward-compat endpoint. Returns the first PNG matching the job_id."""
    if not _UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Format job_id tidak valid")
    base = _screenshot_dir()
    # Legacy single-file name
    legacy = base / f"screenshot_{job_id}.png"
    if legacy.exists():
        return FileResponse(path=str(legacy), media_type="image/png", filename=legacy.name)
    # New scheme: pick first match
    for candidate in sorted(base.glob(f"screenshot_{job_id}_*")):
        if candidate.is_file():
            ext = candidate.suffix.lstrip(".").lower()
            return FileResponse(
                path=str(candidate),
                media_type=_MEDIA_TYPES.get(ext, "application/octet-stream"),
                filename=candidate.name,
            )
    raise HTTPException(status_code=404, detail="Screenshot tidak ditemukan")


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
