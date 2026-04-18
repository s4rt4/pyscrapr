"""Webhook & email testing endpoints."""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.email_notify import _parse_recipients, _send_sync
from app.services.settings_store import get as get_setting
from app.services.webhook import build_job_done_payload, notify

logger = logging.getLogger("pyscrapr.api.webhooks")

router = APIRouter()


class TestWebhookRequest(BaseModel):
    channel: str = "all"  # all | discord | telegram | generic


@router.post("/test")
async def test_webhook(req: TestWebhookRequest):
    """Send a test notification to configured channels."""
    payload = build_job_done_payload(
        job_type="test_notification",
        url="https://example.com/test",
        status="done",
        stats={"downloaded": 42, "bytes_total": 12345678},
        diff={"new_count": 3, "removed_count": 1},
    )
    payload["title"] = "🧪 PyScrapr — Test Notification"
    payload["description"] = "This is a test to verify your webhook configuration is working."

    results = await notify(payload)
    return {
        "sent": results,
        "any_success": any(results.values()),
    }


class TestEmailRequest(BaseModel):
    to: Optional[str] = None  # override recipients (comma-separated)


email_router = APIRouter()


@email_router.post("/test")
async def test_email(req: TestEmailRequest):
    """Send a test email using current SMTP settings."""
    host = get_setting("smtp_host", "") or ""
    if not host:
        return {"success": False, "error": "SMTP host not configured"}

    port = int(get_setting("smtp_port", 587) or 587)
    user = get_setting("smtp_user", "") or ""
    password = get_setting("smtp_password", "") or ""
    use_tls = bool(get_setting("smtp_use_tls", True))
    from_addr = get_setting("smtp_from", "") or user

    to_raw = req.to if req.to else (get_setting("smtp_to", "") or "")
    to_addrs = _parse_recipients(to_raw)
    if not to_addrs:
        return {"success": False, "error": "No recipients configured"}
    if not from_addr:
        return {"success": False, "error": "No from address (set smtp_from or smtp_user)"}

    subject = "[TEST] PyScrapr - Email Notification Test"
    body = (
        "This is a test email from PyScrapr.\n\n"
        "If you received this message, your SMTP configuration is working correctly.\n"
    )
    html = (
        '<div style="font-family:system-ui,sans-serif;max-width:600px;">'
        '<h2 style="color:#3b9eff;">PyScrapr - Test Email</h2>'
        '<p>This is a test email from PyScrapr.</p>'
        '<p>If you received this message, your SMTP configuration is working correctly.</p>'
        '</div>'
    )

    try:
        ok = await asyncio.to_thread(
            _send_sync,
            host, port, user, password, use_tls, from_addr, to_addrs,
            subject, body, html,
        )
        if ok:
            return {"success": True, "error": None, "recipients": to_addrs}
        return {"success": False, "error": "SMTP send failed (see server logs)"}
    except Exception as e:
        logger.warning("Test email error: %s", e)
        return {"success": False, "error": str(e)}
