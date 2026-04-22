"""Job ORM model — represents a scraping run."""
import enum
from typing import Optional

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class JobType(str, enum.Enum):
    IMAGE_HARVESTER = "image_harvester"
    URL_MAPPER = "url_mapper"
    SITE_RIPPER = "site_ripper"
    MEDIA_DOWNLOADER = "media_downloader"
    AI_TAGGING = "ai_tagging"
    TECH_DETECTOR = "tech_detector"
    SEO_AUDIT = "seo_audit"
    LINK_CHECK = "link_check"
    SECURITY_SCAN = "security_scan"
    SSL_INSPECT = "ssl_inspect"
    DOMAIN_INTEL = "domain_intel"
    WAYBACK_LOOKUP = "wayback_lookup"
    SITEMAP_ANALYZE = "sitemap_analyze"
    SCREENSHOT = "screenshot"
    THREAT_SCAN = "threat_scan"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    STOPPED = "stopped"


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True
    )
    # JSON blobs for flexibility — structured access via services
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_dir: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
