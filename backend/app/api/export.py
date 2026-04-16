"""Unified data export — any job type → CSV / JSON / Excel."""
import csv
import io
import json
from typing import Literal

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.crawl_node_repository import CrawlNodeRepository
from app.repositories.job_repository import JobRepository

router = APIRouter()

Format = Literal["csv", "json", "xlsx"]


async def _get_rows(job_id: str, session: AsyncSession) -> tuple[list[str], list[list]]:
    """Return (headers, rows) for any job type."""
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.type in (JobType.IMAGE_HARVESTER, JobType.SITE_RIPPER, JobType.MEDIA_DOWNLOADER):
        asset_repo = AssetRepository(session)
        assets = await asset_repo.list_for_job(job_id, limit=50000)
        headers = ["url", "kind", "status", "size_bytes", "content_type", "local_path", "alt_text"]
        rows = [
            [a.url, a.kind.value if hasattr(a.kind, "value") else str(a.kind),
             a.status.value if hasattr(a.status, "value") else str(a.status),
             a.size_bytes or 0, a.content_type or "", a.local_path or "", a.alt_text or ""]
            for a in assets
        ]
        return headers, rows

    elif job.type == JobType.URL_MAPPER:
        node_repo = CrawlNodeRepository(session)
        nodes = await node_repo.list_for_job(job_id, limit=50000)
        headers = ["url", "depth", "status_code", "title", "content_type", "word_count", "response_ms", "error"]
        rows = [
            [n.url, n.depth, n.status_code or "", n.title or "", n.content_type or "",
             n.word_count or "", n.response_ms or "", n.error or ""]
            for n in nodes
        ]
        return headers, rows

    elif job.type == JobType.AI_TAGGING:
        # Read from JSON results file
        if not job.output_dir:
            raise HTTPException(404, "No results yet")
        from pathlib import Path
        p = Path(job.output_dir)
        if not p.exists():
            raise HTTPException(404, "Results file missing")
        data = json.loads(p.read_text())
        labels = data.get("labels", [])
        headers = ["filename", "top_tag", "top_score"] + labels
        rows = []
        for r in data.get("results", []):
            row = [r["filename"], r.get("top_tag", ""), r.get("top_score", 0)]
            scores = r.get("scores", {})
            row += [scores.get(l, 0) for l in labels]
            rows.append(row)
        return headers, rows

    raise HTTPException(400, f"Export not supported for {job.type}")


@router.get("/{job_id}")
async def export_job(
    job_id: str,
    format: Format = Query(default="csv"),
    session: AsyncSession = Depends(get_session),
):
    headers, rows = await _get_rows(job_id, session)
    short_id = job_id[:8]

    if format == "json":
        payload = [dict(zip(headers, row)) for row in rows]
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="export-{short_id}.json"'},
        )

    elif format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="export-{short_id}.csv"'},
        )

    elif format == "xlsx":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Export"
        ws.append(headers)
        for row in rows:
            ws.append(row)
        # Auto-width columns
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="export-{short_id}.xlsx"'},
        )
