"""Pydantic schemas for Site Ripper (Phase 3)."""
from pydantic import BaseModel, Field, HttpUrl


class RipperStartRequest(BaseModel):
    url: HttpUrl
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=50, ge=1, le=5000)
    max_assets: int = Field(default=3000, ge=1, le=50000)
    stay_on_domain: bool = True
    respect_robots: bool = True
    rate_limit_per_host: float = Field(default=4.0, ge=0.1, le=20.0)
    concurrency: int = Field(default=6, ge=1, le=32)
    include_external_assets: bool = Field(
        default=True,
        description="Download cross-origin assets like CDN-hosted CSS/JS/fonts.",
    )
    rewrite_links: bool = True
    generate_report: bool = True
    use_playwright: bool = False


class RipperStatsDTO(BaseModel):
    pages: int = 0
    assets: int = 0
    bytes_total: int = 0
    broken: int = 0
    failed: int = 0
    by_kind: dict[str, dict] = Field(default_factory=dict)
