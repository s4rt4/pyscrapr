"""Schemas for the Screenshot Generator tool."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class WatermarkPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"


class ColorSchemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    BOTH = "both"


class OutputFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    PDF = "pdf"


class ScreenshotDimensions(BaseModel):
    width: int
    height: int


class ScreenshotRequest(BaseModel):
    url: str = ""
    # Accept either viewports (list) or legacy viewport (string) for backward compat.
    viewports: list[str] = Field(default_factory=lambda: ["desktop"])
    viewport: str | None = None  # legacy; merged into viewports in validator
    custom_width: int | None = None
    custom_height: int | None = None
    full_page: bool = True
    # Legacy boolean kept for backward compat; prefer color_scheme.
    dark_mode: bool | None = None
    color_scheme: ColorSchemeMode = ColorSchemeMode.LIGHT
    device_scale: float = 1.0
    output_format: OutputFormat = OutputFormat.PNG
    jpeg_quality: int = 85
    element_selector: str | None = None
    multiple_elements: bool = False
    hide_selectors: list[str] | None = None
    wait_for_selector: str | None = None
    wait_until: str = Field(default="networkidle", description="load | domcontentloaded | networkidle")
    scroll_through: bool = False
    timeout_ms: int = 30000
    custom_css: str | None = None
    watermark_text: str | None = None
    watermark_position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    watermark_opacity: float = 0.5
    use_auth_vault: bool = False

    @model_validator(mode="after")
    def _merge_legacy(self) -> "ScreenshotRequest":
        # Fold legacy `viewport` into `viewports` if user sent old shape.
        if self.viewport and (not self.viewports or self.viewports == ["desktop"]):
            self.viewports = [self.viewport]
        # Fold legacy `dark_mode` bool into color_scheme if user didn't set color_scheme.
        if self.dark_mode is True and self.color_scheme == ColorSchemeMode.LIGHT:
            self.color_scheme = ColorSchemeMode.DARK
        return self


class CaptureResult(BaseModel):
    file_path: str
    file_url: str
    file_size_bytes: int
    dimensions: ScreenshotDimensions
    viewport_used: str
    color_scheme_used: str
    format: str
    element_index: int | None = None


class ScreenshotResponse(BaseModel):
    job_id: str
    url: str
    final_url: str
    title: str
    status: int
    captures: list[CaptureResult]
    duration_ms: int


class BatchScreenshotRequest(ScreenshotRequest):
    urls: list[str] = Field(default_factory=list)


class BatchResult(BaseModel):
    url: str
    captures: list[CaptureResult]
    final_url: str
    status: int
    error: str | None = None


class BatchScreenshotResponse(BaseModel):
    job_id: str
    total_urls: int
    ok_count: int
    error_count: int
    results: list[BatchResult]
    duration_ms: int


class ViewportSpec(BaseModel):
    key: str
    label: str
    width: int | None = None
    height: int | None = None
    custom: bool = False


class ViewportsResponse(BaseModel):
    viewports: list[ViewportSpec]


# ---------------------------------------------------------------------------
# Gallery / Compare / Video / Export schemas (added by advanced features agent)
# ---------------------------------------------------------------------------


class GalleryFile(BaseModel):
    filename: str
    url: str
    size_bytes: int
    viewport: str | None = None
    format: str = "png"


class GalleryItem(BaseModel):
    job_id: str
    url: str
    created_at: str
    stats: dict = Field(default_factory=dict)
    files: list[GalleryFile] = Field(default_factory=list)


class GalleryResponse(BaseModel):
    total: int
    items: list[GalleryItem]


class CompareMode(str, Enum):
    SIDE_BY_SIDE = "side_by_side"
    OVERLAY = "overlay"


class CompareRequest(BaseModel):
    job_id_a: str
    filename_a: str
    job_id_b: str
    filename_b: str
    mode: CompareMode = CompareMode.SIDE_BY_SIDE
    threshold: int = 10


class CompareStats(BaseModel):
    width: int
    height: int
    total_pixels: int
    different_pixels: int
    diff_ratio: float
    bbox: list[int] | None = None


class CompareFileRef(BaseModel):
    job_id: str
    filename: str


class CompareResponse(BaseModel):
    comparison_id: str
    diff_image_url: str
    mode: str
    stats: CompareStats
    file_a: CompareFileRef
    file_b: CompareFileRef


class VideoFormat(str, Enum):
    MP4 = "mp4"
    GIF = "gif"
    WEBM = "webm"


class VideoRequest(BaseModel):
    url: str
    viewport: str = "desktop"
    custom_width: int | None = None
    custom_height: int | None = None
    scroll_duration_ms: int = 4000
    fps: int = 24
    output_format: VideoFormat = VideoFormat.MP4
    wait_until: str = "networkidle"
    timeout_ms: int = 30000
    use_auth_vault: bool = False


class VideoResponse(BaseModel):
    job_id: str
    file_url: str
    file_path: str
    file_size_bytes: int
    duration_ms: int
    output_format: str
    viewport_used: str
    final_url: str
    title: str
    status: int


class ZipExportRequest(BaseModel):
    job_ids: list[str] = Field(default_factory=list)
