"""Media Downloader orchestrator (Phase 4) — thin wrapper around yt-dlp.

Responsibilities:
  - Translate MediaStartRequest → yt-dlp options
  - Supply an ffmpeg path via imageio-ffmpeg
  - Stream progress to SSE event bus
  - Persist Asset rows per downloaded file
  - Save everything under downloads/<domain>/<date>_media/
"""
import asyncio
import os
from pathlib import Path
from typing import Any, Optional

import imageio_ffmpeg
import yt_dlp

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.job import JobStatus
from app.repositories.asset_repository import AssetRepository
from app.repositories.job_repository import JobRepository
from app.schemas.media import MediaStartRequest
from app.services.event_bus import event_bus
from app.utils.path_helper import domain_folder
from app.utils.url_helper import extract_domain


def _quality_format(quality: str, format: str) -> str:
    """Build a yt-dlp --format string from our presets."""
    if quality == "audio" or format in ("mp3", "m4a", "flac", "opus"):
        return "bestaudio/best"
    height_map = {"4k": 2160, "1080p": 1080, "720p": 720, "480p": 480}
    if quality == "best":
        return f"bestvideo[ext={format}]+bestaudio/bestvideo+bestaudio/best"
    h = height_map.get(quality, 1080)
    return (
        f"bestvideo[height<={h}][ext={format}]+bestaudio/"
        f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
    )


class MediaDownloaderService:
    async def run(
        self,
        job_id: str,
        stop_event: asyncio.Event,
        req: MediaStartRequest,
    ) -> None:
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            asset_repo = AssetRepository(session)
            await job_repo.update_status(job_id, JobStatus.RUNNING)
            await session.commit()
            await event_bus.publish(job_id, {"type": "status", "status": "running"})

            try:
                url_str = str(req.url)
                domain = extract_domain(url_str)
                out_dir = domain_folder(settings.download_dir, domain, "media").parent / "files"
                out_dir.mkdir(parents=True, exist_ok=True)

                stats = {
                    "total_items": 0,
                    "downloaded": 0,
                    "failed": 0,
                    "bytes_total": 0,
                    "current_speed": 0.0,
                    "current_eta": None,
                    "current_filename": None,
                    "current_percent": 0.0,
                }
                saved_files: list[tuple[str, Path, int]] = []  # (title, path, size)

                loop = asyncio.get_running_loop()

                def progress_hook(d: dict[str, Any]) -> None:
                    if stop_event.is_set():
                        raise yt_dlp.utils.DownloadError("cancelled")
                    status = d.get("status")
                    if status == "downloading":
                        stats["current_filename"] = os.path.basename(d.get("filename") or "")
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        downloaded = d.get("downloaded_bytes") or 0
                        stats["current_percent"] = (downloaded / total * 100.0) if total else 0.0
                        stats["current_speed"] = d.get("speed") or 0.0
                        stats["current_eta"] = d.get("eta")
                        asyncio.run_coroutine_threadsafe(
                            event_bus.publish(job_id, {
                                "type": "progress",
                                "stats": dict(stats),
                            }),
                            loop,
                        )
                    elif status == "finished":
                        filename = d.get("filename")
                        size = d.get("total_bytes") or d.get("downloaded_bytes") or 0
                        info = d.get("info_dict") or {}
                        title = info.get("title") or (Path(filename).stem if filename else "")
                        thumb = info.get("thumbnail")
                        duration = info.get("duration")
                        if filename:
                            saved_files.append((title, Path(filename), int(size)))
                        stats["downloaded"] += 1
                        stats["bytes_total"] += int(size)
                        asyncio.run_coroutine_threadsafe(
                            event_bus.publish(job_id, {
                                "type": "item_done",
                                "filename": os.path.basename(filename or ""),
                                "title": title,
                                "thumbnail": thumb,
                                "duration": duration,
                                "size": int(size),
                                "stats": dict(stats),
                            }),
                            loop,
                        )

                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

                ydl_opts: dict[str, Any] = {
                    "quiet": True,
                    "no_warnings": True,
                    "outtmpl": str(out_dir / "%(title).120B [%(id)s].%(ext)s"),
                    "format": _quality_format(req.quality, req.format),
                    "ffmpeg_location": ffmpeg_path,
                    "progress_hooks": [progress_hook],
                    "socket_timeout": 30,
                    "retries": 5,
                    "noplaylist": False,
                    "ignoreerrors": True,
                    "writethumbnail": req.embed_thumbnail,
                    "writesubtitles": req.subtitles in ("download", "embed"),
                    "subtitleslangs": req.subtitle_langs or ["en"],
                }

                # Post-processors
                postprocessors: list[dict[str, Any]] = []
                if req.quality == "audio" or req.format in ("mp3", "m4a", "flac", "opus"):
                    postprocessors.append(
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": req.format if req.format in ("mp3", "m4a", "flac", "opus") else "mp3",
                            "preferredquality": "192",
                        }
                    )
                elif req.format in ("mp4", "webm", "mkv"):
                    postprocessors.append(
                        {"key": "FFmpegVideoRemuxer", "preferedformat": req.format}
                    )
                if req.embed_thumbnail:
                    postprocessors.append({"key": "EmbedThumbnail"})
                if req.embed_metadata:
                    postprocessors.append({"key": "FFmpegMetadata"})
                if req.subtitles == "embed":
                    postprocessors.append({"key": "FFmpegEmbedSubtitle"})
                ydl_opts["postprocessors"] = postprocessors

                # Cookies from browser
                if req.use_browser_cookies:
                    ydl_opts["cookiesfrombrowser"] = (req.use_browser_cookies,)

                # Playlist range
                if req.playlist_start is not None:
                    ydl_opts["playliststart"] = req.playlist_start
                if req.playlist_end is not None:
                    ydl_opts["playlistend"] = req.playlist_end
                if req.max_items is not None:
                    ydl_opts["playlist_items"] = f"1-{req.max_items}"

                await event_bus.publish(
                    job_id,
                    {"type": "log", "message": f"Using ffmpeg at {ffmpeg_path}"},
                )

                def run_sync() -> int:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.download([url_str])

                try:
                    rc = await asyncio.to_thread(run_sync)
                except yt_dlp.utils.DownloadError as e:
                    if "cancelled" in str(e):
                        rc = -1
                    else:
                        raise

                # Persist per-file Assets
                for title, path, size in saved_files:
                    asset = Asset(
                        job_id=job_id,
                        url=url_str,
                        kind=AssetKind.OTHER,
                        status=AssetStatus.DONE,
                        local_path=str(path),
                        size_bytes=size,
                        alt_text=title,
                    )
                    await asset_repo.create(asset)

                stats["total_items"] = len(saved_files)
                await job_repo.update_stats(job_id, stats)
                job = await job_repo.find_by_id(job_id)
                if job:
                    job.output_dir = str(out_dir)

                if stop_event.is_set() or rc == -1:
                    await job_repo.update_status(job_id, JobStatus.STOPPED)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "stopped", "stats": stats})
                else:
                    await job_repo.update_status(job_id, JobStatus.DONE)
                    await session.commit()
                    await event_bus.publish(job_id, {"type": "done", "stats": stats})

            except Exception as e:
                try:
                    await session.rollback()
                except Exception:
                    pass
                async with AsyncSessionLocal() as err_session:
                    err_repo = JobRepository(err_session)
                    await err_repo.update_status(job_id, JobStatus.ERROR, str(e))
                    await err_session.commit()
                await event_bus.publish(job_id, {"type": "error", "message": str(e)})


media_downloader_service = MediaDownloaderService()
