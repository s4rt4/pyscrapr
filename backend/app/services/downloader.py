"""Async downloader with concurrency control + exponential backoff retry."""
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiofiles
import httpx

from app.utils.hash_helper import sha1_bytes

logger = logging.getLogger("pyscrapr.downloader")

# Retryable status codes and exception types
_RETRY_STATUS = {500, 502, 503, 504, 520, 521, 522, 523, 524, 429}
_RETRY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError, ConnectionError, OSError)


@dataclass
class DownloadResult:
    url: str
    ok: bool
    local_path: Optional[Path] = None
    size_bytes: int = 0
    content_type: Optional[str] = None
    sha1: Optional[str] = None
    error: Optional[str] = None
    retries_used: int = 0


class Downloader:
    def __init__(
        self,
        client: httpx.AsyncClient,
        max_concurrency: int = 8,
        max_retries: int = 3,
        ua_rotator: "UARotator | None" = None,
    ):
        self.client = client
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries
        self.ua_rotator = ua_rotator

    def _rotated_headers(self) -> dict[str, str]:
        if self.ua_rotator:
            return self.ua_rotator.get_headers()
        return {}

    async def _request_with_retry(self, url: str, **kwargs) -> tuple[httpx.Response, int]:
        """GET with exponential backoff + per-request UA rotation."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                headers = {**self._rotated_headers(), **kwargs.pop("headers", {})}
                r = await self.client.get(url, follow_redirects=True, headers=headers, **kwargs)
                if r.status_code in _RETRY_STATUS and attempt < self.max_retries:
                    wait = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    logger.debug("Retry %d/%d for %s (status %d)", attempt + 1, self.max_retries, url, r.status_code)
                    await asyncio.sleep(wait)
                    continue
                return r, attempt
            except _RETRY_EXCEPTIONS as e:
                last_exc = e
                if attempt < self.max_retries:
                    wait = (2 ** attempt) * 0.5
                    logger.debug("Retry %d/%d for %s (%s)", attempt + 1, self.max_retries, url, type(e).__name__)
                    await asyncio.sleep(wait)
                    continue
                raise
        # Should not reach here, but just in case
        raise last_exc or RuntimeError("Retry exhausted")

    async def fetch_html(self, url: str) -> str:
        r, _ = await self._request_with_retry(url)
        r.raise_for_status()
        return r.text

    async def download(self, url: str, target_dir: Path, filename: str) -> DownloadResult:
        async with self.semaphore:
            try:
                r, retries = await self._request_with_retry(url)
                r.raise_for_status()
                content = r.content
                sha1 = sha1_bytes(content)
                target_dir.mkdir(parents=True, exist_ok=True)
                path = target_dir / filename
                async with aiofiles.open(path, "wb") as f:
                    await f.write(content)
                return DownloadResult(
                    url=url,
                    ok=True,
                    local_path=path,
                    size_bytes=len(content),
                    content_type=r.headers.get("content-type"),
                    sha1=sha1,
                    retries_used=retries,
                )
            except Exception as e:
                return DownloadResult(url=url, ok=False, error=str(e))
