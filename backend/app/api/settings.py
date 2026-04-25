"""User settings CRUD + dependency management endpoints."""
import asyncio
import subprocess
import sys

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.settings_store import get_all, get_defaults, reset, update

router = APIRouter()


class SettingsPatch(BaseModel):
    """Partial update — only send fields you want to change."""

    class Config:
        extra = "allow"


@router.get("")
async def get_settings():
    return {"settings": get_all(), "defaults": get_defaults()}


@router.put("")
async def update_settings(patch: SettingsPatch):
    updated = update(patch.model_dump(exclude_unset=True))
    return {"settings": updated}


@router.post("/reset")
async def reset_settings():
    data = reset()
    return {"settings": data}


# ─── Dependency management ───

# Packages that benefit from one-click updates (external sites change their API)
_MANAGED_DEPS = {
    "yt-dlp": {
        "pip_name": "yt-dlp",
        "import_name": "yt_dlp",
        "version_attr": "version.__version__",
        "description": "Media download engine — YouTube, IG, TikTok, 1000+ sites",
        "why_update": "YouTube/Instagram sering update teknologi. Update jika download gagal.",
    },
    "browser-cookie3": {
        "pip_name": "browser-cookie3",
        "import_name": "browser_cookie3",
        "version_attr": "__version__",
        "description": "Browser cookie import — Chrome, Firefox, Edge",
        "why_update": "Chrome update sering ubah format enkripsi cookies. Update jika login scraping gagal.",
    },
}


def _run_pip(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pip", *args],
        capture_output=True, text=True, timeout=timeout,
    )


def _get_installed_version(import_name: str, version_attr: str) -> str:
    # Try direct attribute first
    try:
        mod = __import__(import_name)
        parts = version_attr.split(".")
        obj = mod
        for p in parts:
            obj = getattr(obj, p)
        return str(obj)
    except Exception:
        pass
    # Fallback: importlib.metadata (works for all installed packages)
    try:
        import importlib.metadata
        # Convert import_name (underscore) to pip name (hyphen)
        for name_variant in [import_name, import_name.replace("_", "-")]:
            try:
                return importlib.metadata.version(name_variant)
            except importlib.metadata.PackageNotFoundError:
                continue
    except Exception:
        pass
    return "not installed"


def _norm_version(v: str) -> str:
    """Normalize: 2026.03.17 → 2026.3.17"""
    try:
        return ".".join(str(int(p)) for p in v.split(".") if p.isdigit())
    except Exception:
        return v


def _check_pypi_latest(pip_name: str) -> str | None:
    try:
        r = _run_pip("index", "versions", pip_name, timeout=15)
        if "(" in r.stdout and ")" in r.stdout:
            return r.stdout.split("(")[1].split(")")[0].strip()
    except Exception:
        pass
    try:
        r = _run_pip("install", f"{pip_name}==0.0.0.0.0.0.0", timeout=15)
        if "from versions:" in r.stderr:
            versions = r.stderr.split("from versions:")[1].split(")")[0].strip()
            parts = [v.strip() for v in versions.split(",") if v.strip()]
            return parts[-1] if parts else None
    except Exception:
        pass
    return None


@router.get("/deps")
async def list_dependencies():
    """List all managed dependencies with current + latest version."""

    def _check_all():
        results = []
        for key, meta in _MANAGED_DEPS.items():
            current = _get_installed_version(meta["import_name"], meta["version_attr"])
            latest = _check_pypi_latest(meta["pip_name"])
            update_available = bool(
                latest and current != "not installed"
                and _norm_version(latest) != _norm_version(current)
            )
            results.append({
                "key": key,
                "pip_name": meta["pip_name"],
                "description": meta["description"],
                "why_update": meta["why_update"],
                "current": current,
                "latest": latest,
                "update_available": update_available,
            })
        return results

    return await asyncio.to_thread(_check_all)


@router.post("/deps/{dep_key}/update")
async def update_dependency(dep_key: str):
    """Update a single managed dependency."""
    meta = _MANAGED_DEPS.get(dep_key)
    if not meta:
        from fastapi import HTTPException
        raise HTTPException(404, f"Unknown dependency: {dep_key}")

    def _do():
        try:
            # Drop --user flag: it installs to user-site but Python may load
            # from system-site first, leaving the old version active. Install
            # to the same location as the existing package instead.
            result = _run_pip("install", "--upgrade", meta["pip_name"], timeout=120)
            output = result.stdout + result.stderr
            success = result.returncode == 0 or "already satisfied" in output.lower()

            # Use importlib.metadata (queries pip's installed version)
            # rather than importing the module - on Windows the loaded module
            # may still reflect the old in-process state until backend restart.
            try:
                import importlib
                import importlib.metadata
                # Force-refresh metadata cache
                importlib.invalidate_caches()
            except Exception:
                pass
            new_version = _get_installed_version(meta["import_name"], meta["version_attr"])

            return {
                "success": success,
                "package": meta["pip_name"],
                "version": new_version,
                "output": output[-500:] if len(output) > 500 else output,
                "restart_required": True,  # Hint to user
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "package": meta["pip_name"], "version": None, "output": "Timed out (>120s). Check network."}
        except Exception as e:
            return {"success": False, "package": meta["pip_name"], "version": None, "output": f"{type(e).__name__}: {e}"}

    return await asyncio.to_thread(_do)


@router.post("/deps/update-all")
async def update_all_dependencies():
    """Update all managed dependencies at once."""

    def _do():
        results = []
        for key, meta in _MANAGED_DEPS.items():
            try:
                result = _run_pip("install", "--upgrade", meta["pip_name"], timeout=120)
                output = result.stdout + result.stderr
                success = result.returncode == 0 or "already satisfied" in output.lower()
                new_version = _get_installed_version(meta["import_name"], meta["version_attr"])
                results.append({"package": meta["pip_name"], "success": success, "version": new_version})
            except Exception as e:
                results.append({"package": meta["pip_name"], "success": False, "version": None, "error": str(e)})
        return results

    return await asyncio.to_thread(_do)


# Keep backward compat for old endpoints
@router.get("/ytdlp-version")
async def ytdlp_version():
    deps = await list_dependencies()
    yt = next((d for d in deps if d["key"] == "yt-dlp"), None)
    if not yt:
        return {"current": "unknown", "latest": None, "update_available": False}
    return {"current": yt["current"], "latest": yt["latest"], "update_available": yt["update_available"]}


@router.post("/ytdlp-update")
async def ytdlp_update():
    return await update_dependency("yt-dlp")
