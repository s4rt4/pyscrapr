"""MetadataExtractor — extract EXIF/PDF/Office/media metadata from local files.

Defensive by design: every branch isolates its own exceptions and returns None
on failure so a single broken parser never breaks the rest of the extraction.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger("pyscrapr.services.metadata_extractor")

_MAX_VAL_LEN = 200
_XMP_TRUNC = 500

_OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}
_OFFICE_LEGACY = {".doc", ".xls", ".ppt"}
_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    ".heic", ".heif",
}
_PDF_EXTS = {".pdf"}
_MEDIA_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v",
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus",
}


def _truncate(value: Any, limit: int = _MAX_VAL_LEN) -> Any:
    try:
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:
                value = repr(value)
        if isinstance(value, str) and len(value) > limit:
            return value[:limit] + "..."
        return value
    except Exception:
        return None


def _safe_iso(ts: float | None) -> str | None:
    try:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _detect_mime(path: Path) -> str:
    """Best-effort MIME detection. Lazy-imports python-magic and falls back to
    mimetypes / extension."""
    # 1. python-magic (libmagic) — most accurate
    try:
        import magic  # type: ignore
        try:
            return magic.from_file(str(path), mime=True) or ""
        except Exception:
            pass
    except Exception:
        pass
    # 2. stdlib mimetypes
    try:
        import mimetypes
        guess, _ = mimetypes.guess_type(str(path))
        if guess:
            return guess
    except Exception:
        pass
    # 3. fallback to extension
    return path.suffix.lower().lstrip(".") or "application/octet-stream"


# ───────── Image / EXIF ─────────

def _rational_to_float(v: Any) -> float | None:
    try:
        if hasattr(v, "numerator") and hasattr(v, "denominator"):
            d = float(v.denominator)
            return float(v.numerator) / d if d else None
        if isinstance(v, tuple) and len(v) == 2:
            return float(v[0]) / float(v[1]) if v[1] else None
        return float(v)
    except Exception:
        return None


def _gps_to_decimal(coord: Any, ref: str | None) -> float | None:
    try:
        if not coord or len(coord) < 3:
            return None
        d = _rational_to_float(coord[0]) or 0.0
        m = _rational_to_float(coord[1]) or 0.0
        s = _rational_to_float(coord[2]) or 0.0
        val = d + (m / 60.0) + (s / 3600.0)
        if ref and ref.upper() in ("S", "W"):
            val = -val
        return round(val, 7)
    except Exception:
        return None


def _extract_image(path: Path) -> dict[str, Any] | None:
    try:
        from PIL import Image, ExifTags  # type: ignore
    except Exception:
        return None
    try:
        with Image.open(path) as img:
            out: dict[str, Any] = {
                "Format": img.format,
                "Mode": img.mode,
                "ImageWidth": img.width,
                "ImageHeight": img.height,
            }
            try:
                exif = img.getexif()
            except Exception:
                exif = None
            if not exif:
                return out

            tag_map = {v: k for k, v in ExifTags.TAGS.items()}  # name -> id
            id_to_name = ExifTags.TAGS

            wanted = [
                "Make", "Model", "Software", "DateTimeOriginal", "Artist",
                "Copyright", "Orientation", "ExposureTime", "FNumber",
                "ISO", "ISOSpeedRatings", "FocalLength", "LensModel",
            ]
            for name in wanted:
                tid = tag_map.get(name)
                if tid is None:
                    continue
                try:
                    raw = exif.get(tid)
                except Exception:
                    raw = None
                if raw is None:
                    continue
                if name in ("ExposureTime", "FNumber", "FocalLength"):
                    f = _rational_to_float(raw)
                    if f is not None:
                        out[name] = round(f, 6)
                        continue
                out[name] = _truncate(raw)

            # GPS — nested IFD
            try:
                gps_ifd_id = tag_map.get("GPSInfo")
                gps_data = exif.get(gps_ifd_id) if gps_ifd_id else None
                # Pillow >= 6 uses get_ifd
                if not gps_data:
                    try:
                        gps_data = exif.get_ifd(0x8825)
                    except Exception:
                        gps_data = None
                if gps_data:
                    GPSTAGS = ExifTags.GPSTAGS
                    g: dict[str, Any] = {}
                    for k, v in gps_data.items():
                        name = GPSTAGS.get(k, str(k))
                        g[name] = v
                    lat = _gps_to_decimal(g.get("GPSLatitude"), g.get("GPSLatitudeRef"))
                    lon = _gps_to_decimal(g.get("GPSLongitude"), g.get("GPSLongitudeRef"))
                    alt = _rational_to_float(g.get("GPSAltitude"))
                    if lat is not None:
                        out["GPSLatitude"] = lat
                    if lon is not None:
                        out["GPSLongitude"] = lon
                    if alt is not None:
                        out["GPSAltitude"] = round(alt, 3)
            except Exception:
                pass

            return out
    except Exception as e:
        logger.debug("image extract gagal %s: %s", path, e)
        return None


# ───────── PDF ─────────

def _extract_pdf(path: Path) -> dict[str, Any] | None:
    try:
        import fitz  # type: ignore
    except Exception:
        return None
    try:
        doc = fitz.open(path)
        try:
            meta = dict(doc.metadata or {})
            out: dict[str, Any] = {
                "title": _truncate(meta.get("title")),
                "author": _truncate(meta.get("author")),
                "subject": _truncate(meta.get("subject")),
                "keywords": _truncate(meta.get("keywords")),
                "creator": _truncate(meta.get("creator")),
                "producer": _truncate(meta.get("producer")),
                "creation_date": _truncate(meta.get("creationDate")),
                "mod_date": _truncate(meta.get("modDate")),
                "encryption": _truncate(meta.get("encryption")),
                "trapped": _truncate(meta.get("trapped")),
                "page_count": doc.page_count,
            }
            try:
                xmp = doc.xref_xml_metadata() if hasattr(doc, "xref_xml_metadata") else None
            except Exception:
                xmp = None
            if not xmp:
                try:
                    xmp = doc.metadata_xml() if hasattr(doc, "metadata_xml") else None
                except Exception:
                    xmp = None
            if xmp:
                out["xmp_metadata"] = _truncate(xmp, _XMP_TRUNC)
            return {k: v for k, v in out.items() if v is not None}
        finally:
            try:
                doc.close()
            except Exception:
                pass
    except Exception as e:
        logger.debug("pdf extract gagal %s: %s", path, e)
        return None


# ───────── Office ─────────

_DC_NS = "{http://purl.org/dc/elements/1.1/}"
_CP_NS = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
_DCT_NS = "{http://purl.org/dc/terms/}"
_APP_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"


def _extract_office_modern(path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            out: dict[str, Any] = {}
            if "docProps/core.xml" in names:
                try:
                    with zf.open("docProps/core.xml") as f:
                        root = ET.parse(f).getroot()
                    mapping = {
                        "title": f"{_DC_NS}title",
                        "creator": f"{_DC_NS}creator",
                        "subject": f"{_DC_NS}subject",
                        "description": f"{_DC_NS}description",
                        "keywords": f"{_CP_NS}keywords",
                        "last_modified_by": f"{_CP_NS}lastModifiedBy",
                        "revision": f"{_CP_NS}revision",
                        "category": f"{_CP_NS}category",
                        "created": f"{_DCT_NS}created",
                        "modified": f"{_DCT_NS}modified",
                    }
                    for key, tag in mapping.items():
                        el = root.find(tag)
                        if el is not None and el.text:
                            out[key] = _truncate(el.text)
                except Exception:
                    pass
            if "docProps/app.xml" in names:
                try:
                    with zf.open("docProps/app.xml") as f:
                        root = ET.parse(f).getroot()
                    mapping = {
                        "application": f"{_APP_NS}Application",
                        "app_version": f"{_APP_NS}AppVersion",
                        "company": f"{_APP_NS}Company",
                        "manager": f"{_APP_NS}Manager",
                        "doc_security": f"{_APP_NS}DocSecurity",
                        "total_time": f"{_APP_NS}TotalTime",
                        "pages": f"{_APP_NS}Pages",
                        "words": f"{_APP_NS}Words",
                        "characters": f"{_APP_NS}Characters",
                    }
                    for key, tag in mapping.items():
                        el = root.find(tag)
                        if el is not None and el.text:
                            out[key] = _truncate(el.text)
                except Exception:
                    pass
            return out or None
    except Exception as e:
        logger.debug("office modern extract gagal %s: %s", path, e)
        return None


def _extract_office_legacy(path: Path) -> dict[str, Any] | None:
    try:
        import olefile  # type: ignore
    except Exception:
        return None
    try:
        if not olefile.isOleFile(str(path)):
            return None
        ole = olefile.OleFileIO(str(path))
        try:
            meta = ole.get_metadata()
        finally:
            try:
                ole.close()
            except Exception:
                pass
        out: dict[str, Any] = {}
        for attr in (
            "title", "subject", "author", "keywords", "comments",
            "last_saved_by", "revision_number", "create_time", "last_saved_time",
            "company", "manager", "num_pages", "num_words", "num_chars",
        ):
            try:
                val = getattr(meta, attr, None)
                if val is not None:
                    out[attr] = _truncate(val)
            except Exception:
                continue
        return out or None
    except Exception as e:
        logger.debug("office legacy extract gagal %s: %s", path, e)
        return None


def _extract_office(path: Path) -> dict[str, Any] | None:
    ext = path.suffix.lower()
    if ext in _OFFICE_EXTS:
        return _extract_office_modern(path)
    if ext in _OFFICE_LEGACY:
        return _extract_office_legacy(path)
    return None


# ───────── Media (ffprobe) ─────────

def _resolve_ffprobe() -> str | None:
    try:
        import imageio_ffmpeg  # type: ignore
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if not ffmpeg:
            return None
        p = Path(ffmpeg)
        # Replace 'ffmpeg' -> 'ffprobe' in basename, preserve extension
        name = p.name
        new_name = name.replace("ffmpeg", "ffprobe", 1)
        candidate = p.with_name(new_name)
        if candidate.exists():
            return str(candidate)
        # Some packages bundle only ffmpeg; try PATH ffprobe as fallback
        import shutil
        which = shutil.which("ffprobe")
        return which
    except Exception:
        return None


async def _extract_media(path: Path) -> dict[str, Any] | None:
    ffprobe = _resolve_ffprobe()
    if not ffprobe:
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return None
        if proc.returncode != 0 or not stdout:
            return None
        data = json.loads(stdout.decode("utf-8", errors="replace"))
        fmt = data.get("format") or {}
        streams = data.get("streams") or []
        out: dict[str, Any] = {
            "format_name": _truncate(fmt.get("format_name")),
            "format_long_name": _truncate(fmt.get("format_long_name")),
            "duration": _truncate(fmt.get("duration")),
            "size": _truncate(fmt.get("size")),
            "bit_rate": _truncate(fmt.get("bit_rate")),
            "nb_streams": fmt.get("nb_streams"),
        }
        tags = fmt.get("tags") or {}
        if isinstance(tags, dict):
            for k in ("title", "artist", "album", "date", "genre", "comment"):
                # ffprobe tag keys can vary in case
                v = tags.get(k) or tags.get(k.upper()) or tags.get(k.capitalize())
                if v:
                    out[k] = _truncate(v)
        stream_list = []
        for s in streams:
            entry = {
                "index": s.get("index"),
                "codec_type": s.get("codec_type"),
                "codec_name": s.get("codec_name"),
                "codec_long_name": _truncate(s.get("codec_long_name")),
            }
            if s.get("codec_type") == "video":
                entry["width"] = s.get("width")
                entry["height"] = s.get("height")
                entry["pix_fmt"] = s.get("pix_fmt")
                entry["r_frame_rate"] = s.get("r_frame_rate")
            elif s.get("codec_type") == "audio":
                entry["sample_rate"] = s.get("sample_rate")
                entry["channels"] = s.get("channels")
                entry["channel_layout"] = s.get("channel_layout")
            stream_list.append(entry)
        out["streams"] = stream_list
        return out
    except Exception as e:
        logger.debug("media extract gagal %s: %s", path, e)
        return None


# ───────── Public API ─────────

class MetadataExtractor:
    async def extract(self, file_path: Path) -> dict[str, Any]:
        path = Path(file_path)
        try:
            stat = path.stat()
            size_bytes = stat.st_size
            modified_at = _safe_iso(stat.st_mtime)
        except Exception:
            size_bytes = 0
            modified_at = None

        mime = _detect_mime(path)
        ext = path.suffix.lower()

        generic: dict[str, Any] = {
            "path": str(path),
            "basename": path.name,
            "ext": ext,
            "size_bytes": size_bytes,
            "modified_at": modified_at,
            "magic_mime": mime,
        }

        categories: dict[str, Any] = {
            "exif": None,
            "pdf": None,
            "office": None,
            "media": None,
            "generic": generic,
        }

        # Image / EXIF
        if ext in _IMAGE_EXTS or (mime and mime.startswith("image/")):
            try:
                categories["exif"] = _extract_image(path)
            except Exception as e:
                logger.debug("exif branch gagal: %s", e)

        # PDF
        if ext in _PDF_EXTS or mime == "application/pdf":
            try:
                categories["pdf"] = _extract_pdf(path)
            except Exception as e:
                logger.debug("pdf branch gagal: %s", e)

        # Office
        if ext in _OFFICE_EXTS or ext in _OFFICE_LEGACY:
            try:
                categories["office"] = _extract_office(path)
            except Exception as e:
                logger.debug("office branch gagal: %s", e)

        # Media
        if ext in _MEDIA_EXTS or (mime and (mime.startswith("video/") or mime.startswith("audio/"))):
            try:
                categories["media"] = await _extract_media(path)
            except Exception as e:
                logger.debug("media branch gagal: %s", e)

        return {
            "file_type": mime or "application/octet-stream",
            "size_bytes": size_bytes,
            "modified_at": modified_at,
            "categories": categories,
        }


_extractor: MetadataExtractor | None = None


def get_extractor() -> MetadataExtractor:
    global _extractor
    if _extractor is None:
        _extractor = MetadataExtractor()
    return _extractor
