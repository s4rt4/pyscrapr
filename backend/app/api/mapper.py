"""URL Mapper endpoints (Phase 2)."""
import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import AsyncGenerator
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreatedResponse, JobDTO
from app.schemas.mapper import (
    CrawlNodeDTO,
    MapperStartRequest,
    SitemapGraphEdge,
    SitemapGraphNode,
    SitemapGraphResponse,
    SitemapTreeNode,
)
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.url_crawler import url_crawler_service

router = APIRouter()


@router.post("/start", response_model=JobCreatedResponse)
async def start_mapper(
    req: MapperStartRequest,
    session: AsyncSession = Depends(get_session),
):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.URL_MAPPER,
        url=str(req.url),
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    job_manager.submit(job_id, url_crawler_service.run, req=req)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/resume/{job_id}", response_model=JobCreatedResponse)
async def resume_mapper(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.type != JobType.URL_MAPPER:
        raise HTTPException(400, "Not a URL Mapper job")
    if job_manager.is_running(job_id):
        raise HTTPException(409, "Job already running")

    # Rebuild request from stored config
    req = MapperStartRequest.model_validate(job.config)
    job_manager.submit(job_id, url_crawler_service.run, req=req)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.RUNNING)


@router.post("/stop/{job_id}")
async def stop_mapper(job_id: str):
    if not job_manager.stop(job_id):
        raise HTTPException(404, "Job not running")
    return {"ok": True}


@router.get("/jobs/{job_id}", response_model=JobDTO)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDTO.model_validate(job)


@router.get("/jobs/{job_id}/nodes", response_model=list[CrawlNodeDTO])
async def list_nodes(
    job_id: str,
    limit: int = 5000,
    session: AsyncSession = Depends(get_session),
):
    repo = CrawlNodeRepository(session)
    nodes = await repo.list_for_job(job_id, limit=limit)
    return [CrawlNodeDTO.model_validate(n) for n in nodes]


@router.get("/jobs/{job_id}/tree", response_model=list[SitemapTreeNode])
async def get_tree(job_id: str, session: AsyncSession = Depends(get_session)):
    """Return nested tree structure for Mantine Tree view."""
    repo = CrawlNodeRepository(session)
    nodes = await repo.list_for_job(job_id, limit=20000)
    if not nodes:
        return []

    children_map: dict[int | None, list] = defaultdict(list)
    id_map: dict[int, SitemapTreeNode] = {}
    for n in nodes:
        id_map[n.id] = SitemapTreeNode(
            id=n.id,
            url=n.url,
            depth=n.depth,
            status_code=n.status_code,
            title=n.title,
            children=[],
        )
    for n in nodes:
        children_map[n.parent_id].append(id_map[n.id])

    # Attach children
    for node_id, node_dto in id_map.items():
        node_dto.children = children_map.get(node_id, [])

    roots = children_map.get(None, [])
    return roots


@router.get("/jobs/{job_id}/graph", response_model=SitemapGraphResponse)
async def get_graph(job_id: str, session: AsyncSession = Depends(get_session)):
    """Return flat nodes + edges for Cytoscape graph view."""
    repo = CrawlNodeRepository(session)
    nodes = await repo.list_for_job(job_id, limit=20000)

    node_dtos = [
        SitemapGraphNode(
            id=n.id,
            url=n.url,
            depth=n.depth,
            status_code=n.status_code,
            title=n.title,
        )
        for n in nodes
    ]
    edges = [
        SitemapGraphEdge(source=n.parent_id, target=n.id)
        for n in nodes
        if n.parent_id is not None
    ]
    return SitemapGraphResponse(nodes=node_dtos, edges=edges)


@router.get("/jobs/{job_id}/export/json")
async def export_json(job_id: str, session: AsyncSession = Depends(get_session)):
    """Download all nodes for a job as a JSON file."""
    repo = CrawlNodeRepository(session)
    nodes = await repo.list_for_job(job_id, limit=20000)
    payload = {
        "job_id": job_id,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "count": len(nodes),
        "nodes": [
            {
                "id": n.id,
                "url": n.url,
                "parent_id": n.parent_id,
                "depth": n.depth,
                "status_code": n.status_code,
                "title": n.title,
                "content_type": n.content_type,
                "word_count": n.word_count,
                "response_ms": n.response_ms,
                "error": n.error,
            }
            for n in nodes
        ],
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="sitemap-{job_id[:8]}.json"'},
    )


@router.get("/jobs/{job_id}/export/xml")
async def export_sitemap_xml(job_id: str, session: AsyncSession = Depends(get_session)):
    """Download as standard sitemap.xml (Google/SEO compatible)."""
    repo = CrawlNodeRepository(session)
    nodes = await repo.list_for_job(job_id, limit=50000)

    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for n in nodes:
        if n.status_code and 200 <= n.status_code < 300:
            url_el = ET.SubElement(urlset, "url")
            ET.SubElement(url_el, "loc").text = n.url
            if n.created_at:
                ET.SubElement(url_el, "lastmod").text = n.created_at.strftime("%Y-%m-%d")
    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="utf-8")

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="sitemap-{job_id[:8]}.xml"'},
    )


@router.get("/jobs/{job_id}/events")
async def stream_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
