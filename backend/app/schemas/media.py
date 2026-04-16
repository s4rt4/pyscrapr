"""Pydantic schemas for Media Downloader (Phase 4)."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


QualityPreset = Literal[
    "best",
    "4k",
    "1080p",
    "720p",
    "480p",
    "audio",
]

FormatPreset = Literal[
    "mp4",
    "webm",
    "mkv",
    "mp3",
    "m4a",
    "flac",
    "opus",
]

SubtitleMode = Literal[
    "skip",
    "download",
    "embed",
]


class MediaStartRequest(BaseModel):
    url: HttpUrl
    quality: QualityPreset = "1080p"
    format: FormatPreset = "mp4"
    subtitles: SubtitleMode = "skip"
    subtitle_langs: list[str] = Field(default_factory=lambda: ["en", "id"])
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    use_browser_cookies: Optional[Literal["chrome", "firefox", "edge", "brave"]] = None
    # Playlist / channel control
    playlist_start: Optional[int] = Field(default=None, ge=1)
    playlist_end: Optional[int] = Field(default=None, ge=1)
    max_items: Optional[int] = Field(default=None, ge=1, le=10000)


class MediaProbeRequest(BaseModel):
    url: HttpUrl
    use_browser_cookies: Optional[Literal["chrome", "firefox", "edge", "brave"]] = None


class ProbeEntry(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    duration: Optional[float] = None
    uploader: Optional[str] = None
    thumbnail: Optional[str] = None


class MediaProbeResponse(BaseModel):
    kind: Literal["video", "playlist", "channel"]
    extractor: str
    title: Optional[str] = None
    uploader: Optional[str] = None
    total: int
    entries: list[ProbeEntry] = Field(default_factory=list)
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    webpage_url: Optional[str] = None


class MediaStatsDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_items: int = 0
    downloaded: int = 0
    failed: int = 0
    bytes_total: int = 0
    current_speed: float = 0.0  # bytes/sec
    current_eta: Optional[int] = None
    current_filename: Optional[str] = None
    current_percent: float = 0.0
