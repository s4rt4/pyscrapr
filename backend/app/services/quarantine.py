"""Manual file quarantine - move into isolated folder + manifest."""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from app.config import settings as app_config

logger = logging.getLogger("pyscrapr.threat.quarantine")

QUARANTINE_DIR = app_config.data_dir / "quarantine"


def _ensure_dir() -> Path:
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    return QUARANTINE_DIR


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def quarantine_file(source: Path, reason: str, scan_report_id: str | None = None) -> dict[str, Any]:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"File tidak ditemukan: {source}")

    base = _ensure_dir()
    sha = _sha256_file(source)
    ts = int(time.time())
    safe_name = source.name.replace("..", "_")
    target_name = f"{ts}_{sha[:8]}_{safe_name}"

    # Windows: append .txt to neutralize accidental execution
    if sys.platform == "win32":
        target_name += ".txt"

    target = base / target_name
    shutil.move(str(source), str(target))

    manifest = {
        "id": f"{ts}_{sha[:8]}",
        "original_path": str(source),
        "quarantine_path": str(target),
        "sha256": sha,
        "moved_at": ts,
        "reason": reason,
        "scan_report_id": scan_report_id,
    }
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "quarantine_path": str(target),
        "manifest_path": str(manifest_path),
        "sha256": sha,
        "id": manifest["id"],
    }


def list_quarantine() -> list[dict[str, Any]]:
    base = _ensure_dir()
    out = []
    for mf in sorted(base.glob("*.manifest.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            out.append(data)
        except Exception as e:
            logger.debug("manifest baca gagal %s: %s", mf, e)
    return out


def restore_file(quarantine_id: str) -> dict[str, Any]:
    base = _ensure_dir()
    for mf in base.glob("*.manifest.json"):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("id") != quarantine_id:
            continue
        qpath = Path(data["quarantine_path"])
        orig = Path(data["original_path"])
        if not qpath.exists():
            raise FileNotFoundError(f"File karantina hilang: {qpath}")
        orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(qpath), str(orig))
        try:
            mf.unlink()
        except Exception:
            pass
        return {"restored_to": str(orig), "id": quarantine_id}
    raise FileNotFoundError(f"Entri karantina tidak ditemukan: {quarantine_id}")
