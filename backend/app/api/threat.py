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
from app.repositories.ai_threat_cache_repository import AIThreatCacheRepository
from app.repositories.hash_reputation_cache_repository import HashRepCacheRepo
from app.services import quarantine as quarantine_svc
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.settings_store import get as get_setting
from app.services.threat_ai_explainer import get_explainer
from app.services.threat_scanner import get_scanner
from app.services.yara_engine import get_engine as get_yara

logger = logging.getLogger("pyscrapr.api.threat")

router = APIRouter()


def _threat_stats_from_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings", []) or []
    cat_counts: dict[str, int] = {}
    for f in findings:
        c = str(f.get("category") or "other")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    return {
        "risk_score": report.get("risk_score"),
        "verdict": report.get("verdict"),
        "findings_count": len(findings),
        "findings_summary": cat_counts,
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
    # overwrite file_path with the original filename, not the temp path
    report["file_path"] = file.filename or "upload"
    job.stats = {**_threat_stats_from_report(report), "report": report}
    await session.commit()
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
                    "total_findings": report.get("total_findings", 0),
                    "category_counts": report.get("category_counts", {}),
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
    total_findings = 0
    category_counts: dict[str, int] = {}

    def _accumulate_categories(src: dict[str, Any]) -> None:
        nonlocal total_findings
        # Folder-scan style
        cc = src.get("category_counts") or {}
        if isinstance(cc, dict):
            for k, v in cc.items():
                try:
                    category_counts[str(k)] = category_counts.get(str(k), 0) + int(v or 0)
                except Exception:
                    continue
        # Single-file style
        fs = src.get("findings_summary") or {}
        if isinstance(fs, dict):
            for k, v in fs.items():
                try:
                    category_counts[str(k)] = category_counts.get(str(k), 0) + int(v or 0)
                except Exception:
                    continue
        if "total_findings" in src:
            try:
                total_findings += int(src.get("total_findings") or 0)
            except Exception:
                pass
        elif "findings_count" in src:
            try:
                total_findings += int(src.get("findings_count") or 0)
            except Exception:
                pass

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
        _accumulate_categories(s)

    top_categories = sorted(
        [{"category": k, "count": v} for k, v in category_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "total_scans": total,
        "clean": clean,
        "suspicious": suspicious,
        "dangerous": dangerous,
        "jobs_recorded": len(jobs),
        "total_findings": total_findings,
        "top_categories": top_categories,
        "verdict_breakdown": {
            "clean": clean,
            "suspicious": suspicious,
            "dangerous": dangerous,
        },
    }


# --- Report export endpoints ---

def _extract_report(job: Job) -> dict[str, Any]:
    s = job.stats or {}
    report = s.get("report") if isinstance(s, dict) else None
    if not report:
        # Synthesize a minimal report from stats
        report = {
            "job_id": job.id,
            "file_path": job.url,
            "stats": s,
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        }
    return report


@router.get("/report/{job_id}.json")
async def report_json(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.THREAT_SCAN:
        raise HTTPException(status_code=400, detail="Job bukan threat_scan")
    report = _extract_report(job)
    body = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    headers = {
        "Content-Disposition": f'attachment; filename="threat_report_{job_id}.json"',
    }
    return StreamingResponse(
        iter([body]),
        media_type="application/json",
        headers=headers,
    )


@router.get("/report/{job_id}.pdf")
async def report_pdf(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.THREAT_SCAN:
        raise HTTPException(status_code=400, detail="Job bukan threat_scan")
    report = _extract_report(job)

    try:
        from io import BytesIO
        from datetime import datetime
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reportlab tidak tersedia: {e}")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * 28.3,
        rightMargin=2 * 28.3,
        topMargin=2 * 28.3,
        bottomMargin=2 * 28.3,
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8, leading=10)

    story: list = []
    story.append(Paragraph("ThreatScanner Report", h1))
    story.append(Spacer(1, 0.2 * cm))
    file_path = report.get("file_path") or report.get("folder_path") or job.url or "-"
    verdict = report.get("verdict") or "-"
    score = report.get("risk_score")
    score_str = str(score) if score is not None else "-"
    story.append(Paragraph(f"<b>Target:</b> {file_path}", body))
    story.append(Paragraph(f"<b>Verdict:</b> {verdict}", body))
    story.append(Paragraph(f"<b>Risk Score:</b> {score_str}", body))
    story.append(Paragraph(f"<b>Job ID:</b> {job_id}", body))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().isoformat()}Z", body))
    story.append(Spacer(1, 0.5 * cm))

    findings = report.get("findings") or []
    if findings:
        story.append(Paragraph(f"Findings ({len(findings)})", h2))
        rows = [["Category", "Severity", "Title", "Score"]]
        for f in findings[:200]:
            rows.append([
                str(f.get("category", "-")),
                str(f.get("severity", "-")),
                str(f.get("title", "-"))[:80],
                str(f.get("score_delta", 0)),
            ])
        t = Table(rows, hAlign="LEFT", colWidths=[3 * cm, 2.2 * cm, 8.5 * cm, 1.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2029")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))
    else:
        # Folder scan summary
        if "files_total" in report:
            story.append(Paragraph("Folder Scan Summary", h2))
            rows = [
                ["Metric", "Value"],
                ["Files total", str(report.get("files_total", 0))],
                ["Clean", str(report.get("files_clean", 0))],
                ["Suspicious", str(report.get("files_suspicious", 0))],
                ["Dangerous", str(report.get("files_dangerous", 0))],
                ["Total findings", str(report.get("total_findings", 0))],
            ]
            t = Table(rows, hAlign="LEFT", colWidths=[6 * cm, 4 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2029")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.5 * cm))
            top_threats = report.get("top_threats") or []
            if top_threats:
                story.append(Paragraph("Top Threats", h2))
                rows = [["File", "Score", "Verdict"]]
                for tt in top_threats[:20]:
                    rows.append([
                        str(tt.get("file_path", "-"))[:80],
                        str(tt.get("risk_score", 0)),
                        str(tt.get("verdict", "-")),
                    ])
                t2 = Table(rows, hAlign="LEFT", colWidths=[10.5 * cm, 2 * cm, 2.5 * cm])
                t2.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2029")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]))
                story.append(t2)
                story.append(Spacer(1, 0.4 * cm))
        else:
            story.append(Paragraph("Tidak ada findings.", body))

    sha = report.get("sha256")
    if sha:
        story.append(Paragraph(f"<b>SHA-256:</b> {sha}", mono))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "PyScrapr ThreatScanner - laporan otomatis (static analysis only).",
        ParagraphStyle("footer", parent=body, fontSize=8, textColor=colors.grey),
    ))

    try:
        doc.build(story)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF build gagal: {e}")
    pdf_bytes = buf.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="threat_report_{job_id}.pdf"',
    }
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)


@router.post("/rules/fetch")
async def rules_fetch(force: bool = False):
    """Trigger YARA rules auto-fetch (YARAForge core)."""
    return await get_yara().ensure_rules_downloaded(force=force)


# ───── AI Threat Explainer ─────


class ExplainRequest(BaseModel):
    job_id: Optional[str] = None
    file_hash: Optional[str] = None
    threshold: Optional[int] = None
    force: bool = False  # if True, ignore the threshold guard


def _extract_report_from_job(job: Job) -> Optional[dict[str, Any]]:
    stats = job.stats or {}
    rep = stats.get("report")
    if isinstance(rep, dict):
        return rep
    # Single-file scan_upload stores the entire report flat in stats? No — stats only has summary.
    # Fallback: treat stats as the report if it has the right shape.
    if "risk_score" in stats and "findings" in stats:
        return stats
    return None


@router.post("/explain")
async def explain_manual(
    req: ExplainRequest,
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger (or refetch) the AI explanation for a prior scan."""
    if not req.job_id and not req.file_hash:
        raise HTTPException(status_code=422, detail="job_id atau file_hash wajib diisi")

    threshold = int(req.threshold if req.threshold is not None else get_setting("ai_explain_threshold", 50) or 50)
    if req.force:
        threshold = 0

    if req.file_hash and not req.job_id:
        # Cache-only path: lookup by hash
        repo = AIThreatCacheRepository(session)
        cached = await repo.get_by_hash(req.file_hash)
        if cached:
            return {
                "analysis": cached.analysis,
                "model_used": cached.model_used,
                "tokens_used": cached.tokens_used,
                "cost_usd": cached.cost_usd,
                "cached": True,
            }
        raise HTTPException(status_code=404, detail="Cache AI tidak ditemukan untuk hash ini")

    repo = JobRepository(session)
    job = await repo.find_by_id(req.job_id or "")
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    if job.type != JobType.THREAT_SCAN:
        raise HTTPException(status_code=400, detail="Job bukan threat_scan")
    report = _extract_report_from_job(job)
    if not report:
        raise HTTPException(status_code=400, detail="Job tidak menyimpan laporan terstruktur")

    file_hash = report.get("sha256") or req.file_hash or ""
    try:
        result = await get_explainer().explain(
            file_hash=file_hash, findings=report, threshold=threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI explain gagal: {e}")
    if not result:
        raise HTTPException(
            status_code=409,
            detail="Tidak dijelaskan: AI dimatikan, di bawah threshold, atau hash kosong.",
        )
    return result


@router.post("/explain/stream")
async def explain_stream(req: ExplainRequest, session: AsyncSession = Depends(get_session)):
    """SSE stream of AI explanation tokens.

    Bypasses cache to give a live typing effect; the resulting analysis is
    NOT persisted to cache (use /explain for the cached, persisted variant).
    """
    if not req.job_id:
        raise HTTPException(status_code=422, detail="job_id wajib diisi")
    repo = JobRepository(session)
    job = await repo.find_by_id(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    report = _extract_report_from_job(job)
    if not report:
        raise HTTPException(status_code=400, detail="Job tidak menyimpan laporan terstruktur")

    explainer = get_explainer()
    messages = [
        {"role": "system", "content": explainer._system_prompt()},
        {"role": "user", "content": explainer._build_prompt(report)},
    ]
    provider = (get_setting("ai_explain_provider", "deepseek") or "deepseek").lower()
    api_key = ""
    model = None
    if provider == "deepseek":
        api_key = get_setting("deepseek_api_key", "") or ""
        model = get_setting("ai_explain_model_deepseek", "deepseek-chat") or "deepseek-chat"
    elif provider == "openai":
        api_key = get_setting("openai_api_key", "") or ""
        model = get_setting("ai_explain_model_openai", "gpt-4o-mini") or "gpt-4o-mini"
    max_tokens = int(get_setting("ai_explain_max_tokens", 300) or 300)

    from app.services import llm_client

    async def gen() -> AsyncGenerator[str, None]:
        try:
            iterator = await llm_client.chat_completion(
                provider=provider,
                messages=messages,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                stream=True,
                timeout=60,
            )
            async for chunk in iterator:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/reputation-cache/stats")
async def reputation_cache_stats():
    """Hash reputation cache (VT + MB) stats."""
    return await HashRepCacheRepo().stats()


@router.delete("/reputation-cache")
async def reputation_cache_clear(confirm: bool = False):
    """Clear all hash reputation cache entries. Pass ?confirm=true to proceed."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Konfirmasi diperlukan: tambahkan ?confirm=true untuk menghapus cache.",
        )
    cleared = await HashRepCacheRepo().clear_all()
    return {"cleared": cleared}


@router.get("/ai-usage")
async def ai_usage(days: int = 30, session: AsyncSession = Depends(get_session)):
    """AI explainer usage statistics for the past N days."""
    repo = AIThreatCacheRepository(session)
    return await repo.usage_stats(days=days)
