"""Pydantic schemas for Price Watcher."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PriceProductInput(BaseModel):
    url: str
    title: str = ""
    selector: str = ""
    selector_type: str = Field(default="auto", pattern="^(auto|css|xpath)$")
    interval_minutes: int = Field(default=60, ge=5, le=10080)
    enabled: bool = True
    alert_below: Optional[float] = None
    alert_above: Optional[float] = None
    currency: str = "IDR"


class PriceProductUpdate(BaseModel):
    title: Optional[str] = None
    selector: Optional[str] = None
    selector_type: Optional[str] = Field(default=None, pattern="^(auto|css|xpath)$")
    interval_minutes: Optional[int] = Field(default=None, ge=5, le=10080)
    enabled: Optional[bool] = None
    alert_below: Optional[float] = None
    alert_above: Optional[float] = None
    currency: Optional[str] = None


class PriceProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str
    selector: str
    selector_type: str
    interval_minutes: int
    enabled: bool
    alert_below: Optional[float] = None
    alert_above: Optional[float] = None
    currency: str
    last_checked_at: Optional[datetime] = None
    last_price: Optional[float] = None
    last_status: str
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PriceHistoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: str
    price: float
    status: str
    raw_text: Optional[str] = None
    checked_at: datetime


class PriceExtractPreviewResponse(BaseModel):
    price: Optional[float] = None
    status: str
    raw_text: Optional[str] = None
    error: Optional[str] = None
    matched_on: Optional[str] = None
    title: str = ""


class PriceCheckNowResponse(BaseModel):
    ok: bool
    product_id: str
    price: Optional[float] = None
    status: str
    error: Optional[str] = None
    checked_at: Optional[str] = None
