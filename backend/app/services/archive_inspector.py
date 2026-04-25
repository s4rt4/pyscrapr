"""Archive inspection: zip / 7z / rar - detect zip bombs and dangerous contents.

Reads metadata without extracting. Graceful on missing backends.
"""
from __future__ import annotations

import logging
import tempfile
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

    result["recursion_depth"] = _depth
    if _depth >= max_depth:
        result["recursion_capped"] = True
        result["nested_archives"] = []
        return result

    # Recurse into nested archives (only inside zip we have direct extract API).
    nested: list[dict[str, Any]] = []
    try:
        if result["archive_type"] == "zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        name = info.filename or ""
                        if name.endswith("/"):
                            continue
                        ext_inner = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                        if ext_inner not in _ARCHIVE_EXT:
                            continue
                        # Skip if password protected (cannot read)
                        if info.flag_bits & 0x1:
                            nested.append({
                                "path": name,
                                "skipped": True,
                                "reason": "password_protected",
                            })
                            continue
                        # Cap inner size at 200MB to avoid bombs during recursion
                        if info.file_size > 200 * 1024 * 1024:
                            nested.append({
                                "path": name,
                                "skipped": True,
                                "reason": "too_large",
                            })
                            continue
                        tmp_path: Path | None = None
                        try:
                            data = zf.read(name)
                            fd, tmp_str = tempfile.mkstemp(suffix="." + ext_inner)
                            tmp_path = Path(tmp_str)
                            try:
                                import os as _os
                                _os.close(fd)
                            except Exception:
                                pass
                            tmp_path.write_bytes(data)
                            inner = await inspect_archive(
                                tmp_path,
                                max_depth=max_depth,
                                max_ratio=max_ratio,
                                _depth=_depth + 1,
                            )
                            nested.append({"path": name, "report": inner})
                            # Aggregate dangerous escalation
                            if inner.get("dangerous_files"):
                                for df in inner["dangerous_files"]:
                                    cloned = dict(df)
                                    cloned["nested_in"] = name
                                    result["dangerous_files"].append(cloned)
                            if inner.get("zip_bomb_flag"):
                                result["zip_bomb_flag"] = True
                        except Exception as e:
                            logger.debug("recurse %s gagal: %s", name, e)
                            nested.append({
                                "path": name,
                                "skipped": True,
                                "reason": f"{type(e).__name__}: {e}",
                            })
                        finally:
                            if tmp_path is not None:
                                try:
                                    tmp_path.unlink(missing_ok=True)
                                except Exception:
                                    pass
            except Exception as e:
                logger.debug("recurse zip gagal: %s", e)
    except Exception as e:
        logger.debug("recurse umum gagal: %s", e)

    result["nested_archives"] = nested
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
