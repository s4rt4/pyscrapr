"""Schemas for the API Sniffer (P12)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SniffRequest(BaseModel):
    url: str
    wait_seconds: int = Field(default=15, ge=5, le=60)
    max_requests: int = Field(default=200, ge=10, le=1000)
    filter_static: bool = True
    use_stealth: bool = True


class CapturedRequest(BaseModel):
    """A single HTTP transaction captured by Playwright."""
    request_id: str
    method: str
    url: str
    full_url: str
    host: str
    path: str
    resource_type: str | None = None
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str | None = None
    request_body_json: Any | None = None
    status: int | None = None
    response_content_type: str | None = None
    response_body: str | None = None
    response_body_json: Any | None = None
    response_size_bytes: int = 0
    started_at: float
    duration_ms: float | None = None
    is_graphql: bool = False
    graphql_operation: str | None = None


class ApiEndpoint(BaseModel):
    """A grouped endpoint summary (host + method + path)."""
    host: str
    method: str
    path: str
    count: int
    statuses: dict[str, int] = Field(default_factory=dict)
    content_types: dict[str, int] = Field(default_factory=dict)
    sample_request: CapturedRequest
    is_graphql: bool = False


class GraphQLOp(BaseModel):
    operation_name: str
    operation_type: str | None = None
    query: str | None = None
    variables: Any | None = None
    response_sample: Any | None = None
    count: int
    host: str
    path: str


class SniffStats(BaseModel):
    total_requests: int
    unique_endpoints: int
    graphql_ops: int
    content_type_breakdown: dict[str, int] = Field(default_factory=dict)
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    total_response_bytes: int


class SniffReport(BaseModel):
    url: str
    final_url: str
    started_at: str
    finished_at: str
    duration_seconds: float
    stats: SniffStats
    endpoints: list[ApiEndpoint] = Field(default_factory=list)
    graphql_ops: list[GraphQLOp] = Field(default_factory=list)
    requests: list[CapturedRequest] = Field(default_factory=list)


class SniffResponse(BaseModel):
    job_id: str
    status: str
    report: SniffReport | None = None
    error_message: str | None = None
