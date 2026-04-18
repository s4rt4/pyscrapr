"""Cluster / worker-pool endpoints — used on the MASTER side to query,
dispatch to, and proxy status from remote worker instances.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import settings_store
from app.services.worker_dispatcher import worker_dispatcher

logger = logging.getLogger("pyscrapr.worker")

router = APIRouter()


class DispatchRequest(BaseModel):
    job_type: str = Field(..., description="harvester | mapper | ripper | media")
    payload: dict[str, Any] = Field(default_factory=dict)
    worker_url: str | None = Field(default=None, description="If None, auto-picks by strategy")


@router.get("/workers")
async def list_workers():
    """Return health + latency for each configured worker URL."""
    workers = worker_dispatcher.get_workers()
    if not workers:
        return []
    results = await asyncio.gather(
        *(worker_dispatcher.health_check_with_latency(w) for w in workers)
    )
    return [
        {"url": url, "healthy": healthy, "latency_ms": latency_ms}
        for url, (healthy, latency_ms) in zip(workers, results)
    ]


@router.post("/dispatch")
async def dispatch_job(req: DispatchRequest):
    """Dispatch a job to a remote worker. If `worker_url` is None, auto-picks."""
    if not settings_store.get("worker_enabled", False):
        raise HTTPException(400, "worker_enabled is False — remote dispatch is disabled")

    try:
        if req.worker_url:
            target = req.worker_url.rstrip("/")
            body = {"job_type": req.job_type, "payload": req.payload}
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Content-Type": "application/json"}
                token = settings_store.get("worker_auth_token", "") or ""
                if token:
                    headers["X-Worker-Token"] = token
                resp = await client.post(
                    f"{target}/api/worker/submit", json=body, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
            return {
                "worker_url": target,
                "remote_job_id": data.get("job_id"),
                "status": data.get("status", "accepted"),
            }
        return await worker_dispatcher.dispatch(req.job_type, req.payload)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Worker dispatch failed: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/remote-job/{worker_url:path}/{job_id}")
async def remote_job_status(worker_url: str, job_id: str):
    """Proxy to `{worker_url}/api/worker/status/{job_id}`. `worker_url` must be
    URL-encoded by the caller (e.g. `http%3A%2F%2F192.168.1.10%3A8000`)."""
    decoded = unquote(worker_url).rstrip("/")
    if not decoded.startswith(("http://", "https://")):
        raise HTTPException(400, "worker_url must be an absolute http(s) URL")
    try:
        data = await worker_dispatcher.remote_job_status(decoded, job_id)
        return data
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, f"Remote error: {exc}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Worker query failed: {exc}") from exc
