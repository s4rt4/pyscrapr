"""Crawl node model — represents a single crawled page in a URL Mapper job.

Forms a tree via parent_id (self-referential). The root node has parent_id=None.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CrawlNode(Base, TimestampMixin):
    __tablename__ = "crawl_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("crawl_nodes.id", ondelete="SET NULL"), nullable=True
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # Response metadata
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_crawl_nodes_job_url", "job_id", "url", unique=True),
        Index("ix_crawl_nodes_job_parent", "job_id", "parent_id"),
    )
