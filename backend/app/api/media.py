"""Media Downloader endpoints (Phase 4)."""
import json
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.job import Job, JobStatus, JobType
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import AssetDTO, JobCreatedResponse, JobDTO
from app.schemas.media import (
    MediaProbeRequest,
    MediaProbeResponse,
    MediaStartRequest,
)
from app.services.event_bus import event_bus
from app.services.job_manager import job_manager
from app.services.media_downloader import media_downloader_service
from app.services.media_probe import probe

router = APIRouter()


@router.post("/probe", response_model=MediaProbeResponse)
async def probe_media(req: MediaProbeRequest):
    """Preview what a media URL will download (playlist entries, title, etc.)."""
    try:
        return await probe(str(req.url), req.use_browser_cookies)
    except Exception as e:
        raise HTTPException(400, f"Probe failed: {e}")


@router.post("/start", response_model=JobCreatedResponse)
async def start_media(
    req: MediaStartRequest,
    session: AsyncSession = Depends(get_session),
):
    # Hijack JobType.SITE_RIPPER? No — we need a new enum. For Phase 4 we'll
    # use the existing URL_MAPPER slot? No — we added the MEDIA_DOWNLOADER type.
    # Need to update the Job model enum.
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.MEDIA_DOWNLOADER,
        url=str(req.url),
        status=JobStatus.PENDING,
        config=req.model_dump(mode="json"),
        stats={},
    )
    repo = JobRepository(session)
    await repo.create(job)
    await session.commit()

    job_manager.submit(job_id, media_downloader_service.run, req=req)
    return JobCreatedResponse(job_id=job_id, status=JobStatus.PENDING)


@router.post("/stop/{job_id}")
async def stop_media(job_id: str):
    if not job_manager.stop(job_id):
        raise HTTPException(404, "Job not running")
    return {"ok": True}


@router.get("/jobs/{job_id}", response_model=JobDTO)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobDTO.model_validate(job)


