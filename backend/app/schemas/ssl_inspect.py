"""Schemas for SSL certificate inspector."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SslInspectRequest(BaseModel):
    hostname: str
    port: int = 443
    timeout: int = 15


class SslIssue(BaseModel):
    severity: str
    message: str


class SslCipher(BaseModel):
    name: str | None = None
    protocol: str | None = None
    bits: int | None = None


class SslInspectResponse(BaseModel):
    hostname: str
    port: int
    fetched_at: str
    subject: dict[str, str] = Field(default_factory=dict)
    issuer: dict[str, str] = Field(default_factory=dict)
    valid_from: str | None = None
    valid_to: str | None = None
    valid_from_iso: str | None = None
    valid_to_iso: str | None = None
    serial_number: str | None = None
    version: int | None = None
    san: list[str] = Field(default_factory=list)
    days_until_expiry: int | None = None
    is_expired: bool = False
    is_self_signed: bool = False
    hostname_match: bool = False
    tls_version: str | None = None
    cipher: SslCipher | None = None
    cert_size_bytes: int = 0
    issues: list[SslIssue] = Field(default_factory=list)
