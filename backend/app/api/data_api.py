"""Local REST API — unified query endpoint for any job's data.

GET /api/data/{job_id}?filter=field:value&sort=field&limit=50&offset=0
Auto-detects job type and returns appropriate data with pagination.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository

router = APIRouter()


@router.get("/{job_id}")
async def query_job_data(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    sort: Optional[str] = Query(default=None, description="Field to sort by"),
    filter: Optional[str] = Query(default=None, description="field:value filter"),
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.type in (JobType.IMAGE_HARVESTER, JobType.SITE_RIPPER, JobType.MEDIA_DOWNLOADER):
        asset_repo = AssetRepository(session)
        assets = await asset_repo.list_for_job(job_id, limit=limit + offset + 1)
        items = [
            {
                "id": a.id,
                "url": a.url,
                "kind": a.kind.value if hasattr(a.kind, "value") else str(a.kind),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "size_bytes": a.size_bytes,
                "content_type": a.content_type,
                "local_path": a.local_path,
                "alt_text": a.alt_text,
                "sha1": a.sha1,
            }
            for a in assets
        ]
    elif job.type == JobType.URL_MAPPER:
        node_repo = CrawlNodeRepository(session)
        nodes = await node_repo.list_for_job(job_id, limit=limit + offset + 1)
        items = [
            {
                "id": n.id,
                "url": n.url,
                "depth": n.depth,
                "status_code": n.status_code,
                "title": n.title,
                "content_type": n.content_type,
                "word_count": n.word_count,
                "response_ms": n.response_ms,
            }
            for n in nodes
        ]
    else:
        raise HTTPException(400, f"Data API not available for {job.type}")

    # Apply filter
    if filter and ":" in filter:
        key, val = filter.split(":", 1)
        items = [i for i in items if str(i.get(key, "")).lower() == val.lower()]

    # Apply sort
    if sort:
        reverse = sort.startswith("-")
        sort_key = sort.lstrip("-")
        items.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

    total = len(items)
    page = items[offset: offset + limit]

    return {
        "job_id": job_id,
        "job_type": job.type.value if hasattr(job.type, "value") else str(job.type),
        "total": total,
        "offset": offset,
        "limit": limit,
        "count": len(page),
        "data": page,
    }
