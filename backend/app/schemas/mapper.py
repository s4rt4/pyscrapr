"""Pydantic schemas for URL Mapper (Phase 2)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class MapperStartRequest(BaseModel):
    url: HttpUrl
    max_depth: int = Field(default=2, ge=1, le=5)
    max_pages: int = Field(default=500, ge=1, le=20000)
    stay_on_domain: bool = True
    respect_robots: bool = True
    rate_limit_per_host: float = Field(default=1.0, ge=0.1, le=20.0, description="requests per second")
    concurrency: int = Field(default=4, ge=1, le=16)
    exclude_patterns: list[str] = Field(default_factory=list)
    strip_tracking_params: bool = True


class CrawlNodeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    url: str
    parent_id: Optional[int] = None
    depth: int
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None
    word_count: Optional[int] = None
    response_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime


class SitemapTreeNode(BaseModel):
    id: int
    url: str
    depth: int
    status_code: Optional[int] = None
    title: Optional[str] = None
    children: list["SitemapTreeNode"] = Field(default_factory=list)


class SitemapGraphNode(BaseModel):
    id: int
    url: str
    depth: int
    status_code: Optional[int] = None
    title: Optional[str] = None


class SitemapGraphEdge(BaseModel):
    source: int
    target: int


class SitemapGraphResponse(BaseModel):
    nodes: list[SitemapGraphNode]
    edges: list[SitemapGraphEdge]


class MapperStatsDTO(BaseModel):
    discovered: int = 0
    crawled: int = 0
    broken: int = 0
    redirected: int = 0
    external_skipped: int = 0
    avg_response_ms: int = 0
    frontier_size: int = 0
