"""Worker-side endpoints — used when THIS backend instance runs in worker mode.

A master instance POSTs jobs to `/api/worker/submit`; we validate the shared
token (if configured), reconstruct the request schema for the requested job
type, and hand off to the same orchestrator the main API uses.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services import settings_store
from app.services.job_manager import job_manager

logger = logging.getLogger("pyscrapr.worker")

router = APIRouter()


class WorkerSubmitRequest(BaseModel):
    job_type: str = Field(..., description="harvester | mapper | ripper | media")
    payload: dict[str, Any] = Field(default_factory=dict)


def _check_token(x_worker_token: str | None) -> None:
    """Validate the shared secret if one is configured on this worker.

    If `worker_auth_token` setting is empty, requests are accepted without auth
    (local network use only — surface this in UI/docs).
    """
    expected = settings_store.get("worker_auth_token", "") or ""
    if not expected:
        return  # no token required
    if (x_worker_token or "") != expected:
        raise HTTPException(401, "Invalid or missing X-Worker-Token")


@router.get("/health")
async def worker_health():
    """Always-on health probe — used by master for liveness and latency checks."""
    return {
        "status": "ok",
        "mode": settings_store.get("worker_mode", "master"),
        "version": "1.0",
    }


@router.post("/submit")
async def worker_submit(
    req: WorkerSubmitRequest,
    session: AsyncSession = Depends(get_session),
    x_worker_token: str | None = Header(default=None, alias="X-Worker-Token"),
):
    _check_token(x_worker_token)

    job_type = (req.job_type or "").strip().lower()
    payload = req.payload or {}

    # Lazy imports keep the worker endpoint free of unnecessary load at startup
    if job_type == "harvester":
        from app.schemas.job import HarvesterStartRequest
        from app.services.image_harvester import image_harvester_service

        hreq = HarvesterStartRequest.model_validate(payload)
        job_kind = JobType.IMAGE_HARVESTER
        url = str(hreq.url)
        config = hreq.model_dump(mode="json")

        def _launch(job_id: str) -> None:
            job_manager.submit(
                job_id,
                image_harvester_service.run,
                url=str(hreq.url),
                filters=hreq.filters,
                concurrency=hreq.concurrency,
                include_css_bg=hreq.include_background_css,
                deduplicate=hreq.deduplicate,
            )

    elif job_type == "mapper":
        from app.schemas.mapper import MapperStartRequest
        from app.services.url_crawler import url_crawler_service

        mreq = MapperStartRequest.model_validate(payload)
        job_kind = JobType.URL_MAPPER
        url = str(mreq.url)
        config = mreq.model_dump(mode="json")

        def _launch(job_id: str) -> None:
            job_manager.submit(job_id, url_crawler_service.run, req=mreq)

    elif job_type == "ripper":
        from app.schemas.ripper import RipperStartRequest
        from app.services.site_ripper import site_ripper_service

        rreq = RipperStartRequest.model_validate(payload)
        job_kind = JobType.SITE_RIPPER
        url = str(rreq.url)
        config = rreq.model_dump(mode="json")

        def _launch(job_id: str) -> None:
            job_manager.submit(job_id, site_ripper_service.run, req=rreq)

    elif job_type == "media":
        from app.schemas.media import MediaStartRequest
        from app.services.media_downloader import media_downloader_service

        medreq = MediaStartRequest.model_validate(payload)
        job_kind = JobType.MEDIA_DOWNLOADER
        url = str(medreq.url)
        config = medreq.model_dump(mode="json")

        def _launch(job_id: str) -> None:
            job_manager.submit(job_id, media_downloader_service.run, req=medreq)

    else:
        raise HTTPException(400, f"Unknown job_type: {req.job_type!r}")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=job_kind,
        url=url,
        status=JobStatus.PENDING,
        config=config,
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    logger.info("Worker accepted %s job %s (remote dispatch)", job_type, job_id)
    _launch(job_id)

    return {"job_id": job_id, "status": "accepted"}


@router.get("/status/{job_id}")
async def worker_status(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    x_worker_token: str | None = Header(default=None, alias="X-Worker-Token"),
):
    _check_token(x_worker_token)
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.id,
        "type": job.type.value if hasattr(job.type, "value") else str(job.type),
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "url": job.url,
        "stats": job.stats or {},
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if getattr(job, "updated_at", None) else None,
    }
