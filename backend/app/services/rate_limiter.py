"""Per-host async rate limiter using a simple token bucket."""
import asyncio
import time
from typing import Optional

from app.services.url_normalizer import get_host


class HostRateLimiter:
    def __init__(self, default_rps: float = 1.0):
        self.default_rps = default_rps
        self._per_host_rps: dict[str, float] = {}
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def set_host_rps(self, host: str, rps: float) -> None:
        self._per_host_rps[host] = rps

    def _get_lock(self, host: str) -> asyncio.Lock:
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def wait(self, url: str) -> None:
        """Block until the calling coroutine may make a request for this URL."""
        host = get_host(url)
        if not host:
            return

        async with self._global_lock:
            lock = self._get_lock(host)

        async with lock:
            rps = self._per_host_rps.get(host, self.default_rps)
            min_interval = 1.0 / max(rps, 0.01)
            now = time.monotonic()
            last = self._last_request.get(host, 0.0)
            delay = min_interval - (now - last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request[host] = time.monotonic()
