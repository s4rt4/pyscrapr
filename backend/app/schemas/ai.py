"""Pydantic schemas for AI Tools (Phase 5)."""
from pydantic import BaseModel, Field


class TaggingStartRequest(BaseModel):
    harvester_job_id: str = Field(description="Job ID of a completed Image Harvester run")
    labels: list[str] = Field(
        min_length=1,
        max_length=50,
        description="Free-form text labels for zero-shot classification",
        default=["logo", "hero image", "product", "icon", "background", "portrait", "food", "text"],
    )


class TagResult(BaseModel):
    path: str
    filename: str
    scores: dict[str, float]
    top_tag: str | None
    top_score: float


class TaggingResponse(BaseModel):
    job_id: str
    harvester_job_id: str
    total_images: int
    tagged: int
    results: list[TagResult]
