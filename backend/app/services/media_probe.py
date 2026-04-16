"""Probe a media URL using yt-dlp without actually downloading.

Returns metadata needed to preview what a download would produce
(playlist entries, title, duration, thumbnail, uploader).
"""
import asyncio
from typing import Any, Optional

import yt_dlp

from app.schemas.media import MediaProbeResponse, ProbeEntry


def _build_opts(cookies_from_browser: Optional[str]) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",  # quick playlist list, no per-entry fetch
        "socket_timeout": 15,
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    return opts


def _classify(info: dict[str, Any]) -> str:
    t = info.get("_type") or "video"
    if t == "playlist":
        # YouTube channels show up as playlist too — distinguish via extractor
        extractor = (info.get("extractor") or "").lower()
        if "channel" in extractor or info.get("uploader_url"):
            return "channel"
        return "playlist"
    return "video"


def _probe_sync(url: str, cookies_from_browser: Optional[str]) -> MediaProbeResponse:
    opts = _build_opts(cookies_from_browser)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if info is None:
        raise RuntimeError("yt-dlp returned no info")

    kind = _classify(info)
    extractor = info.get("extractor_key") or info.get("extractor") or "unknown"

    if kind in ("playlist", "channel"):
        raw_entries = info.get("entries") or []
        entries = [
            ProbeEntry(
                id=str(e.get("id") or i),
                title=str(e.get("title") or e.get("url") or f"item {i}"),
                url=e.get("url") or e.get("webpage_url"),
                duration=e.get("duration"),
                uploader=e.get("uploader"),
                thumbnail=e.get("thumbnail"),
            )
            for i, e in enumerate(raw_entries)
            if e is not None
        ]
        return MediaProbeResponse(
            kind=kind,  # type: ignore[arg-type]
            extractor=extractor,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            total=len(entries),
            entries=entries[:500],  # cap preview size
            thumbnail=info.get("thumbnail"),
            webpage_url=info.get("webpage_url"),
        )

    return MediaProbeResponse(
        kind="video",
        extractor=extractor,
        title=info.get("title"),
        uploader=info.get("uploader") or info.get("channel"),
        total=1,
        entries=[
            ProbeEntry(
                id=str(info.get("id") or "0"),
                title=str(info.get("title") or ""),
                url=info.get("webpage_url"),
                duration=info.get("duration"),
                uploader=info.get("uploader"),
                thumbnail=info.get("thumbnail"),
            )
        ],
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        webpage_url=info.get("webpage_url"),
    )


async def probe(url: str, cookies_from_browser: Optional[str] = None) -> MediaProbeResponse:
    """Run yt-dlp probe in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(_probe_sync, url, cookies_from_browser)
