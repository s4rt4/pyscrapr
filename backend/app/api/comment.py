"""Comment Harvester API (P11)."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.comment import CommentHarvestRequest
from app.services.comment_harvester import harvest
from app.services.event_bus import event_bus

logger = logging.getLogger("pyscrapr.comment")

router = APIRouter()


def _job_type():
    """Resolve JobType.COMMENT_HARVEST if available, else fall back to OSINT_HARVEST.

    The orchestrator wires COMMENT_HARVEST into models/job.py separately; this
    keeps the module importable even before that wiring lands.
    """
    return getattr(JobType, "COMMENT_HARVEST", JobType.OSINT_HARVEST)


@router.post("/harvest")
async def comment_harvest(
    req: CommentHarvestRequest, session: AsyncSession = Depends(get_session)
):
    """Start a comment harvesting job. Returns job_id immediately."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=422, detail="url wajib diisi")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=_job_type(),
        url=req.url,
        status=JobStatus.PENDING,
        config=req.model_dump(),
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
            report = await harvest(
                req.url,
                max_comments=req.max_comments,
                include_replies=req.include_replies,
                sentiment=req.sentiment_enabled,
                job_id=job_id,
            )
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.DONE
                    j2.stats = {
                        "platform": report.get("platform"),
                        "total_comments": report.get("total_comments", 0),
                        "total_replies": report.get("total_replies", 0),
                        "max_depth": report.get("max_depth", 0),
                        "report": report,
                    }
                    await s2.commit()
        except Exception as e:
            logger.exception("Comment harvest job %s gagal: %s", job_id, e)
            await event_bus.publish(job_id, {"type": "error", "message": str(e)})
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(job_id)
                if j2:
                    j2.status = JobStatus.ERROR
                    j2.error_message = str(e)
                    await s2.commit()

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": JobStatus.PENDING.value}


@router.get("/harvest/events/{job_id}")
async def comment_events(job_id: str):
    """SSE stream of harvest progress."""

    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/harvest/{job_id}")
async def comment_get(job_id: str, session: AsyncSession = Depends(get_session)):
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


def _flatten_for_csv(nodes: list[dict], rows: list[list], path: str = "") -> None:
    for i, n in enumerate(nodes):
        node_path = f"{path}.{i}" if path else str(i)
        sent = n.get("sentiment") or {}
        rows.append([
            node_path,
            n.get("depth", 0),
            n.get("id") or "",
            n.get("author") or "",
            n.get("timestamp") or "",
            n.get("upvotes") if n.get("upvotes") is not None else "",
            sent.get("label") or "",
            sent.get("confidence") if sent.get("confidence") is not None else "",
            (n.get("text") or "").replace("\n", " ").replace("\r", " ")[:1000],
        ])
        kids = n.get("replies") or []
        if kids:
            _flatten_for_csv(kids, rows, node_path)


@router.get("/harvest/export/{job_id}.csv")
async def comment_export_csv(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    stats = job.stats or {}
    report = stats.get("report") or {}
    comments = report.get("comments") or []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "path", "depth", "id", "author", "timestamp", "upvotes",
        "sentiment_label", "sentiment_confidence", "text",
    ])
    rows: list[list] = []
    _flatten_for_csv(comments, rows)
    for r in rows:
        writer.writerow(r)

    headers = {"Content-Disposition": f'attachment; filename="comments_{job_id}.csv"'}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
