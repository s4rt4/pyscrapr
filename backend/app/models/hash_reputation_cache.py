"""SQLite cache for VirusTotal + MalwareBazaar hash lookups.

Caches results indexed by (sha256, source) so the same file scanned
again does not burn the rate-limited public API quota. Negative results
are also cached but with a TTL (re-check after 7 days in case the
sample appears later).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HashReputationCache(Base):
    __tablename__ = "hash_reputation_cache"
    __table_args__ = (UniqueConstraint("sha256", "source", name="uq_hash_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))  # "vt" | "mb"
    found: Mapped[bool] = mapped_column(Boolean, default=False)  # True = positive hit
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
