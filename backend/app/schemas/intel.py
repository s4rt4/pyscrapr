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


class DomainIntelResponse(BaseModel):
    domain: str
    whois: dict[str, Any]
    dns: dict[str, list[str]]
    subdomains: list[str]
    subdomain_count: int
    fetched_at: str
