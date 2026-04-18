"""Playwright (headless Chromium) renderer for JS-heavy sites.

Lazy import: we only try to import playwright at call time so the module itself
always loads cleanly even when playwright isn't installed. This lets the rest
of the app run unchanged and only errors out when the user actually requests
a Playwright-rendered fetch.

Usage:
    renderer = await get_renderer()
    html = await renderer.fetch_html(url)

Browser lifecycle is managed via a process-wide singleton. Call
    await shutdown_renderer()
on app shutdown to close the browser cleanly.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.services import settings_store
from app.services.proxy_manager import ProxyManager
from app.services.ua_rotator import UARotator

logger = logging.getLogger("pyscrapr.playwright")

_INSTALL_HINT = (
    "Playwright not installed. Run: pip install playwright && playwright install chromium"
)


class PlaywrightRenderer:
    """Headless Chromium renderer.

    Can be used as async context manager or as a shared singleton via
    ``get_renderer()``. Browser is launched once and reused for all fetches.
    """

    def __init__(
        self,
        wait_until: str = "networkidle",
        timeout: int = 30000,
    ) -> None:
        self.wait_until = wait_until
        self.timeout = timeout
        self._pw: Any = None
        self._browser: Any = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "PlaywrightRenderer":
        await self._ensure_browser()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        async with self._lock:
            if self._browser is not None:
                return
            try:
                from playwright.async_api import async_playwright  # type: ignore
            except ImportError as exc:
                logger.error("Playwright import failed: %s", exc)
                raise RuntimeError(_INSTALL_HINT) from exc

            # Proxy (browser-level, applied to every page)
            proxy_list = [
                p for p in (settings_store.get("proxy_list", "") or "").splitlines() if p.strip()
            ]
            proxy_mode = settings_store.get("proxy_mode", "none")
            pm = ProxyManager(proxies=proxy_list, mode=proxy_mode)
            proxy_url = pm.get_proxy() if pm.enabled else None
            launch_kwargs: dict[str, Any] = {"headless": True}
            if proxy_url:
                launch_kwargs["proxy"] = {"server": proxy_url}
                logger.info("Launching Chromium via proxy: %s", proxy_url)

            try:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(**launch_kwargs)
            except Exception as exc:
                msg = str(exc).lower()
                # Detect missing browser binary
                if (
                    "executable doesn't exist" in msg
                    or "browsertype.launch" in msg
                    or "playwright install" in msg
                ):
                    logger.error("Chromium binary missing: %s", exc)
                    # Best-effort cleanup
                    try:
                        if self._pw is not None:
                            await self._pw.stop()
                    except Exception:
                        pass
                    self._pw = None
                    self._browser = None
                    raise RuntimeError(_INSTALL_HINT) from exc
                raise

    async def fetch_html(
        self,
        url: str,
        wait_until: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """Navigate to URL in a fresh page and return rendered HTML."""
        await self._ensure_browser()
        assert self._browser is not None

        wu = wait_until or self.wait_until
        to = timeout or self.timeout

        # UA per-page (new context per fetch gives clean cookies)
        ua = UARotator(mode=settings_store.get("ua_mode", "random")).get_headers().get(
            "User-Agent"
        )

        context = await self._browser.new_context(user_agent=ua)
        try:
            page = await context.new_page()
            logger.debug("Playwright navigate: %s (wait_until=%s, timeout=%s)", url, wu, to)
            await page.goto(url, wait_until=wu, timeout=to)
            html = await page.content()
            return html
        finally:
            try:
                await context.close()
            except Exception:
                pass

    async def close(self) -> None:
        try:
            if self._browser is not None:
                await self._browser.close()
        except Exception as exc:
            logger.warning("Error closing browser: %s", exc)
        finally:
            self._browser = None
        try:
            if self._pw is not None:
                await self._pw.stop()
        except Exception as exc:
            logger.warning("Error stopping playwright: %s", exc)
        finally:
            self._pw = None


# ─────────────── singleton ───────────────

_renderer: Optional[PlaywrightRenderer] = None
_renderer_lock = asyncio.Lock()


async def get_renderer() -> PlaywrightRenderer:
    """Return a shared, lazy-initialized PlaywrightRenderer."""
    global _renderer
    if _renderer is not None and _renderer._browser is not None:
        return _renderer
    async with _renderer_lock:
        if _renderer is None:
            _renderer = PlaywrightRenderer(
                wait_until=settings_store.get("playwright_wait_until", "networkidle"),
                timeout=int(settings_store.get("playwright_timeout_ms", 30000)),
            )
        await _renderer._ensure_browser()
        return _renderer


async def shutdown_renderer() -> None:
    """Close the shared browser (call on app shutdown)."""
    global _renderer
    if _renderer is not None:
        await _renderer.close()
        _renderer = None
