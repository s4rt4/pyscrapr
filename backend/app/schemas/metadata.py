"""Pydantic schemas for the Metadata Inspector."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MetadataInspectRequest(BaseModel):
    path: str = Field(..., description="Absolute path to a local file")


class MetadataCategory(BaseModel):
    name: str
    fields: dict[str, Any]


class MetadataInspectResponse(BaseModel):
    file_type: str
    size_bytes: int
    modified_at: Optional[str] = None
    categories: dict[str, Optional[dict[str, Any]]]
