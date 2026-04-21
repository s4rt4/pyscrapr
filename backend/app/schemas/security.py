"""Schemas for security headers scanner."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityScanRequest(BaseModel):
    url: str
    timeout: int = 20


class SecurityCookie(BaseModel):
    name: str
    httponly: bool = False
    secure: bool = False
    samesite: str | None = None
    path: str = "/"


class SecurityIssue(BaseModel):
    severity: str
    header: str
    message: str


class SecurityScanResponse(BaseModel):
    url: str
    final_url: str
    status_code: int
    fetched_at: str
    score: int
    grade: str
    headers_found: dict[str, str] = Field(default_factory=dict)
    headers_missing: list[str] = Field(default_factory=list)
    all_response_headers: dict[str, str] = Field(default_factory=dict)
    cookies: list[SecurityCookie] = Field(default_factory=list)
    issues: list[SecurityIssue] = Field(default_factory=list)
