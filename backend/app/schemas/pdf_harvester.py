"""Pydantic schemas for PDF Harvester."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PdfHarvestRequest(BaseModel):
    url: str
    max_depth: int = Field(default=2, ge=0, le=4)
    max_pages: int = Field(default=50, ge=1, le=500)
    max_pdfs: int = Field(default=100, ge=1, le=500)
    download: bool = True
    extract_text: bool = True


class PdfDocument(BaseModel):
    pdf_id: str
    url: str
    filename: str
    discovered_from: Optional[str] = None
    downloaded: bool = False
    local_path: Optional[str] = None
    file_size: int = 0
    page_count: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None
    preview_text: Optional[str] = None
    text_content: Optional[str] = None
    error: Optional[str] = None


class PdfHarvestReport(BaseModel):
    job_id: str
    url: str
    started_at: str
    finished_at: Optional[str] = None
    pages_crawled: int = 0
    pdfs_found: int = 0
    pdfs_downloaded: int = 0
    total_size: int = 0
    documents: list[PdfDocument] = []
    stats: dict = {}
