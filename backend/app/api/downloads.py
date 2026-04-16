"""Download bundle endpoints — zip output folder of a job."""
import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.job_repository import JobRepository

router = APIRouter()


@router.get("/{job_id}/zip")
async def download_zip(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "Job or output folder not found")

    folder = Path(job.output_dir)
    if not folder.exists():
        raise HTTPException(404, "Output folder missing on disk")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(folder))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.zip"'},
    )
