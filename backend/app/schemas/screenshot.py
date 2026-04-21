"""Schemas for the Screenshot Generator tool."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScreenshotRequest(BaseModel):
    url: str
    viewport: str = "desktop"
    custom_width: int | None = None
    custom_height: int | None = None
    full_page: bool = True
    dark_mode: bool = False
    wait_until: str = Field(default="networkidle", description="load | domcontentloaded | networkidle")
    timeout_ms: int = 30000


class ScreenshotDimensions(BaseModel):
    width: int
    height: int


class ScreenshotResponse(BaseModel):
    job_id: str
    file_path: str
    file_url: str | None = None
    dimensions: ScreenshotDimensions
    file_size_bytes: int
    viewport_used: str
    dark_mode: bool
    final_url: str
    title: str
    status: int


class ViewportSpec(BaseModel):
    key: str
    label: str
    width: int | None = None
    height: int | None = None
    custom: bool = False


class ViewportsResponse(BaseModel):
    viewports: list[ViewportSpec]
