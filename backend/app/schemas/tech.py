"""Schemas for the website technology stack detector."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TechScanRequest(BaseModel):
    url: str
    timeout: int = 20
    use_playwright: bool = Field(
        default=False,
        description="Render via Playwright for JS-heavy sites (falls back to httpx if unavailable).",
    )


class TechMatch(BaseModel):
    name: str
    version: str | None = None
    confidence: int
    categories: list[str] = Field(default_factory=list)
    icon: str | None = None
    website: str | None = None
    cpe: str | None = None
    matched_on: list[str] = Field(default_factory=list)


class TechScanResponse(BaseModel):
    url: str
    final_url: str
    status_code: int
    fetched_at: str
    technologies: list[TechMatch]
    by_category: dict[str, list[TechMatch]]


class TechStatsResponse(BaseModel):
    technologies_count: int
    categories_count: int
