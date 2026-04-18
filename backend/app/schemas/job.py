"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.job import JobStatus, JobType


class ImageFilterConfig(BaseModel):
    """Filter rules for Image Harvester."""
    allowed_types: list[str] = Field(default_factory=lambda: ["jpg", "jpeg", "png", "webp", "gif", "svg"])
    min_width: int = 100
    min_height: int = 100
    min_bytes: int = 5120
    exclude_patterns: list[str] = Field(default_factory=list)


class HarvesterStartRequest(BaseModel):
    url: HttpUrl
    filters: ImageFilterConfig = Field(default_factory=ImageFilterConfig)
    concurrency: int = Field(default=8, ge=1, le=32)
    include_background_css: bool = False
    deduplicate: bool = True
    use_playwright: bool = False


class JobStatsDTO(BaseModel):
    discovered: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    bytes_total: int = 0


class JobDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: JobType
    url: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    stats: dict
    output_dir: Optional[str] = None
    error_message: Optional[str] = None


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus


class AssetDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    url: str
    status: str
    local_path: Optional[str] = None
    size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
