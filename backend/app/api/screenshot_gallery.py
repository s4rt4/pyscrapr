"""Screenshot Gallery endpoints — list, delete, ZIP export of screenshot jobs."""
from __future__ import annotations

import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_config
from app.db.session import get_session
from app.models.job import Job, JobType
from app.schemas.screenshot import (
    GalleryFile,
    GalleryItem,
    GalleryResponse,
    ZipExportRequest,
)

logger = logging.getLogger("pyscrapr.screenshot")

router = APIRouter()

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

_VIEWPORT_KEYS = {
    "desktop",
    "desktop_hd",
    "laptop",
    "tablet",
    "mobile",
    "mobile_sm",
}


def _screenshot_dir() -> Path:
    d = app_config.data_dir / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_file_meta(filename: str) -> tuple[str | None, str]:
    """Return (viewport, format) best-effort from a filename."""
    lower = filename.lower()
    fmt = "png"
    for ext in ("png", "jpeg", "jpg", "webp", "pdf", "mp4", "gif", "webm"):
        if lower.endswith("." + ext):
            fmt = "jpeg" if ext == "jpg" else ext
            break
    viewport: str | None = None
    stem = filename.rsplit(".", 1)[0]
    parts = stem.split("_")
    for p in parts:
        if p in _VIEWPORT_KEYS:
            viewport = p
            break
    return viewport, fmt


def _files_for_job(job_id: str) -> list[GalleryFile]:
    folder = _screenshot_dir()
    out: list[GalleryFile] = []
    if not folder.exists():
        return out
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        name = p.name
        if job_id not in name:
            continue
        # Skip compare / video composite subdirs (handled separately)
        vp, fmt = _parse_file_meta(name)
        try:
            size = p.stat().st_size
        except OSError:
            continue
        file_url = f"/api/screenshot/file/{job_id}/{name}"
        # PDFs and videos share the same endpoint pattern if served by gallery
        out.append(
            GalleryFile(
                filename=name,
                url=file_url,
                size_bytes=size,
                viewport=vp,
                format=fmt,
            )
        )
    return out


@router.get("/gallery", response_model=GalleryResponse)
async def list_gallery(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> GalleryResponse:
    """Paginated listing of all SCREENSHOT jobs with associated files."""
    stmt = select(Job).where(Job.type == JobType.SCREENSHOT)
    count_stmt = select(func.count()).select_from(Job).where(Job.type == JobType.SCREENSHOT)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Job.url.like(like))
        count_stmt = count_stmt.where(Job.url.like(like))
    stmt = stmt.order_by(desc(Job.created_at)).limit(limit).offset(offset)

    total_res = await session.execute(count_stmt)
    total = int(total_res.scalar() or 0)

    res = await session.execute(stmt)
    jobs = list(res.scalars().all())

    items: list[GalleryItem] = []
    for job in jobs:
        created_at = getattr(job, "created_at", None)
        created_iso = created_at.isoformat() if created_at is not None else ""
        items.append(
            GalleryItem(
                job_id=job.id,
                url=job.url or "",
                created_at=created_iso,
                stats=job.stats or {},
                files=_files_for_job(job.id),
            )
        )

    return GalleryResponse(total=total, items=items)


@router.delete("/gallery/{job_id}")
async def delete_gallery_entry(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a screenshot Job row + every file on disk referencing its id."""
    if not _UUID_RE.fullmatch(job_id):
        raise HTTPException(status_code=400, detail="Format job_id tidak valid")

    res = await session.execute(select(Job).where(Job.id == job_id))
    job: Optional[Job] = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Screenshot job tidak ditemukan")

    deleted_files: list[str] = []
    folder = _screenshot_dir()
    if folder.exists():
        for p in folder.iterdir():
            if p.is_file() and job_id in p.name:
                try:
                    p.unlink()
                    deleted_files.append(p.name)
                except OSError as exc:
                    logger.warning("Gagal menghapus %s: %s", p, exc)

    await session.delete(job)
    await session.commit()

    return {"ok": True, "job_id": job_id, "deleted_files": deleted_files}


@router.post("/export/zip")
async def export_zip(
    req: ZipExportRequest,
    session: AsyncSession = Depends(get_session),
):
    """Stream a ZIP archive of screenshot files.

    If ``job_ids`` is empty, include files of ALL screenshot jobs.
    """
    stmt = select(Job).where(Job.type == JobType.SCREENSHOT)
    if req.job_ids:
        stmt = stmt.where(Job.id.in_(req.job_ids))
    res = await session.execute(stmt)
    jobs = list(res.scalars().all())
    if not jobs:
        raise HTTPException(
            status_code=404, detail="Tidak ada screenshot job yang cocok"
        )

    folder = _screenshot_dir()
    buf = io.BytesIO()
    total_files = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for job in jobs:
            for p in folder.iterdir():
                if not p.is_file() or job.id not in p.name:
                    continue
                arc = f"{job.id}/{p.name}"
                try:
                    zf.write(p, arcname=arc)
                    total_files += 1
                except OSError as exc:
                    logger.warning("Gagal menambahkan %s ke zip: %s", p, exc)
    if total_files == 0:
        raise HTTPException(
            status_code=404, detail="Tidak ada file screenshot yang tersedia"
        )
    buf.seek(0)

    filename = (
        f"screenshots_{req.job_ids[0]}.zip"
        if len(req.job_ids) == 1
        else "screenshots_bundle.zip"
    )
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
