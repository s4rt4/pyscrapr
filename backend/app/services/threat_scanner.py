"""ThreatScanner orchestrator - coordinates all static analysis modules."""
from __future__ import annotations

import asyncio
import datetime as _dt
import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from app.services import settings_store
from app.services.entropy_analyzer import calculate_entropy, classify_entropy
from app.services.event_bus import event_bus
from app.services.magic_bytes import detect_type
from app.services.yara_engine import get_engine as get_yara

logger = logging.getLogger("pyscrapr.threat")


_ARCHIVE_EXT = {"zip", "7z", "rar"}
_PDF_EXT = {"pdf"}
_OFFICE_EXT = {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "docm", "xlsm", "pptm"}
_PE_EXT = {"exe", "dll", "scr", "sys", "ocx", "cpl", "drv"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verdict(score: int) -> str:
    if score >= 60:
        return "dangerous"
    if score >= 30:
        return "suspicious"
    return "clean"


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


class ThreatScanner:
    async def scan_file(self, path: Path, job_id: str, depth: str = "standard") -> dict[str, Any]:
        started = time.monotonic()
        path = Path(path)
        if not path.exists() or not path.is_file():
            return {
                "error": f"file tidak ditemukan: {path}",
                "job_id": job_id,
                "file_path": str(path),
            }

        max_mb = int(settings_store.get("threat_max_file_size_mb", 100) or 100)
        file_size = path.stat().st_size
        too_big = file_size > max_mb * 1024 * 1024

        findings: list[dict[str, Any]] = []
        score = 0

        await event_bus.publish(job_id, {"type": "progress", "file": str(path), "stage": "start"})

        # Hash early
        sha = _sha256(path) if not too_big else ""

        report: dict[str, Any] = {
            "job_id": job_id,
            "file_path": str(path),
            "file_size": file_size,
            "sha256": sha,
            "detected_type": None,
            "claimed_type": path.suffix.lstrip(".").lower(),
            "type_spoof": False,
            "entropy": 0.0,
            "entropy_class": "plain",
            "findings": findings,
            "risk_score": 0,
            "verdict": "clean",
            "scanned_at": _now_iso(),
            "scan_duration_ms": 0,
            "skipped": False,
            "skip_reason": None,
            "modules": {},
        }

        if too_big:
            report["skipped"] = True
            report["skip_reason"] = f"file > {max_mb} MB, dilewati"
            findings.append({
                "category": "size",
                "severity": "info",
                "title": "File terlalu besar",
                "description": f"Ukuran {file_size / 1_048_576:.1f} MB melebihi batas {max_mb} MB.",
                "score_delta": 0,
            })
            report["scan_duration_ms"] = int((time.monotonic() - started) * 1000)
            await event_bus.publish(job_id, {"type": "progress", "file": str(path), "stage": "skipped"})
            return report

        # 1. Magic bytes
        mb_info = detect_type(path)
        report["modules"]["magic_bytes"] = mb_info
        report["detected_type"] = mb_info.get("mime")
        if mb_info.get("type_mismatch"):
            report["type_spoof"] = True
            sev = mb_info.get("spoof_severity", "medium")
            delta = {"critical": 40, "high": 25, "medium": 15, "low": 5}.get(sev, 10)
            score += delta
            findings.append({
                "category": "magic_bytes",
                "severity": sev,
                "title": "Ekstensi file tidak cocok dengan tipe sebenarnya",
                "description": (
                    f"File claimed .{report['claimed_type']} tapi libmagic mendeteksi "
                    f"{mb_info.get('mime')} ({mb_info.get('description') or '-'})."
                ),
                "score_delta": delta,
            })

        # 2. Read bytes for entropy + YARA (cap 10MB)
        try:
            with path.open("rb") as f:
                raw = f.read(10 * 1024 * 1024)
        except Exception as e:
            raw = b""
            logger.debug("baca bytes gagal: %s", e)

        if raw:
            ent = calculate_entropy(raw)
            report["entropy"] = ent
            report["entropy_class"] = classify_entropy(ent)
            if ent > 7.6:
                score += 20
                findings.append({
                    "category": "entropy",
                    "severity": "medium",
                    "title": "Entropi sangat tinggi",
                    "description": f"Entropi {ent:.2f} - kemungkinan packed / encrypted.",
                    "score_delta": 20,
                })
            elif ent > 7.2:
                score += 10
                findings.append({
                    "category": "entropy",
                    "severity": "low",
                    "title": "Entropi tinggi",
                    "description": f"Entropi {ent:.2f} - konten terkompresi atau acak.",
                    "score_delta": 10,
                })

        # 3. YARA
        yara_engine = get_yara()
        yara_hits = yara_engine.scan_bytes(raw) if raw else []
        report["modules"]["yara"] = yara_hits
        yara_delta_total = 0
        for hit in yara_hits:
            sev = str(hit.get("severity") or hit.get("meta", {}).get("severity") or "medium").lower()
            delta = 30 if sev in ("high", "critical") else 15
            yara_delta_total = min(50, yara_delta_total + delta)
            findings.append({
                "category": "yara",
                "severity": sev,
                "title": f"YARA match: {hit['rule']}",
                "description": (
                    f"Namespace: {hit.get('namespace', '-')}. "
                    f"Meta: {hit.get('meta', {}).get('description', '-')}"
                ),
                "score_delta": delta,
            })
        score += yara_delta_total

        # 4. Dispatch by type
        ext = report["claimed_type"]
        detected_mime = (report["detected_type"] or "").lower()
        is_archive = ext in _ARCHIVE_EXT or "zip" in detected_mime or "7z" in detected_mime or "rar" in detected_mime
        is_pdf = ext in _PDF_EXT or "pdf" in detected_mime
        is_office = ext in _OFFICE_EXT or "officedocument" in detected_mime or detected_mime in (
            "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint"
        )
        is_pe = ext in _PE_EXT or "dosexec" in detected_mime or "msdownload" in detected_mime

        if is_archive:
            from app.services.archive_inspector import inspect_archive
            max_depth = int(settings_store.get("threat_archive_max_depth", 5) or 5)
            max_ratio = int(settings_store.get("threat_archive_max_ratio", 100) or 100)
            arch = await inspect_archive(path, max_depth=max_depth, max_ratio=max_ratio)
            report["modules"]["archive"] = arch
            if arch.get("zip_bomb_flag"):
                score += 60
                findings.append({
                    "category": "archive",
                    "severity": "critical",
                    "title": "Indikasi zip bomb",
                    "description": f"Ratio kompresi {arch.get('ratio')}x - sangat tinggi.",
                    "score_delta": 60,
                })
            dangerous = arch.get("dangerous_files") or []
            if dangerous:
                seen_ext: set[str] = set()
                archive_delta = 0
                for df in dangerous:
                    seen_ext.add(df.get("extension", ""))
                archive_delta = min(30, 15 * len(seen_ext))
                score += archive_delta
                findings.append({
                    "category": "archive",
                    "severity": "high",
                    "title": "Arsip berisi file eksekutabel",
                    "description": f"{len(dangerous)} file dengan ekstensi berbahaya: "
                                   + ", ".join(sorted(seen_ext)),
                    "score_delta": archive_delta,
                })

        if is_pdf:
            from app.services.document_analyzer import analyze_pdf
            pdf = await analyze_pdf(path)
            report["modules"]["pdf"] = pdf
            if pdf.get("has_javascript"):
                score += 20
                findings.append({
                    "category": "pdf", "severity": "medium",
                    "title": "PDF berisi JavaScript",
                    "description": "Keyword /JS atau /JavaScript ditemukan.",
                    "score_delta": 20,
                })
            if pdf.get("has_openaction"):
                score += 15
                findings.append({
                    "category": "pdf", "severity": "medium",
                    "title": "PDF memiliki OpenAction",
                    "description": "Aksi otomatis saat PDF dibuka.",
                    "score_delta": 15,
                })
            if pdf.get("has_launch"):
                score += 20
                findings.append({
                    "category": "pdf", "severity": "high",
                    "title": "PDF memiliki /Launch action",
                    "description": "PDF bisa menjalankan perintah eksternal.",
                    "score_delta": 20,
                })
            if pdf.get("has_embedded_files"):
                score += 15
                findings.append({
                    "category": "pdf", "severity": "medium",
                    "title": "PDF membawa file embedded",
                    "description": "EmbeddedFile ditemukan - bisa jadi payload.",
                    "score_delta": 15,
                })

        if is_office:
            from app.services.document_analyzer import analyze_office
            off = await analyze_office(path)
            report["modules"]["office"] = off
            if off.get("has_vba_macros"):
                score += 15
                findings.append({
                    "category": "office", "severity": "medium",
                    "title": "Dokumen memiliki VBA macros",
                    "description": "Keyword mencurigakan: "
                                   + ", ".join(off.get("macro_suspicious_keywords", [])[:6]),
                    "score_delta": 15,
                })
            if off.get("has_auto_exec"):
                score += 25
                findings.append({
                    "category": "office", "severity": "high",
                    "title": "VBA auto-exec macro terdeteksi",
                    "description": "Macro akan berjalan otomatis saat dokumen dibuka.",
                    "score_delta": 25,
                })

        if is_pe:
            from app.services.pe_analyzer import analyze_pe
            pe = analyze_pe(path)
            report["modules"]["pe"] = pe
            sus_imp = pe.get("suspicious_imports", [])
            if sus_imp:
                delta = min(25, 15 * len(sus_imp))
                score += delta
                findings.append({
                    "category": "pe", "severity": "high",
                    "title": "PE import mencurigakan",
                    "description": "Ditemukan: " + ", ".join(sus_imp[:10]),
                    "score_delta": delta,
                })
            if pe.get("is_packed"):
                score += 15
                findings.append({
                    "category": "pe", "severity": "medium",
                    "title": "PE terlihat packed",
                    "description": "Entropi section tinggi dengan jumlah section sedikit.",
                    "score_delta": 15,
                })
            if pe.get("compile_timestamp_suspicious"):
                score += 5
                findings.append({
                    "category": "pe", "severity": "low",
                    "title": "Timestamp kompilasi tidak wajar",
                    "description": f"Timestamp: {pe.get('timestamp')}",
                    "score_delta": 5,
                })

        # 5. Hash reputation (VT + MB) - concurrent
        if sha and depth != "quick":
            vt_enabled = bool(settings_store.get("threat_virustotal_enabled", True))
            mb_enabled = bool(settings_store.get("threat_malwarebazaar_enabled", True))
            vt_key = settings_store.get("threat_virustotal_api_key", "") or ""

            tasks = []
            from app.services.hash_reputation import virustotal_lookup, malwarebazaar_lookup
            if vt_enabled and vt_key:
                tasks.append(virustotal_lookup(sha, vt_key))
            else:
                async def _skip_vt():
                    return {"found": False, "error": "disabled"}
                tasks.append(_skip_vt())
            if mb_enabled:
                tasks.append(malwarebazaar_lookup(sha))
            else:
                async def _skip_mb():
                    return {"found": False, "error": "disabled"}
                tasks.append(_skip_mb())

            try:
                vt_res, mb_res = await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                logger.debug("reputation gagal: %s", e)
                vt_res, mb_res = {"found": False, "error": str(e)}, {"found": False, "error": str(e)}

            report["modules"]["virustotal"] = vt_res
            report["modules"]["malwarebazaar"] = mb_res

            if vt_res.get("found") and vt_res.get("malicious_count", 0) > 0:
                mc = int(vt_res["malicious_count"])
                if mc > 5:
                    score += 50
                    sev = "critical"
                    delta = 50
                else:
                    score += 25
                    sev = "high"
                    delta = 25
                findings.append({
                    "category": "virustotal", "severity": sev,
                    "title": f"VirusTotal: {mc} engine flagged",
                    "description": "Top threat: " + ", ".join(vt_res.get("threat_names", [])[:3]),
                    "score_delta": delta,
                })

            if mb_res.get("found"):
                score += 40
                findings.append({
                    "category": "malwarebazaar", "severity": "critical",
                    "title": "Hash dikenal di MalwareBazaar",
                    "description": f"Signature: {mb_res.get('signature') or '-'}. "
                                   f"Tags: {', '.join(mb_res.get('tags', [])[:5])}",
                    "score_delta": 40,
                })

        # Finalize
        score = max(0, min(100, score))
        report["risk_score"] = score
        report["verdict"] = _verdict(score)
        report["scan_duration_ms"] = int((time.monotonic() - started) * 1000)

        # AI Threat Explainer (best-effort, never break the scan)
        report["ai_explanation"] = None
        if settings_store.get("ai_explain_enabled", True):
            try:
                from app.services.threat_ai_explainer import get_explainer
                explainer = get_explainer()
                threshold = int(settings_store.get("ai_explain_threshold", 50) or 50)
                ai_result = await explainer.explain(
                    file_hash=report.get("sha256") or "",
                    findings=report,
                    threshold=threshold,
                )
                if ai_result:
                    report["ai_explanation"] = ai_result
            except Exception as e:
                logger.warning("AI explain gagal: %s", e)

        await event_bus.publish(job_id, {
            "type": "progress",
            "file": str(path),
            "stage": "done",
            "verdict": report["verdict"],
            "score": score,
        })
        return report

    async def scan_folder(
        self,
        path: Path,
        job_id: str,
        depth: str = "standard",
        max_files: int = 500,
    ) -> dict[str, Any]:
        path = Path(path)
        if not path.exists() or not path.is_dir():
            return {"error": f"folder tidak ditemukan: {path}", "job_id": job_id}

        files = [p for p in path.rglob("*") if p.is_file()]
        files = files[:max_files]

        await event_bus.publish(job_id, {
            "type": "progress",
            "stage": "enumerated",
            "files_total": len(files),
            "stats": {"files_total": len(files), "files_scanned": 0},
        })

        reports: list[dict[str, Any]] = []
        clean = suspicious = dangerous = 0
        category_counts: dict[str, int] = {}
        total_findings = 0
        total = len(files)
        for idx, f in enumerate(files):
            await event_bus.publish(job_id, {
                "type": "log",
                "message": f"Scanning {f.name} ({idx + 1}/{total})",
            })
            await event_bus.publish(job_id, {
                "type": "progress",
                "stats": {
                    "files_scanned": idx,
                    "files_total": total,
                    "current_file": str(f),
                },
            })
            try:
                rep = await self.scan_file(f, job_id, depth=depth)
            except Exception as e:
                logger.warning("scan gagal %s: %s", f, e)
                continue
            reports.append(rep)
            v = rep.get("verdict")
            if v == "clean":
                clean += 1
            elif v == "suspicious":
                suspicious += 1
            elif v == "dangerous":
                dangerous += 1
            for fi in rep.get("findings", []) or []:
                total_findings += 1
                cat = str(fi.get("category") or "other")
                category_counts[cat] = category_counts.get(cat, 0) + 1
            await event_bus.publish(job_id, {
                "type": "file_done",
                "filename": str(f),
                "verdict": v,
                "score": rep.get("risk_score", 0),
            })
            await event_bus.publish(job_id, {
                "type": "progress",
                "stage": "file_done",
                "index": idx + 1,
                "total": total,
                "file": str(f),
                "verdict": v,
                "stats": {
                    "files_scanned": idx + 1,
                    "files_total": total,
                    "current_file": str(f),
                },
            })

        # Top threats
        top = sorted(reports, key=lambda r: r.get("risk_score", 0), reverse=True)[:5]
        top_summary = [
            {"file_path": r["file_path"], "risk_score": r["risk_score"], "verdict": r["verdict"]}
            for r in top
        ]

        top_categories = sorted(
            [{"category": k, "count": v} for k, v in category_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return {
            "job_id": job_id,
            "folder_path": str(path),
            "files_total": len(files),
            "files_clean": clean,
            "files_suspicious": suspicious,
            "files_dangerous": dangerous,
            "total_findings": total_findings,
            "top_categories": top_categories,
            "category_counts": category_counts,
            "top_threats": top_summary,
            "files": reports,
        }


_scanner: ThreatScanner | None = None


def get_scanner() -> ThreatScanner:
    global _scanner
    if _scanner is None:
        _scanner = ThreatScanner()
    return _scanner
