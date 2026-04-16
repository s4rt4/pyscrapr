"""robots.txt checker with per-host caching."""
import asyncio
from typing import Optional
from urllib.robotparser import RobotFileParser

import httpx

from app.services.url_normalizer import get_host


class RobotsChecker:
    def __init__(self, client: httpx.AsyncClient, user_agent: str):
        self.client = client
        self.user_agent = user_agent
        self._cache: dict[str, Optional[RobotFileParser]] = {}
        self._lock = asyncio.Lock()

    async def _load(self, host: str, scheme: str = "https") -> Optional[RobotFileParser]:
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            r = await self.client.get(robots_url, timeout=10)
            if r.status_code >= 400:
                return None
            rp = RobotFileParser()
            rp.parse(r.text.splitlines())
            return rp
        except Exception:
            return None

    async def allowed(self, url: str) -> bool:
        host = get_host(url)
        if not host:
            return True
        async with self._lock:
            if host not in self._cache:
                scheme = "https" if url.startswith("https") else "http"
                self._cache[host] = await self._load(host, scheme)
        rp = self._cache.get(host)
        if rp is None:
            return True  # failed to fetch robots.txt → be permissive
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True

    async def crawl_delay(self, url: str) -> Optional[float]:
        host = get_host(url)
        rp = self._cache.get(host)
        if rp is None:
            return None
        try:
            return rp.crawl_delay(self.user_agent)
        except Exception:
            return None
