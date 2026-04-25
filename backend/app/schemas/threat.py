"""Pydantic schemas for ThreatScanner API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ThreatScanRequest(BaseModel):
    path: Optional[str] = None
    depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")


class ThreatFinding(BaseModel):
    category: str
    severity: str
    title: str
    description: str
    score_delta: int


class ThreatScanResponse(BaseModel):
    job_id: str
    file_path: str
    file_size: int
    sha256: str
    detected_type: Optional[str] = None
    claimed_type: str
    type_spoof: bool
    entropy: float
    entropy_class: Optional[str] = None
    findings: list[ThreatFinding]
    risk_score: int
    verdict: str
    scanned_at: str
    scan_duration_ms: int
    skipped: bool = False
    skip_reason: Optional[str] = None
    modules: dict[str, Any] = Field(default_factory=dict)
    ai_explanation: Optional[dict[str, Any]] = None


class FolderScanTopThreat(BaseModel):
    file_path: str
    risk_score: int
    verdict: str


class FolderScanResponse(BaseModel):
    job_id: str
    folder_path: str
    files_total: int
    files_clean: int
    files_suspicious: int
    files_dangerous: int
    top_threats: list[FolderScanTopThreat]
    files: list[ThreatScanResponse]


class QuarantineRequest(BaseModel):
    file_path: str
    reason: str = "manual quarantine"


class QuarantineEntry(BaseModel):
    id: str
    original_path: str
    quarantine_path: str
    sha256: str
    moved_at: int
    reason: str
    scan_report_id: Optional[str] = None


class YaraRuleInfo(BaseModel):
    name: str
    path: str
    namespace: str
    source: str
    tags: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)


class ThreatStats(BaseModel):
    total_scans: int
    clean: int
    suspicious: int
    dangerous: int
