"""Global EventBus listener that fires webhooks on job completion.

Subscribes to ALL events across ALL jobs. When a job reaches terminal state
(done/error/stopped), looks up the job in DB and dispatches a notification
to configured webhook channels.
"""
import logging
from typing import Any

from app.db.session import AsyncSessionLocal
from app.repositories.job_repository import JobRepository
from app.services.settings_store import get as get_setting
from app.services.webhook import build_job_done_payload, notify

logger = logging.getLogger("pyscrapr.webhook_listener")

_TERMINAL_EVENTS = {"done", "error", "stopped"}


async def on_job_event(job_id: str, event: dict[str, Any]) -> None:
    """Handle global events — fire webhook when job reaches terminal state."""
    event_type = event.get("type")
    if event_type not in _TERMINAL_EVENTS:
        return

    # Gate by settings
    if event_type == "error" and not get_setting("webhook_on_error", True):
        return
    if event_type in ("done", "stopped") and not get_setting("webhook_on_done", True):
        return

    # Load job from DB
    try:
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.find_by_id(job_id)
            if not job:
                return

            job_type = job.type.value if hasattr(job.type, "value") else str(job.type)
            status = job.status.value if hasattr(job.status, "value") else str(job.status)

            payload = build_job_done_payload(
                job_type=job_type,
                url=job.url,
                status=status,
                stats=job.stats or event.get("stats", {}),
            )

            # If error, include error message
            if event_type == "error":
                err_msg = event.get("message") or job.error_message or "Unknown error"
                payload["description"] += f"\n\n**Error:** {err_msg[:500]}"

            results = await notify(payload)
            if any(results.values()):
                logger.info("Webhook sent for job %s: %s", job_id[:8], results)
    except Exception as e:
        logger.warning("Webhook listener error for job %s: %s", job_id[:8], e)
