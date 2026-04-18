"""Global EventBus listener that sends SMTP email on job completion.

Mirrors webhook_listener.py — subscribes to all job events, dispatches
email on terminal events (done/error/stopped) if enabled in settings.
"""
import logging
from typing import Any

from app.db.session import AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.services.email_notify import build_job_email, send_email
from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.email_listener")

_TERMINAL_EVENTS = {"done", "error", "stopped"}


async def on_job_event(job_id: str, event: dict[str, Any]) -> None:
    """Handle global events — send email when job reaches terminal state."""
    event_type = event.get("type")
    if event_type not in _TERMINAL_EVENTS:
        return

    if not get_setting("smtp_enabled", False):
        return
    if event_type == "error" and not get_setting("smtp_on_error", True):
        return
    if event_type in ("done", "stopped") and not get_setting("smtp_on_done", True):
        return

    try:
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(job_id)
            if not job:
                return

            job_type = job.type.value if hasattr(job.type, "value") else str(job.type)
            status = job.status.value if hasattr(job.status, "value") else str(job.status)

            err_msg = None
            if event_type == "error":
                err_msg = event.get("message") or job.error_message or "Unknown error"

            subject, text_body, html_body = build_job_email(
                job_type=job_type,
                url=job.url,
                status=status,
                stats=job.stats or event.get("stats", {}),
                error=err_msg,
            )

            ok = await send_email(subject, text_body, html_body)
            if ok:
                logger.info("Email sent for job %s (%s)", job_id[:8], event_type)
    except Exception as e:
        logger.warning("Email listener error for job %s: %s", job_id[:8], e)
