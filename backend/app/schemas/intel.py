"""Schemas for domain intelligence endpoints."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DomainRequest(BaseModel):
    domain: str


class DNSRequest(BaseModel):
    domain: str
    record_types: Optional[list[str]] = None


class WhoisData(BaseModel):
    registered: Optional[bool] = None
    domain: Optional[str] = None
    registrar: Optional[str] = None
    registration_date: Optional[str] = None
    expiration_date: Optional[str] = None
    last_updated: Optional[str] = None
    nameservers: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    registrant_country: Optional[str] = None
    error: Optional[str] = None


class SpfRecord(BaseModel):
    found: bool = False
    raw: Optional[str] = None
    policy: str = "unknown"
    all_directive: Optional[str] = None
    includes: list[str] = Field(default_factory=list)
    mechanisms: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DmarcRecord(BaseModel):
    found: bool = False
    raw: Optional[str] = None
    policy: Optional[str] = None
    subdomain_policy: Optional[str] = None
    pct: Optional[int] = None
    rua: list[str] = Field(default_factory=list)
    ruf: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DkimRecord(BaseModel):
    selectors_checked: list[str] = Field(default_factory=list)
    selectors_found: list[str] = Field(default_factory=list)


class EmailSecurityRecord(BaseModel):
    spf: SpfRecord
    dmarc: DmarcRecord
    dkim: DkimRecord
    grade: str = "F"


class DomainIntelResponse(BaseModel):
    domain: str
    whois: dict[str, Any]
    dns: dict[str, list[str]]
    subdomains: list[str]
    subdomain_count: int
    fetched_at: str
    email_security: Optional[EmailSecurityRecord] = None
