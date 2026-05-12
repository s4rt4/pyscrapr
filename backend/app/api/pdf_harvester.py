"""PDF Harvester API endpoints."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.pdf_harvester import PdfHarvestRequest
from app.services.event_bus import event_bus
from app.services.pdf_harvester import get_harvester
from app.services.pdf_search_index import get_index

logger = logging.getLogger("pyscrapr.pdf_harvester")

router = APIRouter()


def _job_type() -> JobType:
    """Resolve PDF_HARVEST JobType, fall back to OSINT_HARVEST if not yet wired."""
    try:
        return JobType.PDF_HARVEST  # type: ignore[attr-defined]
    except AttributeError:
        return JobType.OSINT_HARVEST


@router.post("/scan")
async def pdf_scan(
    req: PdfHarvestRequest,
    session: AsyncSession = Depends(get_session),
):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=422, detail="url wajib diisi")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=_job_type(),
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    async def _run():
        async with AsyncSessionLocal() as s2:
            r2 = JobRepository(s2)
            j2 = await r2.find_by_id(job_id)
            if j2:
                j2.status = JobStatus.RUNNING
                await s2.commit()
        try:
            report = await get_harvester().harvest(
                req.url,
                job_id=job_id,
                max_depth=req.max_depth,
                max_pages=req.max_pages,
                max_pdfs=req.max_pdfs,
                download=req.download,
                extract_text=req.extract_text,
            )
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.DONE
                    j2.stats = {
                        **(report.get("stats") or {}),
                        "report": report,
                    }
                    await s2.commit()
        except Exception as e:
            logger.exception("PDF harvest job %s gagal: %s", job_id, e)
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.ERROR
                    j2.error_message = str(e)
                    await s2.commit()

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": JobStatus.PENDING.value}


@router.get("/scan/events/{job_id}")
async def pdf_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/scan/{job_id}")
async def pdf_get(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "config": job.config,
        "report": report,
        "stats": {k: v for k, v in stats.items() if k != "report"} if isinstance(stats, dict) else {},
        "error_message": job.error_message,
    }


@router.get("/scan/{job_id}/search")
async def pdf_search(
    job_id: str,
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")

    index = get_index()
    hits = index.search(job_id, q)

    # If index is empty (e.g., after restart), fall back to scanning the stored report.
    if not hits:
        stats = job.stats or {}
        report = stats.get("report") if isinstance(stats, dict) else None
        if report and report.get("documents"):
            ql = q.lower()
            for d in report["documents"]:
                text = d.get("text_content") or ""
                if not text:
                    continue
                lower = text.lower()
                idx = lower.find(ql)
                if idx < 0:
                    continue
                a = max(0, idx - 40)
                b = min(len(text), idx + len(q) + 40)
                hits.append({
                    "pdf_id": d.get("pdf_id"),
                    "snippet": text[a:b].replace("\n", " ").strip(),
                    "match_count": lower.count(ql),
                })
            hits.sort(key=lambda r: -r["match_count"])

    return {"job_id": job_id, "query": q, "hits": hits, "total": len(hits)}


@router.get("/scan/{job_id}/file/{pdf_id}")
async def pdf_file(
    job_id: str, pdf_id: str, session: AsyncSession = Depends(get_session)
):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    doc = next((d for d in report.get("documents", []) if d.get("pdf_id") == pdf_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF tidak ditemukan")
    local_path = doc.get("local_path")
    if not local_path or not Path(local_path).exists():
        raise HTTPException(status_code=410, detail="File sudah tidak tersedia")
    return FileResponse(
        local_path,
        media_type="application/pdf",
        filename=doc.get("filename") or "document.pdf",
    )


@router.get("/scan/{job_id}/export.csv")
async def pdf_export_csv(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    report = stats.get("report") if isinstance(stats, dict) else None
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "pdf_id", "filename", "url", "title", "author",
        "page_count", "file_size", "creation_date", "downloaded", "error",
    ])
    for d in report.get("documents", []) or []:
        writer.writerow([
            d.get("pdf_id", ""),
            d.get("filename", ""),
            d.get("url", ""),
            (d.get("title") or "").replace("\n", " "),
            (d.get("author") or "").replace("\n", " "),
            d.get("page_count") or "",
            d.get("file_size") or 0,
            d.get("creation_date") or "",
            "yes" if d.get("downloaded") else "no",
            (d.get("error") or "")[:200],
        ])
    headers = {"Content-Disposition": f'attachment; filename="pdf_harvest_{job_id}.csv"'}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
