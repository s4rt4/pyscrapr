"""ThreatScanner endpoints."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.job_repository import JobRepository
from app.schemas.threat import (
    FolderScanResponse,
    QuarantineEntry,
    QuarantineRequest,
    ThreatScanRequest,
    ThreatScanResponse,
    YaraRuleInfo,
)
from app.services import quarantine as quarantine_svc
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.threat_scanner import get_scanner
from app.services.yara_engine import get_engine as get_yara

logger = logging.getLogger("pyscrapr.api.threat")

router = APIRouter()


def _threat_stats_from_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_score": report.get("risk_score"),
        "verdict": report.get("verdict"),
        "findings_count": len(report.get("findings", [])),
    }


@router.post("/scan/upload")
async def scan_upload(
    file: UploadFile = File(...),
    depth: str = "standard",
    session: AsyncSession = Depends(get_session),
):
    """Upload a file, scan it, delete temp, return report."""
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.THREAT_SCAN,
        url=file.filename or "upload",
        status=JobStatus.RUNNING,
        config={"source": "upload", "filename": file.filename, "depth": depth},
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    tmp_dir = Path(tempfile.gettempdir()) / "pyscrapr_threat"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{job_id}_{os.path.basename(file.filename or 'upload')}"
    tmp_path = tmp_dir / safe_name
    try:
        data = await file.read()
        tmp_path.write_bytes(data)
        report = await get_scanner().scan_file(tmp_path, job_id, depth=depth)
    except Exception as e:
        logger.exception("scan upload gagal: %s", e)
        job.status = JobStatus.ERROR
        job.error_message = str(e)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Scan gagal: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    job.status = JobStatus.DONE
    job.stats = _threat_stats_from_report(report)
    await session.commit()
    # overwrite file_path with the original filename, not the temp path
    report["file_path"] = file.filename or "upload"
    return report


@router.post("/scan/path")
async def scan_path(
    req: ThreatScanRequest,
    session: AsyncSession = Depends(get_session),
):
    """Scan a local file or folder path."""
    if not req.path:
        raise HTTPException(status_code=422, detail="path wajib diisi")
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path tidak ditemukan: {req.path}")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.THREAT_SCAN,
        url=req.path,
        status=JobStatus.PENDING,
        config={"source": "path", "path": req.path, "depth": req.depth},
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    scanner = get_scanner()

    async def _run(jid, _stop_evt):
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as s2:
            r2 = JobRepository(s2)
            j2 = await r2.find_by_id(jid)
            if j2:
                j2.status = JobStatus.RUNNING
                await s2.commit()
        try:
            if p.is_file():
                report = await scanner.scan_file(p, jid, depth=req.depth)
                stats = _threat_stats_from_report(report)
            else:
                report = await scanner.scan_folder(p, jid, depth=req.depth)
                stats = {
                    "files_total": report.get("files_total", 0),
                    "files_clean": report.get("files_clean", 0),
                    "files_suspicious": report.get("files_suspicious", 0),
                    "files_dangerous": report.get("files_dangerous", 0),
                }
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(jid)
                if j2:
                    j2.status = JobStatus.DONE
                    j2.output_dir = str(p.parent if p.is_file() else p)
                    j2.stats = {**stats, "report": report}
                    await s2.commit()
            await event_bus.publish(jid, {"type": "done", "stats": stats})
        except Exception as e:
            logger.exception("scan_path gagal: %s", e)
            async with AsyncSessionLocal() as s2:
                r2 = JobRepository(s2)
                j2 = await r2.find_by_id(jid)
                if j2:
                    j2.status = JobStatus.ERROR
                    j2.error_message = str(e)
                    await s2.commit()
            await event_bus.publish(jid, {"type": "error", "message": str(e)})

    job_manager.submit(job_id, _run)
    return {"job_id": job_id, "status": JobStatus.PENDING.value}


@router.get("/scan/events/{job_id}")
async def scan_events(job_id: str):
    """SSE stream of scan progress."""
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/scan/{job_id}")
async def get_scan_report(job_id: str, session: AsyncSession = Depends(get_session)):
    """Retrieve the persisted scan report for a job."""
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.THREAT_SCAN:
        raise HTTPException(status_code=400, detail="Job bukan threat_scan")
    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "config": job.config,
        "stats": job.stats,
        "error_message": job.error_message,
    }


@router.post("/quarantine")
async def quarantine_endpoint(req: QuarantineRequest):
    try:
        return quarantine_svc.quarantine_file(Path(req.file_path), req.reason)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quarantine gagal: {e}")


@router.get("/quarantine", response_model=list[QuarantineEntry])
async def list_quarantine_endpoint():
    return quarantine_svc.list_quarantine()


@router.post("/quarantine/restore/{quarantine_id}")
async def restore_quarantine(quarantine_id: str):
    try:
        return quarantine_svc.restore_file(quarantine_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore gagal: {e}")


@router.get("/rules", response_model=list[YaraRuleInfo])
async def list_rules():
    return get_yara().list_rules()


@router.post("/rules/reload")
async def reload_rules():
    count = get_yara().reload()
    return {"reloaded": True, "rule_files": count}


@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)):
    """Aggregate threat-scan stats from persisted jobs."""
    stmt = select(Job).where(Job.type == JobType.THREAT_SCAN).order_by(desc(Job.created_at)).limit(1000)
    result = await session.execute(stmt)
    jobs = list(result.scalars().all())

    total = 0
    clean = suspicious = dangerous = 0
    for j in jobs:
        s = j.stats or {}
        # Folder scans carry aggregate counters
        if "files_total" in s:
            total += int(s.get("files_total", 0) or 0)
            clean += int(s.get("files_clean", 0) or 0)
            suspicious += int(s.get("files_suspicious", 0) or 0)
            dangerous += int(s.get("files_dangerous", 0) or 0)
        else:
            total += 1
            v = s.get("verdict")
            if v == "clean":
                clean += 1
            elif v == "suspicious":
                suspicious += 1
            elif v == "dangerous":
                dangerous += 1
    return {
        "total_scans": total,
        "clean": clean,
        "suspicious": suspicious,
        "dangerous": dangerous,
        "jobs_recorded": len(jobs),
    }
