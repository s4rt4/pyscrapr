"""Pydantic schemas for OSINT Harvester (Phase 9)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OSINTRequest(BaseModel):
    url: str
    max_depth: int = Field(default=0, ge=0, le=3)
    max_pages: int = Field(default=50, ge=1, le=500)
    stay_on_domain: bool = True
    filters: Optional[dict[str, bool]] = None
    custom_patterns: list[str] = []


class OSINTFinding(BaseModel):
    category: str
    subcategory: Optional[str] = None
    value: str
    source_url: str
    context_snippet: Optional[str] = None


class OSINTReport(BaseModel):
    job_id: str
    url: str
    started_at: str
    finished_at: Optional[str] = None
    pages_crawled: int = 0
    findings: list[OSINTFinding] = []
    stats: dict[str, int] = {}
