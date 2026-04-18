"""SMTP email notifier — stdlib only (smtplib + email.message).

Used as an alternative/parallel channel to webhook notifications. Reads
config from settings_store at call time. Never raises — returns bool.
"""
import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Optional

from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.email")

_TIMEOUT = 15


def _parse_recipients(raw: str) -> list[str]:
    return [r.strip() for r in (raw or "").split(",") if r.strip()]


def _send_sync(
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body: str,
    html: Optional[str],
) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=_TIMEOUT) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=_TIMEOUT) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as e:
        logger.warning("SMTP send failed to %s:%s: %s", host, port, e)
        return False


async def send_email(subject: str, body: str, html: Optional[str] = None) -> bool:
    """Send an email using current SMTP settings. Returns False on any failure."""
    if not get_setting("smtp_enabled", False):
        return False
    host = get_setting("smtp_host", "") or ""
    if not host:
        return False

    port = int(get_setting("smtp_port", 587) or 587)
    user = get_setting("smtp_user", "") or ""
    password = get_setting("smtp_password", "") or ""
    use_tls = bool(get_setting("smtp_use_tls", True))
    from_addr = get_setting("smtp_from", "") or user
    to_raw = get_setting("smtp_to", "") or ""

    to_addrs = _parse_recipients(to_raw)
    if not to_addrs:
        logger.warning("SMTP: no recipients configured")
        return False
    if not from_addr:
        logger.warning("SMTP: no from address (set smtp_from or smtp_user)")
        return False

    ok = await asyncio.to_thread(
        _send_sync,
        host, port, user, password, use_tls, from_addr, to_addrs,
        subject, body, html,
    )
    if ok:
        logger.info("SMTP email sent to %d recipient(s): %s", len(to_addrs), subject[:80])
    return ok


def build_job_email(
    job_type: str,
    url: str,
    status: str,
    stats: dict[str, Any],
    error: Optional[str] = None,
) -> tuple[str, str, str]:
    """Build (subject, text_body, html_body) for a job-completion email."""
    prefix = {
        "done": "[OK]",
        "error": "[ERROR]",
        "stopped": "[STOPPED]",
    }.get(status, "[INFO]")

    tool_name = job_type.replace("_", " ").title()
    subject = f"{prefix} PyScrapr - {tool_name}"

    # Build stat rows
    stat_rows: list[tuple[str, str]] = [
        ("Tool", tool_name),
        ("Status", status),
        ("URL", url),
    ]
    for key in ("downloaded", "crawled", "assets", "tagged", "skipped", "failed"):
        if key in stats:
            stat_rows.append((key.title(), str(stats[key])))
    if "bytes_total" in stats:
        try:
            mb = float(stats["bytes_total"]) / 1024 / 1024
            stat_rows.append(("Size", f"{mb:.2f} MB"))
        except (TypeError, ValueError):
            pass

    # Text body
    lines = [f"PyScrapr job completed: {status}", ""]
    for k, v in stat_rows:
        lines.append(f"  {k}: {v}")
    if error:
        lines += ["", "Error:", error[:2000]]
    text_body = "\n".join(lines)

    # HTML body
    color = {"done": "#22c55e", "error": "#ef4444", "stopped": "#eab308"}.get(status, "#3b9eff")
    rows_html = "".join(
        f'<tr><td style="padding:4px 12px 4px 0;color:#666;">{k}</td>'
        f'<td style="padding:4px 0;font-family:monospace;">{v}</td></tr>'
        for k, v in stat_rows
    )
    error_html = ""
    if error:
        safe_err = (error[:2000]).replace("<", "&lt;").replace(">", "&gt;")
        error_html = (
            f'<h3 style="color:#ef4444;margin-top:16px;">Error</h3>'
            f'<pre style="background:#fff1f0;padding:12px;border-radius:6px;'
            f'white-space:pre-wrap;word-break:break-word;">{safe_err}</pre>'
        )
    html_body = (
        f'<div style="font-family:system-ui,sans-serif;max-width:600px;">'
        f'<h2 style="color:{color};margin:0 0 8px 0;">{prefix} PyScrapr - {tool_name}</h2>'
        f'<p style="color:#666;margin:0 0 16px 0;">Job status: <b>{status}</b></p>'
        f'<table style="border-collapse:collapse;">{rows_html}</table>'
        f'{error_html}'
        f'<hr style="margin-top:24px;border:none;border-top:1px solid #eee;">'
        f'<p style="color:#999;font-size:12px;">Sent by PyScrapr</p>'
        f'</div>'
    )
    return subject, text_body, html_body
