"""File type detection via libmagic - detects extension spoofing.

Gracefully degrades when python-magic is missing.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("pyscrapr.threat.magic")

_magic_mime = None
_magic_desc = None
_magic_available: bool | None = None


def _init_magic() -> bool:
    global _magic_mime, _magic_desc, _magic_available
    if _magic_available is not None:
        return _magic_available
    try:
        import magic  # type: ignore
        _magic_mime = magic.Magic(mime=True)
        _magic_desc = magic.Magic()
        _magic_available = True
    except Exception as e:
        logger.warning("python-magic tidak tersedia: %s", e)
        _magic_available = False
    return _magic_available


# MIME -> typical extensions (used for spoof detection)
_MIME_TO_EXT: dict[str, set[str]] = {
    "application/x-dosexec": {"exe", "dll", "scr", "sys"},
    "application/x-msdownload": {"exe", "dll"},
    "application/pdf": {"pdf"},
    "image/png": {"png"},
    "image/jpeg": {"jpg", "jpeg"},
    "image/gif": {"gif"},
    "image/webp": {"webp"},
    "image/bmp": {"bmp"},
    "image/x-icon": {"ico"},
    "application/zip": {"zip", "jar", "apk", "docx", "xlsx", "pptx"},
    "application/x-rar": {"rar"},
    "application/x-rar-compressed": {"rar"},
    "application/x-7z-compressed": {"7z"},
    "application/gzip": {"gz", "tgz"},
    "application/x-tar": {"tar"},
    "application/msword": {"doc"},
    "application/vnd.ms-excel": {"xls"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {"docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"xlsx"},
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {"pptx"},
    "text/plain": {"txt", "md", "log", "ini", "cfg"},
    "text/html": {"html", "htm"},
    "text/x-python": {"py"},
    "text/x-shellscript": {"sh"},
    "application/x-bat": {"bat", "cmd"},
    "application/javascript": {"js"},
    "application/json": {"json"},
    "application/xml": {"xml"},
    "video/mp4": {"mp4", "m4v"},
    "video/x-matroska": {"mkv"},
    "audio/mpeg": {"mp3"},
    "audio/ogg": {"ogg"},
    "audio/wav": {"wav"},
}

# Dangerous detected types when extension claims something benign
_DANGEROUS_DETECTED = {
    "application/x-dosexec",
    "application/x-msdownload",
    "application/x-sharedlib",
    "application/x-executable",
    "application/x-mach-binary",
}

_BENIGN_CLAIMED = {"txt", "pdf", "doc", "docx", "jpg", "jpeg", "png", "gif", "md"}


def detect_type(path: Path) -> dict[str, Any]:
    """Return detection report with spoof severity.

    Keys: mime, description, extension_claimed, type_mismatch (bool),
    spoof_severity (critical|high|medium|low|none), available (bool)
    """
    claimed = path.suffix.lstrip(".").lower()
    out: dict[str, Any] = {
        "mime": None,
        "description": None,
        "extension_claimed": claimed,
        "type_mismatch": False,
        "spoof_severity": "none",
        "available": False,
    }
    if not _init_magic():
        return out
    try:
        mime = _magic_mime.from_file(str(path)) if _magic_mime else None
        desc = _magic_desc.from_file(str(path)) if _magic_desc else None
        out["mime"] = mime
        out["description"] = desc
        out["available"] = True

        if not mime:
            return out

        expected_exts = _MIME_TO_EXT.get(mime, set())
        if claimed and expected_exts and claimed not in expected_exts:
            out["type_mismatch"] = True
            # Severity calc
            if mime in _DANGEROUS_DETECTED and claimed in _BENIGN_CLAIMED:
                out["spoof_severity"] = "critical"
            elif mime in _DANGEROUS_DETECTED:
                out["spoof_severity"] = "high"
            elif claimed in {"exe", "dll", "scr", "bat", "cmd", "ps1", "vbs"}:
                out["spoof_severity"] = "high"
            else:
                out["spoof_severity"] = "medium"
    except Exception as e:
        logger.debug("magic detect_type gagal untuk %s: %s", path, e)
    return out
