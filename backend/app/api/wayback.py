"""Wayback Machine Explorer endpoints."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services import wayback

logger = logging.getLogger("pyscrapr.wayback")

router = APIRouter()


class SaveRequest(BaseModel):
    url: str


@router.get("/snapshots")
async def snapshots(
    url: str = Query(..., description="Target URL"),
    from_year: Optional[int] = Query(None, alias="from"),
    to_year: Optional[int] = Query(None, alias="to"),
    limit: int = Query(200, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
) -> dict:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.WAYBACK_LOOKUP,
        url=url,
        status=JobStatus.RUNNING,
        config={"from": from_year, "to": to_year, "limit": limit},
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    try:
        rows = await wayback.list_snapshots(url, from_year, to_year, limit)
    except Exception as e:
        logger.exception("wayback snapshots failed")
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=str(e))

    job.status = JobStatus.DONE
    job.stats = {"snapshots": len(rows)}
    await session.commit()

    return {"url": url, "count": len(rows), "snapshots": rows}


@router.post("/save")
async def save(req: SaveRequest) -> dict:
    try:
        return await wayback.save_now(req.url)
    except Exception as e:
        logger.exception("wayback save failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content", response_class=PlainTextResponse)
async def content(
    url: str = Query(...),
    timestamp: str = Query(...),
) -> PlainTextResponse:
    try:
        body = await wayback.get_snapshot_content(url, timestamp)
        return PlainTextResponse(body)
    except Exception as e:
        logger.exception("wayback content failed")
        raise HTTPException(status_code=500, detail=str(e))
