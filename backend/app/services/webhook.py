"""Webhook dispatcher — send notifications to Discord, Telegram, or generic HTTP.

Triggered when jobs complete (especially scheduled jobs with Diff detection).
"""
import asyncio
import logging
from typing import Any, Optional

import httpx

from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.webhook")


def _truncate(s: str, max_len: int = 2000) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


async def _send_discord(webhook_url: str, payload: dict[str, Any]) -> bool:
    """Send to Discord webhook with rich embed."""
    title = payload.get("title", "PyScrapr notification")
    description = payload.get("description", "")
    color = payload.get("color", 0x3b9eff)  # cyan
    fields = payload.get("fields", [])

    embed = {
        "title": _truncate(title, 256),
        "description": _truncate(description, 4096),
        "color": color,
        "fields": [
            {"name": _truncate(f["name"], 256), "value": _truncate(str(f["value"]), 1024), "inline": f.get("inline", True)}
            for f in fields[:25]
        ],
        "footer": {"text": "PyScrapr"},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            try:
                r = await client.post(webhook_url, json={"embeds": [embed]})
                if r.status_code in (200, 204):
                    return True
                if r.status_code == 429:  # rate limited
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                logger.warning("Discord webhook failed: %d %s", r.status_code, r.text[:200])
                return False
            except Exception as e:
                logger.warning("Discord webhook error (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(attempt + 1)
        return False


async def _send_telegram(bot_token: str, chat_id: str, payload: dict[str, Any]) -> bool:
    """Send to Telegram via Bot API."""
    title = payload.get("title", "PyScrapr")
    description = payload.get("description", "")
    fields = payload.get("fields", [])

    # Build Markdown message
    lines = [f"*{title}*", ""]
    if description:
        lines.append(description)
        lines.append("")
    for f in fields:
        lines.append(f"*{f['name']}:* `{f['value']}`")

    text = _truncate("\n".join(lines), 4096)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            try:
                r = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                })
                if r.status_code == 200:
                    return True
                if r.status_code == 429:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                logger.warning("Telegram webhook failed: %d %s", r.status_code, r.text[:200])
                return False
            except Exception as e:
                logger.warning("Telegram error (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(attempt + 1)
        return False


async def _send_generic(webhook_url: str, payload: dict[str, Any]) -> bool:
    """POST raw JSON payload to user-defined webhook URL."""
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            try:
                r = await client.post(webhook_url, json=payload)
                if 200 <= r.status_code < 300:
                    return True
                if r.status_code == 429:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                return False
            except Exception as e:
                logger.warning("Generic webhook error (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(attempt + 1)
        return False


async def notify(payload: dict[str, Any]) -> dict[str, bool]:
    """Dispatch payload to all configured channels.

    Payload shape:
      {
        "title": str,
        "description": str,
        "color": int (optional, Discord),
        "fields": [{"name": str, "value": str, "inline": bool}, ...]
      }
    """
    results = {"discord": False, "telegram": False, "generic": False}

    discord_url = get_setting("webhook_discord_url", "")
    telegram_token = get_setting("webhook_telegram_token", "")
    telegram_chat_id = get_setting("webhook_telegram_chat_id", "")
    generic_url = get_setting("webhook_generic_url", "")

    tasks = []
    if discord_url:
        tasks.append(("discord", _send_discord(discord_url, payload)))
    if telegram_token and telegram_chat_id:
        tasks.append(("telegram", _send_telegram(telegram_token, telegram_chat_id, payload)))
    if generic_url:
        tasks.append(("generic", _send_generic(generic_url, payload)))

    if not tasks:
        return results

    outcomes = await asyncio.gather(*(t[1] for t in tasks), return_exceptions=True)
    for (name, _), outcome in zip(tasks, outcomes):
        results[name] = outcome if isinstance(outcome, bool) else False

    return results


def build_job_done_payload(
    job_type: str,
    url: str,
    status: str,
    stats: dict[str, Any],
    diff: Optional[dict] = None,
) -> dict[str, Any]:
    """Build a standardized notification payload for a completed job."""
    color = 0x22c55e if status == "done" else 0xef4444 if status == "error" else 0xeab308
    emoji = "✅" if status == "done" else "❌" if status == "error" else "⏸️"

    fields = [
        {"name": "Tool", "value": job_type.replace("_", " ").title(), "inline": True},
        {"name": "Status", "value": status, "inline": True},
    ]

    # Add key stats
    for key in ("downloaded", "crawled", "assets", "tagged"):
        if key in stats:
            fields.append({"name": key.title(), "value": str(stats[key]), "inline": True})

    if "bytes_total" in stats:
        mb = stats["bytes_total"] / 1024 / 1024
        fields.append({"name": "Size", "value": f"{mb:.2f} MB", "inline": True})

    # Add diff summary if provided
    if diff:
        new_count = diff.get("new_count", 0)
        removed_count = diff.get("removed_count", 0)
        if new_count or removed_count:
            fields.append({
                "name": "Changes",
                "value": f"🆕 {new_count} new · 🗑️ {removed_count} removed",
                "inline": False,
            })

    return {
        "title": f"{emoji} PyScrapr — {job_type.replace('_', ' ').title()}",
        "description": f"Target: `{url[:100]}`",
        "color": color,
        "fields": fields,
    }
