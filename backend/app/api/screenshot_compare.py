"""Screenshot compare endpoints — visual diff between two captured files."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings as app_config
from app.schemas.screenshot import (
    CompareFileRef,
    CompareRequest,
    CompareResponse,
    CompareStats,
)
from app.services import screenshot_compare as compare_service

logger = logging.getLogger("pyscrapr.screenshot")

router = APIRouter()

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-]+$")


def _screenshot_dir() -> Path:
    d = app_config.data_dir / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _compare_dir() -> Path:
    d = _screenshot_dir() / "compare"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("", response_model=CompareResponse)
async def do_compare(req: CompareRequest) -> CompareResponse:
    for name in (req.filename_a, req.filename_b):
        if not _SAFE_NAME.match(name):
            raise HTTPException(
                status_code=400, detail=f"Nama file tidak valid: {name}"
            )
    try:
        result = await compare_service.compare(
            job_id_a=req.job_id_a,
            filename_a=req.filename_a,
            job_id_b=req.job_id_b,
            filename_b=req.filename_b,
            output_dir=_compare_dir(),
            mode=req.mode.value if hasattr(req.mode, "value") else str(req.mode),
            threshold=req.threshold,
            source_dir=_screenshot_dir(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Compare failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Gagal compare: {exc}")

    return CompareResponse(
        comparison_id=result["comparison_id"],
        diff_image_url=result["diff_image_url"],
        mode=result["mode"],
        stats=CompareStats(**result["stats"]),
        file_a=CompareFileRef(**result["file_a"]),
        file_b=CompareFileRef(**result["file_b"]),
    )


@router.get("/file/{comparison_id}.png")
async def get_compare_file(comparison_id: str):
    if not _SAFE_NAME.match(comparison_id):
        raise HTTPException(status_code=400, detail="comparison_id tidak valid")
    path = _compare_dir() / f"{comparison_id}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Diff image tidak ditemukan")
    return FileResponse(
        path=str(path), media_type="image/png", filename=f"{comparison_id}.png"
    )
