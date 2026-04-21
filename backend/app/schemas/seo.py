"""Schemas for SEO auditor."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SeoAuditRequest(BaseModel):
    url: str
    timeout: int = 20


class SeoIssue(BaseModel):
    severity: str
    code: str
    message: str


class SeoAuditResponse(BaseModel):
    url: str
    final_url: str
    status_code: int
    fetched_at: str
    score: int
    title: str | None = None
    title_length: int = 0
    description: str | None = None
    description_length: int = 0
    canonical: str | None = None
    robots: str | None = None
    lang: str | None = None
    viewport: str | None = None
    has_favicon: bool = False
    og: dict[str, str] = Field(default_factory=dict)
    twitter: dict[str, str] = Field(default_factory=dict)
    h1: list[str] = Field(default_factory=list)
    h2: list[str] = Field(default_factory=list)
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    img_total: int = 0
    img_without_alt: int = 0
    a_internal: int = 0
    a_external: int = 0
    structured_data: list[str] = Field(default_factory=list)
    word_count: int = 0
    issues: list[SeoIssue] = Field(default_factory=list)
