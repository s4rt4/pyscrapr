"""Asset ORM model — one downloaded file belonging to a job."""
import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssetStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class AssetKind(str, enum.Enum):
    IMAGE = "image"
    CSS = "css"
    JS = "js"
    FONT = "font"
    HTML = "html"
    OTHER = "other"


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[AssetKind] = mapped_column(
        Enum(AssetKind), nullable=False, default=AssetKind.IMAGE
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus), nullable=False, default=AssetStatus.PENDING
    )
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha1: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    alt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
