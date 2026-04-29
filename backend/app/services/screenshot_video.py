"""Screenshot video recording — scroll-through capture via Playwright.

Records a WebM through Playwright's ``record_video_dir`` context option, then
optionally transcodes to MP4 or GIF using the ffmpeg binary shipped with
``imageio-ffmpeg`` (already a dependency).
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.services import settings_store
from app.services.ua_rotator import UARotator

logger = logging.getLogger("pyscrapr.screenshot")

_INSTALL_HINT = (
    "Playwright belum terpasang. Jalankan dua perintah berurutan: "
    "pip install playwright ; lalu: python -m playwright install chromium"
)

_VIEWPORTS: dict[str, dict[str, int]] = {
    "desktop": {"width": 1920, "height": 1080},
    "desktop_hd": {"width": 2560, "height": 1440},
    "laptop": {"width": 1366, "height": 768},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
    "mobile_sm": {"width": 375, "height": 667},
}


def _resolve_viewport(
    viewport: str, custom_width: int | None, custom_height: int | None
) -> tuple[dict[str, int], str]:
    if viewport == "custom":
        if not custom_width or not custom_height:
            raise ValueError("custom viewport membutuhkan custom_width dan custom_height")
        vp = {"width": int(custom_width), "height": int(custom_height)}
        return vp, f"custom {vp['width']}x{vp['height']}"
    if viewport not in _VIEWPORTS:
        raise ValueError(
            f"Viewport tidak dikenal: '{viewport}'. Valid: {list(_VIEWPORTS.keys()) + ['custom']}"
        )
    return dict(_VIEWPORTS[viewport]), viewport


def _ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("imageio-ffmpeg belum terpasang") from exc


async def _run_ffmpeg(args: list[str]) -> None:
    exe = _ffmpeg_path()
    cmd = [exe, "-y", *args]
    logger.info("ffmpeg: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _out, err = await proc.communicate()
    if proc.returncode != 0:
        tail = (err or b"").decode("utf-8", errors="ignore")[-1200:]
        raise RuntimeError(f"ffmpeg gagal (exit {proc.returncode}): {tail}")


class ScreenshotVideo:
    """Record a scroll-through video of a page and transcode as requested."""

    async def record_scroll(
        self,
        url: str,
        job_id: str,
        output_dir: Path,
        viewport: str = "desktop",
        custom_width: int | None = None,
        custom_height: int | None = None,
        scroll_duration_ms: int = 4000,
        fps: int = 24,
        output_format: str = "mp4",
        wait_until: str = "networkidle",
        timeout_ms: int = 30000,
        use_auth_vault: bool = False,
    ) -> dict[str, Any]:
        vp, viewport_used = _resolve_viewport(viewport, custom_width, custom_height)

        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            logger.error("Playwright import failed: %s", exc)
            raise RuntimeError(_INSTALL_HINT) from exc

        output_dir.mkdir(parents=True, exist_ok=True)

        ua = (
            UARotator(mode=settings_store.get("ua_mode", "random"))
            .get_headers()
            .get("User-Agent")
        )

        started = time.monotonic()
        pw = None
        browser = None
        webm_path: Optional[Path] = None
        status = 0
        final_url = url
        title = ""
        try:
            try:
                from app.services.playwright_stealth_helper import stealth_launch_args
                pw = await async_playwright().start()
                browser = await pw.chromium.launch(headless=True, args=stealth_launch_args())
            except Exception as exc:
                msg = str(exc).lower()
                if (
                    "executable doesn't exist" in msg
                    or "browsertype.launch" in msg
                    or "playwright install" in msg
                ):
                    raise RuntimeError(_INSTALL_HINT) from exc
                raise

            context = await browser.new_context(
                viewport=vp,
                user_agent=ua,
                record_video_dir=str(output_dir),
                record_video_size=vp,
            )
            try:
                page = await context.new_page()
                from app.services.playwright_stealth_helper import apply_stealth_to_page
                await apply_stealth_to_page(page)
                resp = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                status = resp.status if resp is not None else 0
                final_url = page.url
                try:
                    title = await page.title()
                except Exception:
                    title = ""

                # Scroll script: linearly from top to bottom over the requested
                # duration, using requestAnimationFrame for smooth motion.
                script = """
                    async (duration) => {
                      const total = document.documentElement.scrollHeight - window.innerHeight;
                      if (total <= 0) { return; }
                      const start = performance.now();
                      await new Promise((resolve) => {
                        const step = (now) => {
                          const t = Math.min(1, (now - start) / duration);
                          window.scrollTo(0, Math.round(total * t));
                          if (t >= 1) { resolve(); } else { requestAnimationFrame(step); }
                        };
                        requestAnimationFrame(step);
                      });
                    }
                """
                try:
                    await page.evaluate(script, scroll_duration_ms)
                except Exception as exc:
                    logger.warning("Scroll script error (non-fatal): %s", exc)

                # Give the video a small tail so the final frame lands cleanly.
                await asyncio.sleep(0.4)

                # Capture the video path BEFORE closing the page.
                video = page.video
                await page.close()
                await context.close()
                if video is not None:
                    src_path = Path(await video.path())
                    webm_path = output_dir / f"video_{job_id}.webm"
                    try:
                        src_path.replace(webm_path)
                    except OSError:
                        # Cross-device move fallback
                        webm_path.write_bytes(src_path.read_bytes())
                        try:
                            src_path.unlink()
                        except OSError:
                            pass
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

        if webm_path is None or not webm_path.exists():
            raise RuntimeError("Video tidak dihasilkan oleh Playwright")

        fmt = output_format.lower()
        final_path = webm_path
        if fmt == "mp4":
            out = output_dir / f"video_{job_id}.mp4"
            await _run_ffmpeg(
                [
                    "-i", str(webm_path),
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    str(out),
                ]
            )
            final_path = out
            try:
                webm_path.unlink()
            except OSError:
                pass
        elif fmt == "gif":
            out = output_dir / f"video_{job_id}.gif"
            gif_fps = min(fps, 15)
            await _run_ffmpeg(
                [
                    "-i", str(webm_path),
                    "-vf", f"fps={gif_fps},scale=720:-1:flags=lanczos",
                    "-loop", "0",
                    str(out),
                ]
            )
            final_path = out
            try:
                webm_path.unlink()
            except OSError:
                pass
        elif fmt == "webm":
            final_path = webm_path
        else:
            raise ValueError(f"Format video tidak didukung: {output_format}")

        duration_ms = int((time.monotonic() - started) * 1000)
        ext = final_path.suffix.lstrip(".")

        return {
            "file_path": str(final_path),
            "file_url": f"/api/screenshot/video/file/{job_id}.{ext}",
            "file_size_bytes": final_path.stat().st_size,
            "duration_ms": duration_ms,
            "output_format": ext,
            "viewport_used": viewport_used,
            "final_url": final_url,
            "title": title,
            "status": status,
        }


    async def trim(
        self,
        source_path: Path,
        output_dir: Path,
        job_id: str,
        start_seconds: float,
        end_seconds: float | None,
        output_format: str,
    ) -> dict[str, Any]:
        """Trim an existing video file using ffmpeg.

        Uses stream copy for WebM (fast, no re-encode). For MP4/GIF the
        trim is applied during the transcode.
        """
        if start_seconds < 0:
            raise ValueError("start_seconds tidak boleh negatif")
        if end_seconds is not None and end_seconds <= start_seconds:
            raise ValueError("end_seconds harus lebih besar dari start_seconds")

        output_dir.mkdir(parents=True, exist_ok=True)
        fmt = output_format.lower()
        ss = f"{start_seconds:.3f}"
        to_args = ["-to", f"{end_seconds:.3f}"] if end_seconds is not None else []

        started = time.monotonic()
        if fmt == "webm":
            out = output_dir / f"video_{job_id}_trim.webm"
            await _run_ffmpeg(
                ["-ss", ss, "-i", str(source_path), *to_args, "-c", "copy", str(out)]
            )
        elif fmt == "mp4":
            out = output_dir / f"video_{job_id}_trim.mp4"
            await _run_ffmpeg(
                [
                    "-ss", ss,
                    "-i", str(source_path),
                    *to_args,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    str(out),
                ]
            )
        elif fmt == "gif":
            out = output_dir / f"video_{job_id}_trim.gif"
            await _run_ffmpeg(
                [
                    "-ss", ss,
                    "-i", str(source_path),
                    *to_args,
                    "-vf", "fps=15,scale=720:-1:flags=lanczos",
                    "-loop", "0",
                    str(out),
                ]
            )
        else:
            raise ValueError(f"Format video tidak didukung: {output_format}")

        duration_ms = int((time.monotonic() - started) * 1000)
        ext = out.suffix.lstrip(".")
        return {
            "file_path": str(out),
            "file_url": f"/api/screenshot/video/file/{job_id}_trim.{ext}",
            "file_size_bytes": out.stat().st_size,
            "duration_ms": duration_ms,
            "output_format": ext,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
        }


_video: Optional[ScreenshotVideo] = None


def get_video() -> ScreenshotVideo:
    global _video
    if _video is None:
        _video = ScreenshotVideo()
    return _video
