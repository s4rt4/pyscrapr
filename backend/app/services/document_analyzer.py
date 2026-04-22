"""PDF + Office document static analysis."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("pyscrapr.threat.doc")

_PDF_SUSPICIOUS_KEYWORDS = [
    "/JS", "/JavaScript", "/OpenAction", "/AA", "/Launch",
    "/EmbeddedFile", "/EmbeddedFiles", "/RichMedia", "/XFA",
    "/SubmitForm", "/GoToR", "/GoToE", "/ImportData",
]

_URL_RE = re.compile(rb"https?://[^\s\"'<>()]+")

_VBA_SUSPICIOUS_KEYWORDS = [
    "Shell", "WScript.Shell", "CreateObject", "powershell", "cmd.exe",
    "DownloadFile", "DownloadString", "URLDownloadToFile", "Run ",
    "Execute", "ExecuteGlobal", "Environ", "Kill", "Base64",
]

_AUTO_EXEC_TRIGGERS = [
    "AutoOpen", "Auto_Open", "AutoExec", "AutoClose", "Auto_Close",
    "Document_Open", "Workbook_Open", "Document_Close", "Workbook_Activate",
]


async def analyze_pdf(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "has_javascript": False,
        "has_openaction": False,
        "has_launch": False,
        "has_embedded_files": False,
        "urls_found": [],
        "suspicious_keywords": [],
        "page_count": 0,
        "error": None,
        "available": False,
    }

    # Raw byte keyword scan - fast, works without pymupdf
    try:
        raw = path.read_bytes()
    except Exception as e:
        out["error"] = f"read error: {e}"
        return raw_none(out)

    for kw in _PDF_SUSPICIOUS_KEYWORDS:
        if kw.encode() in raw:
            out["suspicious_keywords"].append(kw)

    out["has_javascript"] = ("/JS" in out["suspicious_keywords"]
                             or "/JavaScript" in out["suspicious_keywords"])
    out["has_openaction"] = "/OpenAction" in out["suspicious_keywords"]
    out["has_launch"] = "/Launch" in out["suspicious_keywords"]
    out["has_embedded_files"] = (
        "/EmbeddedFile" in out["suspicious_keywords"]
        or "/EmbeddedFiles" in out["suspicious_keywords"]
    )

    urls = set()
    for m in _URL_RE.finditer(raw[: 5 * 1024 * 1024]):
        try:
            urls.add(m.group(0).decode(errors="ignore"))
        except Exception:
            pass
    out["urls_found"] = sorted(urls)[:50]

    # Try pymupdf for page count + deeper parsing
    try:
        import fitz  # type: ignore
        with fitz.open(str(path)) as doc:
            out["page_count"] = doc.page_count
            out["available"] = True
    except Exception as e:
        logger.debug("pymupdf tidak tersedia atau baca gagal: %s", e)

    return out


def raw_none(d: dict[str, Any]) -> dict[str, Any]:
    return d


async def analyze_office(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "has_vba_macros": False,
        "has_auto_exec": False,
        "macro_suspicious_keywords": [],
        "external_links": [],
        "ole_objects_count": 0,
        "error": None,
        "available": False,
    }

    try:
        from oletools.olevba import VBA_Parser  # type: ignore
    except Exception as e:
        out["error"] = f"oletools tidak tersedia: {e}"
        return out

    try:
        parser = VBA_Parser(str(path))
        out["available"] = True
        if parser.detect_vba_macros():
            out["has_vba_macros"] = True
            seen_kw: set[str] = set()
            auto_exec = False
            try:
                for (_fn, _stream, _vba_fname, vba_code) in parser.extract_macros():
                    if not vba_code:
                        continue
                    code_lower = vba_code.lower() if isinstance(vba_code, str) else ""
                    for kw in _VBA_SUSPICIOUS_KEYWORDS:
                        if kw.lower() in code_lower:
                            seen_kw.add(kw)
                    for t in _AUTO_EXEC_TRIGGERS:
                        if t.lower() in code_lower:
                            auto_exec = True
            except Exception as e:
                logger.debug("extract_macros gagal: %s", e)
            out["macro_suspicious_keywords"] = sorted(seen_kw)
            out["has_auto_exec"] = auto_exec
        try:
            parser.close()
        except Exception:
            pass
    except Exception as e:
        out["error"] = f"olevba error: {e}"

    # External link + OLE scan via raw bytes
    try:
        raw = path.read_bytes()
        urls = set()
        for m in _URL_RE.finditer(raw):
            try:
                urls.add(m.group(0).decode(errors="ignore"))
            except Exception:
                pass
        out["external_links"] = sorted(urls)[:50]
        out["ole_objects_count"] = raw.count(b"\x01Ole")
    except Exception:
        pass

    return out
