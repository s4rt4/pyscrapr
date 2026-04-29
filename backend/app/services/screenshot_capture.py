"""Screenshot capture service using Playwright (headless Chromium).

Supports multi-viewport, multi-scheme, multiple output formats, element capture,
element hiding, custom CSS, text watermark, retina scale, auth vault cookies,
lazy-load scroll, and batch mode via shared browser.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from app.services import auth_vault, settings_store
from app.services.ua_rotator import UARotator

logger = logging.getLogger("pyscrapr.screenshot")

_INSTALL_HINT = (
    "Playwright belum terpasang. Jalankan dua perintah berurutan: "
    "pip install playwright ; lalu: python -m playwright install chromium"
)

_FNAME_SAFE = re.compile(r"[^a-zA-Z0-9_\-.]")


def _sanitize(part: str) -> str:
    return _FNAME_SAFE.sub("_", part)[:60]


class ScreenshotCapture:
    """Capture screenshots with viewport, color scheme, and format options."""

    VIEWPORTS: dict[str, dict[str, int]] = {
        "desktop": {"width": 1920, "height": 1080},
        "desktop_hd": {"width": 2560, "height": 1440},
        "laptop": {"width": 1366, "height": 768},
        "tablet": {"width": 768, "height": 1024},
        "mobile": {"width": 390, "height": 844},
        "mobile_sm": {"width": 375, "height": 667},
    }

    _WM_POS_CSS = {
        "top-left": "top: 20px; left: 20px;",
        "top-right": "top: 20px; right: 20px;",
        "bottom-left": "bottom: 20px; left: 20px;",
        "bottom-right": "bottom: 20px; right: 20px;",
        "center": "top: 50%; left: 50%; transform: translate(-50%, -50%);",
    }

    def _resolve_viewport(
        self,
        viewport: str,
        custom_width: int | None,
        custom_height: int | None,
    ) -> tuple[dict[str, int], str]:
        if viewport == "custom":
            if not custom_width or not custom_height:
                raise ValueError("Viewport custom butuh custom_width dan custom_height")
            vp = {"width": int(custom_width), "height": int(custom_height)}
            return vp, f"custom_{vp['width']}x{vp['height']}"
        if viewport not in self.VIEWPORTS:
            raise ValueError(
                f"Viewport '{viewport}' tidak dikenal. Valid: "
                f"{list(self.VIEWPORTS.keys()) + ['custom']}"
            )
        return dict(self.VIEWPORTS[viewport]), viewport

    def _watermark_css(self, text: str, position: str, opacity: float) -> str:
        pos_css = self._WM_POS_CSS.get(position, self._WM_POS_CSS["bottom-right"])
        # Escape for CSS string literal: backslash and double-quote.
        safe = text.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'body::after {'
            f' content: "{safe}";'
            ' position: fixed;'
            f' {pos_css}'
            ' font-size: 14px;'
            ' background: rgba(0,0,0,0.6);'
            ' color: white;'
            ' padding: 6px 12px;'
            ' border-radius: 4px;'
            ' z-index: 999999;'
            f' opacity: {opacity};'
            ' pointer-events: none;'
            '}'
        )

    async def _auto_scroll(self, page: Any) -> None:
        await page.evaluate(
            """
            async () => {
                await new Promise(resolve => {
                    let total = 0;
                    const dist = 200;
                    const timer = setInterval(() => {
                        window.scrollBy(0, dist);
                        total += dist;
                        if (total >= document.body.scrollHeight) {
                            clearInterval(timer);
                            window.scrollTo(0, 0);
                            resolve();
                        }
                    }, 100);
                });
            }
            """
        )

    def _build_filename(
        self,
        job_id: str,
        viewport_label: str,
        scheme: str,
        fmt: str,
        element_index: int | None = None,
    ) -> str:
        parts = ["screenshot", job_id, _sanitize(viewport_label), scheme]
        if element_index is not None:
            parts.append(f"el{element_index}")
        ext = "pdf" if fmt == "pdf" else fmt
        return "_".join(parts) + f".{ext}"

    async def _inject_auth_cookies(self, context: Any, url: str) -> None:
        try:
            args = auth_vault.get_httpx_args(url)
        except Exception as exc:
            logger.debug("auth_vault lookup failed: %s", exc)
            return
        cookies_map = args.get("cookies") or {}
        if not cookies_map:
            return
        host = urlparse(url).netloc
        if not host:
            return
        pw_cookies = [
            {"name": k, "value": str(v), "domain": host, "path": "/"}
            for k, v in cookies_map.items()
        ]
        try:
            await context.add_cookies(pw_cookies)
        except Exception as exc:
            logger.warning("Gagal inject cookies dari auth_vault: %s", exc)

    async def _capture_one_combo(
        self,
        browser: Any,
        url: str,
        output_dir: Path,
        job_id: str,
        viewport_key: str,
        custom_width: int | None,
        custom_height: int | None,
        full_page: bool,
        scheme: str,
        device_scale: float,
        output_format: str,
        jpeg_quality: int,
        element_selector: str | None,
        multiple_elements: bool,
        hide_selectors: list[str] | None,
        wait_for_selector: str | None,
        wait_until: str,
        scroll_through: bool,
        timeout_ms: int,
        custom_css: str | None,
        watermark_text: str | None,
        watermark_position: str,
        watermark_opacity: float,
        use_auth_vault: bool,
        ua: str | None,
    ) -> tuple[list[dict], dict[str, Any]]:
        """Capture one (viewport, scheme) combination. Returns (captures, meta)."""
        vp, viewport_label = self._resolve_viewport(viewport_key, custom_width, custom_height)
        context = await browser.new_context(
            viewport=vp,
            user_agent=ua,
            color_scheme=scheme,
            device_scale_factor=float(device_scale),
        )
        try:
            if use_auth_vault:
                await self._inject_auth_cookies(context, url)

            page = await context.new_page()
            from app.services.playwright_stealth_helper import apply_stealth_to_page
            await apply_stealth_to_page(page)
            try:
                await page.emulate_media(color_scheme=scheme)
            except Exception as exc:
                logger.debug("emulate_media failed: %s", exc)

            logger.info(
                "Screenshot navigate: %s (viewport=%s scheme=%s fmt=%s)",
                url, viewport_label, scheme, output_format,
            )
            resp = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            status = resp.status if resp is not None else 0
            final_url = page.url
            try:
                title = await page.title()
            except Exception:
                title = ""

            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
                except Exception as exc:
                    logger.warning("wait_for_selector '%s' gagal: %s", wait_for_selector, exc)

            # Inject hide selectors
            if hide_selectors:
                for sel in hide_selectors:
                    safe_sel = sel.replace("\\", "\\\\")
                    try:
                        await page.add_style_tag(
                            content=f"{safe_sel} {{ display: none !important; }}"
                        )
                    except Exception as exc:
                        logger.debug("hide selector '%s' failed: %s", sel, exc)

            if custom_css:
                try:
                    await page.add_style_tag(content=custom_css)
                except Exception as exc:
                    logger.debug("custom_css failed: %s", exc)

            if watermark_text:
                try:
                    await page.add_style_tag(
                        content=self._watermark_css(
                            watermark_text, watermark_position, watermark_opacity
                        )
                    )
                except Exception as exc:
                    logger.debug("watermark failed: %s", exc)

            if scroll_through:
                try:
                    await self._auto_scroll(page)
                except Exception as exc:
                    logger.debug("auto-scroll failed: %s", exc)

            captures: list[dict] = []

            # --- PDF branch (full page only, no element capture) ---
            if output_format == "pdf":
                fname = self._build_filename(job_id, viewport_label, scheme, "pdf")
                fpath = output_dir / fname
                await page.pdf(path=str(fpath), print_background=True)
                size = fpath.stat().st_size
                captures.append(self._pack_result(
                    fpath, job_id, fname, vp, viewport_label, scheme, "pdf", size, None
                ))
                return captures, {"final_url": final_url, "title": title or "", "status": status}

            # --- Element screenshot(s) ---
            if element_selector:
                locator = page.locator(element_selector)
                if multiple_elements:
                    handles = await locator.all()
                    if not handles:
                        raise RuntimeError(
                            f"Tidak ada elemen cocok untuk selector: {element_selector}"
                        )
                    for idx, el in enumerate(handles):
                        captures.append(
                            await self._shoot_element(
                                el, output_dir, job_id, viewport_label, scheme,
                                output_format, jpeg_quality, vp, idx,
                            )
                        )
                else:
                    el = locator.first
                    captures.append(
                        await self._shoot_element(
                            el, output_dir, job_id, viewport_label, scheme,
                            output_format, jpeg_quality, vp, None,
                        )
                    )
                return captures, {"final_url": final_url, "title": title or "", "status": status}

            # --- Full page / viewport screenshot ---
            captures.append(
                await self._shoot_page(
                    page, output_dir, job_id, viewport_label, scheme,
                    output_format, jpeg_quality, full_page, vp,
                )
            )
            return captures, {"final_url": final_url, "title": title or "", "status": status}
        finally:
            try:
                await context.close()
            except Exception:
                pass

    async def _shoot_page(
        self,
        page: Any,
        output_dir: Path,
        job_id: str,
        viewport_label: str,
        scheme: str,
        output_format: str,
        jpeg_quality: int,
        full_page: bool,
        vp: dict[str, int],
    ) -> dict:
        return await self._shoot_generic(
            target=page,
            output_dir=output_dir,
            job_id=job_id,
            viewport_label=viewport_label,
            scheme=scheme,
            output_format=output_format,
            jpeg_quality=jpeg_quality,
            extra_kwargs={"full_page": full_page},
            vp=vp,
            element_index=None,
        )

    async def _shoot_element(
        self,
        element: Any,
        output_dir: Path,
        job_id: str,
        viewport_label: str,
        scheme: str,
        output_format: str,
        jpeg_quality: int,
        vp: dict[str, int],
        element_index: int | None,
    ) -> dict:
        return await self._shoot_generic(
            target=element,
            output_dir=output_dir,
            job_id=job_id,
            viewport_label=viewport_label,
            scheme=scheme,
            output_format=output_format,
            jpeg_quality=jpeg_quality,
            extra_kwargs={},
            vp=vp,
            element_index=element_index,
        )

    async def _shoot_generic(
        self,
        target: Any,
        output_dir: Path,
        job_id: str,
        viewport_label: str,
        scheme: str,
        output_format: str,
        jpeg_quality: int,
        extra_kwargs: dict,
        vp: dict[str, int],
        element_index: int | None,
    ) -> dict:
        is_webp = output_format == "webp"
        # Playwright only supports png + jpeg natively. WebP goes via Pillow.
        native_fmt = "jpeg" if output_format == "jpeg" else "png"
        fname_fmt = output_format  # final filename extension

        fname = self._build_filename(job_id, viewport_label, scheme, fname_fmt, element_index)
        fpath = output_dir / fname

        if is_webp:
            tmp_png = fpath.with_suffix(".tmp.png")
            await target.screenshot(path=str(tmp_png), type="png", **extra_kwargs)
            try:
                from PIL import Image  # type: ignore
            except ImportError as exc:
                tmp_png.unlink(missing_ok=True)
                raise RuntimeError(
                    "Format WebP butuh Pillow. Jalankan: pip install pillow"
                ) from exc
            try:
                with Image.open(tmp_png) as im:
                    im.save(str(fpath), "WEBP", quality=int(jpeg_quality))
            finally:
                tmp_png.unlink(missing_ok=True)
        else:
            kwargs: dict[str, Any] = {"path": str(fpath), "type": native_fmt, **extra_kwargs}
            if native_fmt == "jpeg":
                kwargs["quality"] = int(jpeg_quality)
            await target.screenshot(**kwargs)

        size = fpath.stat().st_size
        return self._pack_result(
            fpath, job_id, fname, vp, viewport_label, scheme, output_format, size, element_index
        )

    def _pack_result(
        self,
        fpath: Path,
        job_id: str,
        fname: str,
        vp: dict[str, int],
        viewport_label: str,
        scheme: str,
        output_format: str,
        size: int,
        element_index: int | None,
    ) -> dict:
        dims = _read_png_dims(fpath) or {"width": vp["width"], "height": vp["height"]}
        return {
            "file_path": str(fpath),
            "file_url": f"/api/screenshot/file/{job_id}/{fname}",
            "file_size_bytes": size,
            "dimensions": dims,
            "viewport_used": viewport_label,
            "color_scheme_used": scheme,
            "format": output_format,
            "element_index": element_index,
        }

    async def _launch_browser(self) -> tuple[Any, Any]:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            logger.error("Playwright import failed: %s", exc)
            raise RuntimeError(_INSTALL_HINT) from exc
        from app.services.playwright_stealth_helper import stealth_launch_args
        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.launch(headless=True, args=stealth_launch_args())
        except Exception as exc:
            msg = str(exc).lower()
            if (
                "executable doesn't exist" in msg
                or "browsertype.launch" in msg
                or "playwright install" in msg
            ):
                await pw.stop()
                raise RuntimeError(_INSTALL_HINT) from exc
            await pw.stop()
            raise
        return pw, browser

    async def capture(
        self,
        url: str,
        output_dir: Path,
        job_id: str,
        viewports: list[str],
        custom_width: int | None = None,
        custom_height: int | None = None,
        full_page: bool = True,
        color_scheme: str = "light",
        device_scale: float = 1.0,
        output_format: str = "png",
        jpeg_quality: int = 85,
        element_selector: str | None = None,
        multiple_elements: bool = False,
        hide_selectors: list[str] | None = None,
        wait_for_selector: str | None = None,
        wait_until: str = "networkidle",
        scroll_through: bool = False,
        timeout_ms: int = 30000,
        custom_css: str | None = None,
        watermark_text: str | None = None,
        watermark_position: str = "bottom-right",
        watermark_opacity: float = 0.5,
        use_auth_vault: bool = False,
    ) -> dict[str, Any]:
        """Capture screenshots. Returns {captures: [...], final_url, title, status}."""
        if not viewports:
            raise ValueError("viewports tidak boleh kosong")
        output_dir.mkdir(parents=True, exist_ok=True)
        ua = UARotator(mode=settings_store.get("ua_mode", "random")).get_headers().get("User-Agent")

        schemes = ["light", "dark"] if color_scheme == "both" else [color_scheme]

        pw, browser = await self._launch_browser()
        try:
            all_captures: list[dict] = []
            meta: dict[str, Any] = {"final_url": url, "title": "", "status": 0}
            for vp_key in viewports:
                for scheme in schemes:
                    caps, m = await self._capture_one_combo(
                        browser=browser,
                        url=url,
                        output_dir=output_dir,
                        job_id=job_id,
                        viewport_key=vp_key,
                        custom_width=custom_width,
                        custom_height=custom_height,
                        full_page=full_page,
                        scheme=scheme,
                        device_scale=device_scale,
                        output_format=output_format,
                        jpeg_quality=jpeg_quality,
                        element_selector=element_selector,
                        multiple_elements=multiple_elements,
                        hide_selectors=hide_selectors,
                        wait_for_selector=wait_for_selector,
                        wait_until=wait_until,
                        scroll_through=scroll_through,
                        timeout_ms=timeout_ms,
                        custom_css=custom_css,
                        watermark_text=watermark_text,
                        watermark_position=watermark_position,
                        watermark_opacity=watermark_opacity,
                        use_auth_vault=use_auth_vault,
                        ua=ua,
                    )
                    all_captures.extend(caps)
                    meta = m
            return {"captures": all_captures, **meta}
        finally:
            try:
                await browser.close()
            except Exception as exc:
                logger.warning("Error closing browser: %s", exc)
            try:
                await pw.stop()
            except Exception as exc:
                logger.warning("Error stopping playwright: %s", exc)

    async def capture_batch(
        self,
        urls: list[str],
        output_dir: Path,
        job_id: str,
        concurrency: int = 3,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Capture multiple URLs sharing a single browser. Returns per-url results."""
        output_dir.mkdir(parents=True, exist_ok=True)
        ua = UARotator(mode=settings_store.get("ua_mode", "random")).get_headers().get("User-Agent")

        viewports: list[str] = kwargs.pop("viewports", ["desktop"])
        color_scheme: str = kwargs.pop("color_scheme", "light")
        schemes = ["light", "dark"] if color_scheme == "both" else [color_scheme]

        pw, browser = await self._launch_browser()
        sem = asyncio.Semaphore(max(1, int(concurrency)))

        async def _one_url(u: str, idx: int) -> dict[str, Any]:
            async with sem:
                per_job = f"{job_id}_{idx}"
                try:
                    all_caps: list[dict] = []
                    meta: dict[str, Any] = {"final_url": u, "title": "", "status": 0}
                    for vp_key in viewports:
                        for scheme in schemes:
                            caps, m = await self._capture_one_combo(
                                browser=browser,
                                url=u,
                                output_dir=output_dir,
                                job_id=per_job,
                                viewport_key=vp_key,
                                custom_width=kwargs.get("custom_width"),
                                custom_height=kwargs.get("custom_height"),
                                full_page=kwargs.get("full_page", True),
                                scheme=scheme,
                                device_scale=kwargs.get("device_scale", 1.0),
                                output_format=kwargs.get("output_format", "png"),
                                jpeg_quality=kwargs.get("jpeg_quality", 85),
                                element_selector=kwargs.get("element_selector"),
                                multiple_elements=kwargs.get("multiple_elements", False),
                                hide_selectors=kwargs.get("hide_selectors"),
                                wait_for_selector=kwargs.get("wait_for_selector"),
                                wait_until=kwargs.get("wait_until", "networkidle"),
                                scroll_through=kwargs.get("scroll_through", False),
                                timeout_ms=kwargs.get("timeout_ms", 30000),
                                custom_css=kwargs.get("custom_css"),
                                watermark_text=kwargs.get("watermark_text"),
                                watermark_position=kwargs.get("watermark_position", "bottom-right"),
                                watermark_opacity=kwargs.get("watermark_opacity", 0.5),
                                use_auth_vault=kwargs.get("use_auth_vault", False),
                                ua=ua,
                            )
                            all_caps.extend(caps)
                            meta = m
                    return {"url": u, "captures": all_caps, **meta, "error": None}
                except Exception as exc:
                    logger.exception("Batch capture gagal untuk %s: %s", u, exc)
                    return {
                        "url": u,
                        "captures": [],
                        "final_url": u,
                        "status": 0,
                        "title": "",
                        "error": str(exc) or exc.__class__.__name__,
                    }

        try:
            results = await asyncio.gather(
                *[_one_url(u, i) for i, u in enumerate(urls)]
            )
            return list(results)
        finally:
            try:
                await browser.close()
            except Exception as exc:
                logger.warning("Error closing browser: %s", exc)
            try:
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
