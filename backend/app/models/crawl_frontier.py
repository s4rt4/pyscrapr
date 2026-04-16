"""Crawl frontier — the queue of URLs waiting to be crawled.

Persisted to SQLite so pause/resume survives process restart.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CrawlFrontier(Base, TimestampMixin):
    __tablename__ = "crawl_frontier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    parent_node_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_frontier_job_url", "job_id", "url", unique=True),
    )
