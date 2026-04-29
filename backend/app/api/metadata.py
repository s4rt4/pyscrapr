"""Metadata Inspector endpoints."""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.metadata import MetadataInspectRequest, MetadataInspectResponse
from app.services.metadata_extractor import get_extractor

logger = logging.getLogger("pyscrapr.api.metadata")

router = APIRouter()

_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


def _validate_path(p_str: str) -> Path:
    if not p_str or not p_str.strip():
        raise HTTPException(status_code=422, detail="path wajib diisi")
    p = Path(p_str.strip())
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path tidak ditemukan: {p_str}")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Path bukan berkas (file).")
    if not os.access(p, os.R_OK):
        raise HTTPException(status_code=403, detail="Berkas tidak dapat dibaca.")
    return p


@router.post("/inspect", response_model=MetadataInspectResponse)
async def inspect_post(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = None,
):
    """Inspect metadata.

    Two modes detected from request:
    - multipart/form-data with `file` field -> upload mode
    - JSON `{path: str}` body -> path mode

    For convenience this endpoint also accepts a `path` query/form parameter.
    """
    extractor = get_extractor()

    if file is not None:
        tmp_dir = Path(tempfile.gettempdir()) / "pyscrapr_metadata"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        safe_name = os.path.basename(file.filename or "upload")
        tmp_path = tmp_dir / f"meta_{os.getpid()}_{safe_name}"
        try:
            data = await file.read()
            if len(data) > _MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Berkas melebihi 100 MB.")
            tmp_path.write_bytes(data)
            return await extractor.extract(tmp_path)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("inspect upload gagal: %s", e)
            raise HTTPException(status_code=500, detail=f"Inspeksi gagal: {e}")
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    if path:
        p = _validate_path(path)
        try:
            return await extractor.extract(p)
        except Exception as e:
            logger.exception("inspect path gagal: %s", e)
            raise HTTPException(status_code=500, detail=f"Inspeksi gagal: {e}")

    raise HTTPException(status_code=422, detail="Sertakan field 'file' atau parameter 'path'.")


@router.post("/inspect/path", response_model=MetadataInspectResponse)
async def inspect_path_json(req: MetadataInspectRequest):
    """JSON-body convenience for path mode."""
    p = _validate_path(req.path)
    try:
        return await get_extractor().extract(p)
    except Exception as e:
        logger.exception("inspect path gagal: %s", e)
        raise HTTPException(status_code=500, detail=f"Inspeksi gagal: {e}")


@router.get("/inspect", response_model=MetadataInspectResponse)
async def inspect_get(path: str = Query(..., description="Absolute file path")):
    """GET variant for deep-link integration from other tools."""
    p = _validate_path(path)
    try:
        return await get_extractor().extract(p)
    except Exception as e:
        logger.exception("inspect path (GET) gagal: %s", e)
        raise HTTPException(status_code=500, detail=f"Inspeksi gagal: {e}")
