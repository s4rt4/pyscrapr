"""Archive inspection: zip / 7z / rar - detect zip bombs and dangerous contents.

Reads metadata without extracting. Graceful on missing backends.
"""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("pyscrapr.threat.archive")

_DANGEROUS_EXT = {
    "exe", "dll", "scr", "sys", "ps1", "vbs", "vbe", "js", "jse", "wsf",
    "wsh", "bat", "cmd", "com", "lnk", "chm", "hta", "msi", "msp", "cpl",
    "jar", "pif", "reg", "ocx",
}

_ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2"}


def _classify_entry(name: str) -> tuple[str, bool, bool]:
    """Return (ext, is_dangerous, is_archive)."""
    if "." not in name:
        return "", False, False
    ext = name.rsplit(".", 1)[-1].lower()
    return ext, ext in _DANGEROUS_EXT, ext in _ARCHIVE_EXT


async def inspect_archive(
    path: Path,
    max_depth: int = 5,
    max_ratio: int = 100,
    _depth: int = 0,
) -> dict[str, Any]:
    """Inspect archive at path. Returns report dict with dangers + nested findings."""
    ext = path.suffix.lstrip(".").lower()

    result: dict[str, Any] = {
        "archive_type": ext,
        "total_entries": 0,
        "compressed_size": 0,
        "uncompressed_size": 0,
        "ratio": 0.0,
        "zip_bomb_flag": False,
        "dangerous_files": [],
        "password_protected": False,
        "recursive_findings": [],
        "error": None,
    }

    try:
        compressed = path.stat().st_size
        result["compressed_size"] = compressed
    except Exception:
        pass

    try:
        if ext == "zip" or zipfile.is_zipfile(path):
            result["archive_type"] = "zip"
            _inspect_zip(path, result)
        elif ext == "7z":
            _inspect_7z(path, result)
        elif ext == "rar":
            _inspect_rar(path, result)
        else:
            result["error"] = f"tipe arsip tidak didukung: {ext}"
            return result
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        return result

    # Compute ratio + zip bomb
    if result["compressed_size"] > 0 and result["uncompressed_size"] > 0:
        ratio = result["uncompressed_size"] / max(1, result["compressed_size"])
        result["ratio"] = round(ratio, 2)
        if ratio > max_ratio:
            result["zip_bomb_flag"] = True

    return result


def _inspect_zip(path: Path, out: dict[str, Any]) -> None:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            infos = zf.infolist()
            out["total_entries"] = len(infos)
            total_unc = 0
            for info in infos:
                total_unc += int(info.file_size)
                if info.flag_bits & 0x1:
                    out["password_protected"] = True
                ext, dangerous, is_arch = _classify_entry(info.filename)
                if dangerous:
                    out["dangerous_files"].append({
                        "name": info.filename,
                        "size": int(info.file_size),
                        "extension": ext,
                    })
            out["uncompressed_size"] = total_unc
    except zipfile.BadZipFile as e:
        out["error"] = f"BadZipFile: {e}"


def _inspect_7z(path: Path, out: dict[str, Any]) -> None:
    try:
        import py7zr  # type: ignore
    except Exception as e:
        out["error"] = f"py7zr tidak terpasang: {e}"
        return
    try:
        with py7zr.SevenZipFile(str(path), mode="r") as sz:
            if sz.password_protected:
                out["password_protected"] = True
            info_list = sz.list()
            out["total_entries"] = len(info_list)
            total_unc = 0
            for entry in info_list:
                size = getattr(entry, "uncompressed", 0) or 0
                total_unc += int(size)
                name = getattr(entry, "filename", "") or ""
                ext, dangerous, _ = _classify_entry(name)
                if dangerous:
                    out["dangerous_files"].append({
                        "name": name,
                        "size": int(size),
                        "extension": ext,
                    })
            out["uncompressed_size"] = total_unc
    except Exception as e:
        out["error"] = f"7z error: {e}"


def _inspect_rar(path: Path, out: dict[str, Any]) -> None:
    try:
        import rarfile  # type: ignore
    except Exception as e:
        out["error"] = f"rarfile tidak terpasang: {e}"
        return
    try:
        with rarfile.RarFile(str(path)) as rf:
            if rf.needs_password():
                out["password_protected"] = True
            infos = rf.infolist()
            out["total_entries"] = len(infos)
            total_unc = 0
            for info in infos:
                total_unc += int(getattr(info, "file_size", 0) or 0)
                name = getattr(info, "filename", "") or ""
                ext, dangerous, _ = _classify_entry(name)
                if dangerous:
                    out["dangerous_files"].append({
                        "name": name,
                        "size": int(getattr(info, "file_size", 0) or 0),
                        "extension": ext,
                    })
            out["uncompressed_size"] = total_unc
    except Exception as e:
        out["error"] = f"rar error: {e}"
