"""PriceProduct ORM model — represents a product URL being monitored for price changes."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PriceProduct(Base, TimestampMixin):
    __tablename__ = "price_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selector: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selector_type: Mapped[str] = mapped_column(String(10), default="auto", nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_below: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alert_above: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
