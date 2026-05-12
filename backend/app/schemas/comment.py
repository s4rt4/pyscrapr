"""Schemas for Comment Harvester (P11)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SentimentScore(BaseModel):
    label: str  # "positive" | "neutral" | "negative"
    confidence: float = 0.0


class CommentNode(BaseModel):
    id: str
    author: Optional[str] = None
    text: str = ""
    timestamp: Optional[str] = None  # ISO string when available
    upvotes: Optional[int] = None
    depth: int = 0
    sentiment: Optional[SentimentScore] = None
    replies: List["CommentNode"] = Field(default_factory=list)


CommentNode.model_rebuild()


class CommentHarvestRequest(BaseModel):
    url: str
    max_comments: int = 500
    include_replies: bool = True
    sentiment_enabled: bool = False


class CommentHarvestReport(BaseModel):
    url: str
    platform: str  # "youtube" | "reddit" | "forum" | "unknown"
    title: Optional[str] = None
    fetched_at: str
    total_comments: int
    total_replies: int
    max_depth: int
    sentiment_summary: Optional[dict] = None  # {"positive": N, "neutral": N, "negative": N}
    comments: List[CommentNode] = Field(default_factory=list)


class CommentHarvestResponse(BaseModel):
    job_id: str
    status: str
    report: Optional[CommentHarvestReport] = None
    error_message: Optional[str] = None
