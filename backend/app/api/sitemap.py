"""Sitemap analyzer endpoints."""
from __future__ import annotations

import csv
import io
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.services import sitemap_analyzer

logger = logging.getLogger("pyscrapr.sitemap")

router = APIRouter()


class SitemapRequest(BaseModel):
    url: str


@router.post("/analyze")
async def analyze_sitemap(
    req: SitemapRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.SITEMAP_ANALYZE,
        url=req.url,
        status=JobStatus.RUNNING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)

    try:
        result = await sitemap_analyzer.analyze(req.url)
    except Exception as e:
        logger.exception("sitemap analyze failed for %s", req.url)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=str(e))

    job.status = JobStatus.DONE
    job.stats = {
        "total_urls": result.get("total_urls", 0),
        "sub_sitemaps": len(result.get("sub_sitemaps", [])),
        "source": result.get("source", "unknown"),
    }
    await session.commit()

    return result


@router.get("/download")
async def download_urls(
    url: str = Query(..., description="Site root or sitemap URL"),
    format: str = Query("csv", pattern="^(csv|json)$"),
) -> Response:
    try:
        urls = await sitemap_analyzer.collect_all_urls(url)
    except Exception as e:
        logger.exception("sitemap download failed")
        raise HTTPException(status_code=500, detail=str(e))

    if format == "json":
        body = json.dumps(urls, ensure_ascii=False, indent=2)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sitemap_urls.json"'},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["loc", "lastmod", "changefreq", "priority"])
    for u in urls:
        writer.writerow([
            u.get("loc", ""),
            u.get("lastmod") or "",
            u.get("changefreq") or "",
            u.get("priority") or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sitemap_urls.csv"'},
    )
