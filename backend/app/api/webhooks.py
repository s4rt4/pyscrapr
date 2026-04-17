"""Webhook testing & manual trigger endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.webhook import build_job_done_payload, notify

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
