"""Custom Python pipeline CRUD + run endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository
from app.services.pipeline_executor import (
    delete_pipeline,
    get_pipeline,
    list_pipelines,
    run_pipeline,
    save_pipeline,
)

router = APIRouter()


class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    code: str
    enabled: bool = True
    auto_run_on: list[str] = []


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    code: str | None = None
    enabled: bool | None = None
    auto_run_on: list[str] | None = None


class RunRequest(BaseModel):
    code: str
    job_id: str | None = Field(default=None, description="Optional: run against a completed job's data")
    sample_data: list[dict] | None = None


@router.get("")
async def list_all():
    return list_pipelines()


@router.post("")
async def create_pipeline(req: PipelineCreate):
    pid = str(uuid.uuid4())[:8]
    return save_pipeline(pid, req.name, req.description, req.code, req.enabled, req.auto_run_on)


@router.get("/{pipeline_id}")
async def get_one(pipeline_id: str):
    p = get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(404, "Pipeline not found")
    return p


@router.put("/{pipeline_id}")
async def update(pipeline_id: str, req: PipelineUpdate):
    existing = get_pipeline(pipeline_id)
    if not existing:
        raise HTTPException(404, "Pipeline not found")
    patch = req.model_dump(exclude_unset=True)
    return save_pipeline(
        pipeline_id,
        patch.get("name", existing["name"]),
        patch.get("description", existing["description"]),
        patch.get("code", existing["code"]),
        patch.get("enabled", existing["enabled"]),
        patch.get("auto_run_on", existing.get("auto_run_on", [])),
    )


@router.delete("/{pipeline_id}")
async def delete(pipeline_id: str):
    if not delete_pipeline(pipeline_id):
        raise HTTPException(404, "Pipeline not found")
    return {"ok": True}


@router.post("/run")
async def run(req: RunRequest, session: AsyncSession = Depends(get_session)):
    """Run pipeline code against a job's data OR provided sample_data."""
    data: list[dict] = []
    url = ""

    if req.sample_data is not None:
        data = req.sample_data
    elif req.job_id:
        repo = JobRepository(session)
        job = await repo.find_by_id(req.job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        url = job.url

        if job.type in (JobType.IMAGE_HARVESTER, JobType.SITE_RIPPER, JobType.MEDIA_DOWNLOADER):
            asset_repo = AssetRepository(session)
            assets = await asset_repo.list_for_job(req.job_id, limit=10000)
            data = [
                {
                    "url": a.url,
                    "kind": a.kind.value if hasattr(a.kind, "value") else str(a.kind),
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                    "size_bytes": a.size_bytes,
                    "local_path": a.local_path,
                    "alt_text": a.alt_text,
                }
                for a in assets
            ]
        elif job.type == JobType.URL_MAPPER:
            node_repo = CrawlNodeRepository(session)
            nodes = await node_repo.list_for_job(req.job_id, limit=10000)
            data = [
                {
                    "url": n.url,
                    "depth": n.depth,
                    "status_code": n.status_code,
                    "title": n.title,
                    "word_count": n.word_count,
                }
                for n in nodes
            ]

    return run_pipeline(req.code, data, url=url, job_id=req.job_id or "")
