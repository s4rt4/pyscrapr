"""Worker node dispatcher — coordinates remote job submission across a pool
of headless PyScrapr backend instances.

Design: lightweight HTTP-only. No message broker. Master POSTs jobs directly
to worker URLs and polls for status. Round-robin / random / least-loaded
strategies supported.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from app.services import settings_store

logger = logging.getLogger("pyscrapr.worker")

_TIMEOUT = 10.0


class WorkerDispatcher:
    def __init__(self) -> None:
        self._rr_index = 0
        # Track approximate load per worker URL (incremented on dispatch)
        self._load: dict[str, int] = {}

    # ---------- pool helpers ----------

    def get_workers(self) -> list[str]:
        """Return cleaned worker URL pool from settings."""
        raw = settings_store.get("worker_pool", "") or ""
        urls: list[str] = []
        # Allow both comma and newline separators
        for chunk in raw.replace("\n", ",").split(","):
            url = chunk.strip().rstrip("/")
            if url:
                urls.append(url)
        return urls

    def _strategy(self) -> str:
        return settings_store.get("worker_dispatch_strategy", "round_robin") or "round_robin"

    def _token(self) -> str:
        return settings_store.get("worker_auth_token", "") or ""

    # ---------- picking ----------

    async def pick_worker(self) -> str | None:
        workers = self.get_workers()
        if not workers:
            return None
        strategy = self._strategy()
        if strategy == "random":
            return random.choice(workers)
        if strategy == "least_loaded":
            return min(workers, key=lambda u: self._load.get(u, 0))
        # default round_robin
        url = workers[self._rr_index % len(workers)]
        self._rr_index = (self._rr_index + 1) % len(workers)
        return url

    # ---------- HTTP ops ----------

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self._token()
        if token:
            headers["X-Worker-Token"] = token
        return headers

    async def dispatch(self, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a job to the next worker. Returns dispatch metadata.

        Raises RuntimeError if no workers available, or httpx errors on failure.
        """
        worker_url = await self.pick_worker()
        if not worker_url:
            raise RuntimeError("No workers configured in pool")
        url = f"{worker_url}/api/worker/submit"
        body = {"job_type": job_type, "payload": payload}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            logger.info("Dispatching %s job to %s", job_type, worker_url)
            resp = await client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        self._load[worker_url] = self._load.get(worker_url, 0) + 1
        return {
            "worker_url": worker_url,
            "remote_job_id": data.get("job_id"),
            "status": data.get("status", "accepted"),
        }

    async def health_check(self, worker_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(f"{worker_url}/api/worker/health")
                return resp.status_code == 200
        except Exception as exc:
            logger.debug("Health check failed for %s: %s", worker_url, exc)
            return False

    async def health_check_with_latency(self, worker_url: str) -> tuple[bool, int]:
        start = time.perf_counter()
        ok = False
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(f"{worker_url}/api/worker/health")
                ok = resp.status_code == 200
        except Exception as exc:
            logger.debug("Health check failed for %s: %s", worker_url, exc)
            ok = False
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ok, latency_ms

    async def health_all(self) -> dict[str, bool]:
        workers = self.get_workers()
        if not workers:
            return {}
        results = await asyncio.gather(*(self.health_check(w) for w in workers))
        return dict(zip(workers, results))

    async def remote_job_status(self, worker_url: str, job_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{worker_url}/api/worker/status/{job_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()


worker_dispatcher = WorkerDispatcher()