@router.get("/jobs/{job_id}/items", response_model=list[AssetDTO])
async def list_items(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = AssetRepository(session)
    items = await repo.list_for_job(job_id, limit=5000)
    return [AssetDTO.model_validate(a) for a in items]


@router.get("/jobs/{job_id}/events")
async def stream_events(job_id: str):
    async def gen() -> AsyncGenerator[str, None]:
        async for event in event_bus.stream(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/file/{asset_id}")
async def download_file(
    job_id: str,
    asset_id: int,
    session: AsyncSession = Depends(get_session),
):
    repo = AssetRepository(session)
    assets = await repo.list_for_job(job_id, limit=10000)
    asset = next((a for a in assets if a.id == asset_id), None)
    if not asset or not asset.local_path:
        raise HTTPException(404, "Asset not found")
    p = Path(asset.local_path)
    if not p.exists():
        raise HTTPException(404, "File missing on disk")
    return FileResponse(str(p), filename=p.name)


@router.post("/jobs/{job_id}/open-folder")
async def open_folder(job_id: str, session: AsyncSession = Depends(get_session)):
    """Open output folder in OS file manager (cross-platform)."""
    repo = JobRepository(session)
    job = await repo.find_by_id(job_id)
    if not job or not job.output_dir:
        raise HTTPException(404, "No output folder")
    folder = Path(job.output_dir)
    if not folder.exists():
        raise HTTPException(404, "Folder missing")
    import subprocess
    import sys
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(folder)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return {"ok": True, "path": str(folder)}


@router.post("/test-bypass-proxy")
async def test_bypass_proxy(req: dict):
    """Test if a proxy URL works by fetching ifconfig.me/ip via the proxy.
    Body: {"proxy_url": "socks5://127.0.0.1:40000"}.
    Returns: {"ok": bool, "ip": str | None, "error": str | None, "latency_ms": int}
    """
    import time
    import httpx
    proxy_url = (req.get("proxy_url") or "").strip()
    if not proxy_url:
        raise HTTPException(422, "proxy_url required")
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15.0) as client:
            r = await client.get("https://api.ipify.org?format=json")
            r.raise_for_status()
            data = r.json()
            return {
                "ok": True,
                "ip": data.get("ip"),
                "error": None,
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
    except Exception as e:
        return {
            "ok": False,
            "ip": None,
            "error": f"{type(e).__name__}: {e}",
            "latency_ms": int((time.monotonic() - started) * 1000),
        }



@router.get("/warp-status")
async def warp_status():
    """Get Cloudflare WARP status. Returns mode + connected.

    Output of `warp-cli status` looks like:
      Status update: Connected
      Network: healthy
    Output of `warp-cli settings` includes mode info on one line.
    """
    import subprocess
    try:
        status_proc = subprocess.run(
            ["warp-cli", "status"], capture_output=True, text=True, timeout=8
        )
        status_out = (status_proc.stdout + status_proc.stderr).lower()
        connected = "connected" in status_out and "disconnected" not in status_out

        # Detect mode via settings command. WARP CLI output format varies by
        # version but consistently has a line "Mode: <value>" (case-sensitive
        # 'Mode:' with capital M, followed by tab/spaces then the value).
        settings_proc = subprocess.run(
            ["warp-cli", "settings"], capture_output=True, text=True, timeout=8
        )
        settings_raw = settings_proc.stdout + settings_proc.stderr
        mode = "unknown"
        import re
        # Match lines like:
        #   (user set)\tMode: Warp
        #   Mode: Proxy
        #   Operation mode: warp+doh
        for line in settings_raw.splitlines():
            # Skip false-positive lines like "Exclude mode, with hosts/ips:"
            # by anchoring on a Mode: pattern that captures the rest of line.
            m = re.search(r"\bMode:\s*(.+?)(?:\s*$|\s+on\s+port|\s+with\s+)", line, re.IGNORECASE)
            if not m:
                continue
            val = m.group(1).strip().lower()
            # WARP CLI 2025+ uses values like:
            #   "Warp"           -> full tunnel
            #   "WarpProxy on port 40000" (captured: "warpproxy")
            #   "Warp+DoH"       -> full tunnel with DNS over HTTPS
            #   "WarpDoT"        -> WARP with DoT
            # Check for "proxy" substring first (more specific) before "warp"
            if "proxy" in val:
                mode = "proxy"
                break
            if "dot" in val and "doh" not in val:
                mode = "dot"
                break
            if "warp" in val:
                mode = "warp"
                break

        return {
            "ok": True,
            "available": True,
            "connected": connected,
            "mode": mode,
            "raw_status": status_proc.stdout.strip()[:200],
        }
    except FileNotFoundError:
        return {"ok": False, "available": False, "error": "warp-cli tidak ditemukan di PATH"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "available": True, "error": "warp-cli timeout"}
    except Exception as e:
        return {"ok": False, "available": True, "error": f"{type(e).__name__}: {e}"}


@router.post("/warp-toggle")
async def warp_toggle(req: dict):
    """Switch Cloudflare WARP between full tunnel ('warp') and proxy ('proxy').

    Body: {"mode": "warp" | "proxy"}.

    Behavior:
      - mode="warp"  -> full tunnel (defeats SNI inspection, banking goes via Cloudflare)
      - mode="proxy" -> proxy mode (banking direct, only apps using 127.0.0.1:40000 tunneled)

    After switching, also issues warp-cli connect to ensure the connection is up.
    """
    import subprocess
    mode = (req.get("mode") or "").strip().lower()
    if mode not in ("warp", "proxy"):
        raise HTTPException(422, "mode harus 'warp' atau 'proxy'")
    try:
        # Disconnect first so the mode change is clean
        subprocess.run(["warp-cli", "disconnect"], capture_output=True, text=True, timeout=10)
        # Set mode
        set_proc = subprocess.run(
            ["warp-cli", "mode", mode], capture_output=True, text=True, timeout=10
        )
        if set_proc.returncode != 0:
            err = (set_proc.stdout + set_proc.stderr).strip()
            raise HTTPException(500, f"warp-cli mode gagal: {err[:200]}")
        # Reconnect
        connect_proc = subprocess.run(
            ["warp-cli", "connect"], capture_output=True, text=True, timeout=15
        )
        connect_out = (connect_proc.stdout + connect_proc.stderr).strip()
        # Wait briefly for connection to establish
        import asyncio
        await asyncio.sleep(2)

        # Auto-adjust bypass proxy setting so yt-dlp routes correctly:
        # - Full tunnel: disable bypass (WARP covers system traffic, port 40000
        #   is NOT listening so trying socks5://127.0.0.1:40000 fails refused)
        # - Proxy mode: enable bypass (port 40000 IS listening, route media via it)
        from app.services.settings_store import update as _update_settings
        if mode == "warp":
            _update_settings({"media_bypass_enabled": False})
        else:
            _update_settings({"media_bypass_enabled": True})

        return {
            "ok": True,
            "mode": mode,
            "connect_output": connect_out[:200],
            "bypass_auto_adjusted": True,
        }
    except FileNotFoundError:
        raise HTTPException(503, "warp-cli tidak ditemukan. Install Cloudflare WARP dulu.")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "warp-cli timeout")
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@router.post("/ssh-tunnel/start")
async def ssh_tunnel_start(req: dict = None):
    """Start SSH tunnel using saved settings (or override via body).

    Body (all optional, falls back to settings):
      {host, port, username, auth_method, password, key_path, local_port}

    Also auto-adjusts bypass proxy to point at the SSH SOCKS5 listener.
    """
    from app.services.settings_store import get as _get_setting, update as _update_setting
    from app.services.ssh_tunnel import get_tunnel

    body = req or {}
    cfg = {
        "host": body.get("host") or _get_setting("ssh_tunnel_host", ""),
        "port": int(body.get("port") or _get_setting("ssh_tunnel_port", 22)),
        "username": body.get("username") or _get_setting("ssh_tunnel_username", ""),
        "auth_method": body.get("auth_method") or _get_setting("ssh_tunnel_auth_method", "password"),
        "password": body.get("password") if body.get("password") is not None else _get_setting("ssh_tunnel_password", ""),
        "key_path": body.get("key_path") or _get_setting("ssh_tunnel_key_path", ""),
        "local_port": int(body.get("local_port") or _get_setting("ssh_tunnel_local_port", 1080)),
    }
    tunnel = get_tunnel()
    result = await tunnel.start(**cfg)
    if result.get("ok"):
        # Auto-update bypass proxy URL to point at this SSH tunnel
        _update_setting({
            "media_bypass_enabled": True,
            "media_bypass_proxy_url": f"socks5://127.0.0.1:{cfg['local_port']}",
        })
    return result


@router.post("/ssh-tunnel/stop")
async def ssh_tunnel_stop():
    from app.services.ssh_tunnel import get_tunnel
    return await get_tunnel().stop()


@router.get("/ssh-tunnel/status")
async def ssh_tunnel_status():
    from app.services.ssh_tunnel import get_tunnel
    return get_tunnel().status()
