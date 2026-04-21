"""Screenshot capture service using Playwright (headless Chromium).

Lazy-imports playwright so the module always loads cleanly even without the
dependency. Mirrors the graceful ImportError handling of playwright_renderer.py
but uses its own browser lifecycle because screenshot capture needs per-shot
viewport + color scheme emulation that we don't want to share with the HTML
renderer's singleton.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.services import settings_store
from app.services.ua_rotator import UARotator

logger = logging.getLogger("pyscrapr.screenshot")

_INSTALL_HINT = (
    "Playwright not installed. Run: pip install playwright && playwright install chromium"
)


class ScreenshotCapture:
    """Capture PNG screenshots with viewport + color scheme emulation."""

    VIEWPORTS: dict[str, dict[str, int]] = {
        "desktop": {"width": 1920, "height": 1080},
        "desktop_hd": {"width": 2560, "height": 1440},
        "laptop": {"width": 1366, "height": 768},
        "tablet": {"width": 768, "height": 1024},       # iPad portrait
        "mobile": {"width": 390, "height": 844},        # iPhone 14
        "mobile_sm": {"width": 375, "height": 667},     # iPhone SE
    }

    async def capture(
        self,
        url: str,
        output_dir: Path,
        job_id: str,
        viewport: str = "desktop",
        custom_width: int | None = None,
        custom_height: int | None = None,
        full_page: bool = True,
        dark_mode: bool = False,
        wait_until: str = "networkidle",
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """Capture a screenshot of ``url`` and save as PNG to ``output_dir``."""
        # Resolve viewport
        if viewport == "custom":
            if not custom_width or not custom_height:
                raise ValueError("custom viewport requires custom_width and custom_height")
            vp = {"width": int(custom_width), "height": int(custom_height)}
            viewport_used = f"custom {vp['width']}x{vp['height']}"
        else:
            if viewport not in self.VIEWPORTS:
                raise ValueError(
                    f"Unknown viewport '{viewport}'. Valid: {list(self.VIEWPORTS.keys()) + ['custom']}"
                )
            vp = dict(self.VIEWPORTS[viewport])
            viewport_used = viewport

        # Lazy import playwright
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            logger.error("Playwright import failed: %s", exc)
            raise RuntimeError(_INSTALL_HINT) from exc

        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"screenshot_{job_id}.png"

        ua = UARotator(mode=settings_store.get("ua_mode", "random")).get_headers().get(
            "User-Agent"
        )

        pw = None
        browser = None
        try:
            try:
                pw = await async_playwright().start()
                browser = await pw.chromium.launch(headless=True)
            except Exception as exc:
                msg = str(exc).lower()
                if (
                    "executable doesn't exist" in msg
                    or "browsertype.launch" in msg
                    or "playwright install" in msg
                ):
                    logger.error("Chromium binary missing: %s", exc)
                    raise RuntimeError(_INSTALL_HINT) from exc
                raise

            context = await browser.new_context(
                viewport=vp,
                user_agent=ua,
                color_scheme="dark" if dark_mode else "light",
            )
            try:
                page = await context.new_page()
                try:
                    await page.emulate_media(color_scheme="dark" if dark_mode else "light")
                except Exception as exc:
                    logger.debug("emulate_media failed (non-fatal): %s", exc)

                logger.info(
                    "Screenshot navigate: %s (viewport=%s dark=%s wait_until=%s)",
                    url, viewport_used, dark_mode, wait_until,
                )
                resp = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)

                status = resp.status if resp is not None else 0
                final_url = page.url
                try:
                    title = await page.title()
                except Exception:
                    title = ""

                await page.screenshot(path=str(file_path), full_page=full_page, type="png")

                # Image dimensions: for full_page we can't cheaply know final height
                # without re-reading the PNG, so read file and parse PNG header.
                dims = _read_png_dims(file_path) or {
                    "width": vp["width"],
                    "height": vp["height"],
                }

                return {
                    "file_path": str(file_path),
                    "file_url": f"/api/screenshot/file/{job_id}",
                    "dimensions": dims,
                    "file_size_bytes": file_path.stat().st_size,
                    "viewport_used": viewport_used,
                    "dark_mode": dark_mode,
                    "final_url": final_url,
                    "title": title or "",
                    "status": status,
                }
            finally:
                try:
                    await context.close()
                except Exception:
                    pass
        finally:
            try:
                if browser is not None:
                    await browser.close()
            except Exception as exc:
                logger.warning("Error closing browser: %s", exc)
            try:
                if pw is not None:
                    await pw.stop()
            except Exception as exc:
                logger.warning("Error stopping playwright: %s", exc)


def _read_png_dims(path: Path) -> Optional[dict[str, int]]:
    """Parse PNG IHDR for dimensions. Avoids extra Pillow dep."""
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        return {"width": width, "height": height}
    except Exception:
        return None


_capture: Optional[ScreenshotCapture] = None


def get_capture() -> ScreenshotCapture:
    global _capture
    if _capture is None:
        _capture = ScreenshotCapture()
    return _capture
