"""Schemas for Exposure Scanner."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ExposureScanRequest(BaseModel):
    url: str
    throttle_seconds: float = 1.0


class ExposureFinding(BaseModel):
    path: str
    category: str
    severity: str
    status: int
    content_preview: str | None = None
    plausible: bool


class ExposureScanResponse(BaseModel):
    base_url: str
    scanned_at: str
    total_checked: int
    total_found: int
    findings: list[ExposureFinding] = Field(default_factory=list)
    error: str | None = None
