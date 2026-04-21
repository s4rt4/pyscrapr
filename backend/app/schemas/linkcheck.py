"""Schemas for broken link checker."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LinkCheckRequest(BaseModel):
    url: str
    max_pages: int = 50
    timeout: int = 10
    stay_on_domain: bool = True


class LinkEntry(BaseModel):
    url: str
    status: int = 0
    ok: bool = False
    latency_ms: int = 0
    redirect_chain: list[str] = Field(default_factory=list)
    reason: str = ""
    source_page: str = ""


class LinkCheckResponse(BaseModel):
    url: str
    fetched_at: str
    elapsed_sec: float
    total_pages: int
    total_links: int
    unique_links: int
    ok_count: int
    broken_count: int
    redirect_count: int
    by_status: dict[str, int] = Field(default_factory=dict)
    broken_list: list[LinkEntry] = Field(default_factory=list)
    all_links: list[LinkEntry] = Field(default_factory=list)
