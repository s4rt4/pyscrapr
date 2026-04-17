"""Custom Python pipeline executor.

User writes a Python snippet that transforms scraped data before storage/export.
Script runs via exec() in a restricted namespace — WARNING: not a sandbox.
For personal/offline use only.

Script contract:
  - Input variable: `data` (list of dicts)
  - Input variable: `url` (string, original job URL)
  - Input variable: `job_id` (string)
  - Output: modify `data` in-place, or assign new value to `output`
  - If neither, the original data is returned unchanged
"""
import json
import traceback
from pathlib import Path
from typing import Any

from app.config import settings

_PIPELINES_FILE = settings.data_dir / "pipelines.json"


def _load() -> dict[str, Any]:
    if not _PIPELINES_FILE.exists():
        return {}
    try:
        return json.loads(_PIPELINES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict[str, Any]) -> None:
    _PIPELINES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PIPELINES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ─── CRUD ───

def list_pipelines() -> list[dict]:
    store = _load()
    return [
        {"id": k, **v}
        for k, v in store.items()
    ]


def get_pipeline(pipeline_id: str) -> dict | None:
    store = _load()
    meta = store.get(pipeline_id)
    if not meta:
        return None
    return {"id": pipeline_id, **meta}


def save_pipeline(
    pipeline_id: str,
    name: str,
    description: str,
    code: str,
    enabled: bool = True,
    auto_run_on: list[str] | None = None,
) -> dict:
    store = _load()
    store[pipeline_id] = {
        "name": name,
        "description": description,
        "code": code,
        "enabled": enabled,
        "auto_run_on": auto_run_on or [],  # list of job types to auto-run on
    }
    _save(store)
    return {"id": pipeline_id, **store[pipeline_id]}


def find_pipelines_for_job_type(job_type: str) -> list[dict]:
    """Return all enabled pipelines configured to auto-run on this job type."""
    result = []
    for pid, meta in _load().items():
        if not meta.get("enabled", True):
            continue
        auto = meta.get("auto_run_on") or []
        if job_type in auto:
            result.append({"id": pid, **meta})
    return result


def delete_pipeline(pipeline_id: str) -> bool:
    store = _load()
    if pipeline_id not in store:
        return False
    del store[pipeline_id]
    _save(store)
    return True


# ─── Execution ───

def run_pipeline(
    code: str,
    data: list[dict],
    url: str = "",
    job_id: str = "",
) -> dict:
    """Execute user code against data. Returns {success, output, error, logs}.

    The script's stdout is captured; the final `output` or `data` variable is returned.
    """
    # Capture stdout
    import io
    import contextlib

    logs_io = io.StringIO()
    namespace: dict[str, Any] = {
        "data": list(data),  # copy so script can mutate safely
        "url": url,
        "job_id": job_id,
        "output": None,
        # Useful stdlib modules pre-imported for convenience
        "re": __import__("re"),
        "json": __import__("json"),
        "datetime": __import__("datetime"),
        "math": __import__("math"),
        "statistics": __import__("statistics"),
    }

    try:
        with contextlib.redirect_stdout(logs_io):
            exec(code, namespace)

        # Prefer explicit `output` if user set it, else modified `data`
        if namespace.get("output") is not None:
            result = namespace["output"]
        else:
            result = namespace.get("data", data)

        return {
            "success": True,
            "output": result,
            "output_type": type(result).__name__,
            "output_count": len(result) if hasattr(result, "__len__") else None,
            "logs": logs_io.getvalue(),
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(limit=5),
            "logs": logs_io.getvalue(),
        }
