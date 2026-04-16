"""Diff / Change detection — compare two runs of the same URL.

GET /api/diff?job_a=<id>&job_b=<id>
Returns: new items (in B but not A), removed items (in A but not B), unchanged count.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.asset_repository import AssetRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository
from app.models.job import JobType

router = APIRouter()


@router.get("")
async def compare_jobs(
    job_a: str,
    job_b: str,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    a = await repo.find_by_id(job_a)
    b = await repo.find_by_id(job_b)
    if not a or not b:
        raise HTTPException(404, "Job not found")

    # Determine comparison strategy by job type
    if a.type in (JobType.IMAGE_HARVESTER, JobType.SITE_RIPPER, JobType.MEDIA_DOWNLOADER):
        return await _diff_assets(session, job_a, job_b)
    elif a.type == JobType.URL_MAPPER:
        return await _diff_crawl_nodes(session, job_a, job_b)
    else:
        raise HTTPException(400, f"Diff not supported for {a.type}")


async def _diff_assets(session: AsyncSession, job_a: str, job_b: str) -> dict:
    repo = AssetRepository(session)
    assets_a = await repo.list_for_job(job_a, limit=50000)
    assets_b = await repo.list_for_job(job_b, limit=50000)

    urls_a = {a.url for a in assets_a}
    urls_b = {a.url for a in assets_b}

    new_urls = urls_b - urls_a
    removed_urls = urls_a - urls_b
    unchanged = urls_a & urls_b

    return {
        "type": "assets",
        "job_a": job_a,
        "job_b": job_b,
        "new": [{"url": u} for u in sorted(new_urls)[:500]],
        "removed": [{"url": u} for u in sorted(removed_urls)[:500]],
        "new_count": len(new_urls),
        "removed_count": len(removed_urls),
        "unchanged_count": len(unchanged),
        "total_a": len(urls_a),
        "total_b": len(urls_b),
    }


async def _diff_crawl_nodes(session: AsyncSession, job_a: str, job_b: str) -> dict:
    repo = CrawlNodeRepository(session)
    nodes_a = await repo.list_for_job(job_a, limit=50000)
    nodes_b = await repo.list_for_job(job_b, limit=50000)

    urls_a = {n.url for n in nodes_a}
    urls_b = {n.url for n in nodes_b}

    # Also detect status changes for pages present in both
    status_a = {n.url: n.status_code for n in nodes_a}
    status_b = {n.url: n.status_code for n in nodes_b}
    changed_status = [
        {"url": u, "was": status_a[u], "now": status_b[u]}
        for u in urls_a & urls_b
        if status_a[u] != status_b[u]
    ]

    new_urls = urls_b - urls_a
    removed_urls = urls_a - urls_b

    return {
        "type": "crawl_nodes",
        "job_a": job_a,
        "job_b": job_b,
        "new": [{"url": u} for u in sorted(new_urls)[:500]],
        "removed": [{"url": u} for u in sorted(removed_urls)[:500]],
        "status_changed": changed_status[:200],
        "new_count": len(new_urls),
        "removed_count": len(removed_urls),
        "status_changed_count": len(changed_status),
        "unchanged_count": len(urls_a & urls_b) - len(changed_status),
        "total_a": len(urls_a),
        "total_b": len(urls_b),
    }
