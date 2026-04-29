"""Exposure Scanner - probe known leak paths against a target URL.

Designed for auditing your own sites. Each path is HEAD-tested first, then
GETted on a positive hit, then validated for plausibility so we don't
report a generic 404 page as a finding.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.exposure")


# (path, category, base_severity)
EXPOSURE_PATHS: list[tuple[str, str, str]] = [
    # Git exposed
    ("/.git/HEAD", "git", "critical"),
    ("/.git/config", "git", "critical"),
    ("/.git/index", "git", "high"),
    # Env files
    ("/.env", "env", "critical"),
    ("/.env.local", "env", "critical"),
    ("/.env.production", "env", "critical"),
    ("/.env.development", "env", "high"),
    # Database / backup
    ("/backup.sql", "backup", "critical"),
    ("/database.sql", "backup", "critical"),
    ("/dump.sql", "backup", "critical"),
    ("/db.sqlite", "backup", "high"),
    # WordPress backups
    ("/wp-config.php.bak", "wordpress", "critical"),
    ("/wp-config.php~", "wordpress", "critical"),
    ("/wp-config.php.old", "wordpress", "critical"),
    # IDE / OS metadata
    ("/.DS_Store", "metadata", "low"),
    ("/.svn/entries", "svn", "high"),
    ("/.idea/workspace.xml", "ide", "medium"),
    ("/.vscode/settings.json", "ide", "low"),
    # Composer / package
    ("/composer.json", "manifest", "info"),
    ("/composer.lock", "manifest", "info"),
    ("/package.json", "manifest", "info"),
    # Server config
    ("/.htaccess.bak", "server", "high"),
    ("/web.config.bak", "server", "high"),
    ("/server-status", "server", "medium"),
    # PHP info leak
    ("/phpinfo.php", "phpinfo", "high"),
    ("/info.php", "phpinfo", "high"),
    ("/test.php", "phpinfo", "low"),
    # Credentials / SSH keys
    ("/.aws/credentials", "ssh", "critical"),
    ("/id_rsa", "ssh", "critical"),
    ("/.ssh/id_rsa", "ssh", "critical"),
]


_DS_STORE_MAGIC = b"\x00\x00\x00\x01Bud1"
_HTML_DOCTYPE_RE = re.compile(rb"<!doctype\s+html", re.IGNORECASE)
_ENV_LINE_RE = re.compile(r"^[A-Z_][A-Z0-9_]*\s*=", re.MULTILINE)
_SECRET_KEYS = ("AWS_SECRET", "STRIPE_SECRET", "DATABASE_URL")


def _normalize_base_url(raw: str) -> str:
    raw = (raw or "").strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _sanitize_preview(content: bytes, limit: int = 200) -> str:
    try:
        text = content[:600].decode("utf-8", errors="replace")
    except Exception:
        text = ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _check_plausibility(path: str, category: str, content: bytes, homepage: bytes | None) -> bool:
    """Decide if the response looks like a real leak vs a 404 fallback page."""
    if not content:
        return False

    # Format-specific signatures
    if path.endswith("/.git/HEAD"):
        head = content[:128].decode("utf-8", errors="replace").strip()
        return head.startswith("ref: refs/")
    if path.endswith("/.git/config"):
        return b"[core]" in content or b"[remote " in content
    if path.endswith("/.git/index"):
        return content[:4] == b"DIRC"
    if path.endswith("/.DS_Store"):
        return content.startswith(_DS_STORE_MAGIC)
    if category == "env":
        text = content[:2000].decode("utf-8", errors="replace")
        if _HTML_DOCTYPE_RE.search(content[:200]):
            return False
        return bool(_ENV_LINE_RE.search(text))
    if path.endswith(".sql"):
        head = content[:512].decode("utf-8", errors="replace").lower()
        if "<html" in head or "<!doctype" in head:
            return False
        return any(k in head for k in ("create table", "insert into", "drop table", "-- mysql", "pg_dump"))
    if path.endswith(".sqlite"):
        return content[:16].startswith(b"SQLite format 3")
    if category == "wordpress":
        if _HTML_DOCTYPE_RE.search(content[:200]):
            return False
        head = content[:512].decode("utf-8", errors="replace")
        return "<?php" in head or "DB_NAME" in head or "DB_PASSWORD" in head
    if category == "phpinfo":
        return b"phpinfo()" in content[:4000] or b"PHP Version" in content[:4000]
    if category == "manifest":
        text = content[:1000].decode("utf-8", errors="replace").lstrip()
        return text.startswith("{")
    if category == "ide":
        head = content[:200]
        return head.startswith(b"<?xml") or head.lstrip().startswith(b"{")
    if category == "ssh":
        head = content[:200].decode("utf-8", errors="replace")
        if "BEGIN" in head and ("PRIVATE KEY" in head or "RSA" in head):
            return True
        if "aws_access_key_id" in head.lower() or "[default]" in head:
            return True
        return False
    if category == "svn":
        return content[:8].isdigit() or b"dir\n" in content[:100]
    if category == "server" and path.endswith("server-status"):
        return b"Apache Server Status" in content[:4000] or b"Server Version" in content[:4000]
    if category == "server":
        # .htaccess.bak / web.config.bak
        if _HTML_DOCTYPE_RE.search(content[:200]):
            return False
        head = content[:512].decode("utf-8", errors="replace")
        return ("RewriteEngine" in head) or head.lstrip().startswith("<?xml") or "<configuration" in head

    # Fallback: not a homepage clone, not generic 404 HTML
    if homepage and len(content) > 32 and content[:200] == homepage[:200]:
        return False
    if _HTML_DOCTYPE_RE.search(content[:200]):
        return False
    return True


class ExposureScanner:
    async def scan(self, base_url: str, throttle_seconds: float = 1.0) -> dict[str, Any]:
        normalized = _normalize_base_url(base_url)
        scanned_at = datetime.now(timezone.utc).isoformat()
        if not normalized:
            return {
                "base_url": base_url,
                "scanned_at": scanned_at,
                "total_checked": 0,
                "total_found": 0,
                "findings": [],
                "error": "URL tidak valid",
            }

        findings: list[dict[str, Any]] = []
        homepage_bytes: bytes | None = None

        try:
            async with build_client(timeout=10, target_url=normalized) as client:
                # Try fetch homepage as 404-fingerprint baseline
                try:
                    home_resp = await client.get(normalized + "/", follow_redirects=True)
                    if home_resp.status_code < 500:
                        homepage_bytes = home_resp.content[:600]
                except httpx.HTTPError as e:
                    logger.info("homepage fetch failed for %s: %s", normalized, e)
                    return {
                        "base_url": normalized,
                        "scanned_at": scanned_at,
                        "total_checked": 0,
                        "total_found": 0,
                        "findings": [],
                        "error": f"Tidak bisa mengakses base URL: {e}",
                    }

                first = True
                for path, category, base_sev in EXPOSURE_PATHS:
                    if not first and throttle_seconds > 0:
                        await asyncio.sleep(throttle_seconds)
                    first = False

                    full = normalized + path
                    status = 0
                    content_preview: str | None = None
                    plausible = False
                    severity = base_sev

                    try:
                        head = await client.head(full, follow_redirects=False)
                        status = head.status_code
                    except httpx.HTTPError as e:
                        logger.debug("HEAD %s failed: %s", full, e)
                        continue

                    if status not in (200, 301, 302):
                        continue

                    # If redirect, check Location is not just a homepage redirect
                    if status in (301, 302):
                        try:
                            get_resp = await client.get(full, follow_redirects=False)
                            status = get_resp.status_code
                        except httpx.HTTPError:
                            continue
                        if status in (301, 302):
                            # bare redirect, skip
                            continue

                    try:
                        get_resp = await client.get(full, follow_redirects=False)
                    except httpx.HTTPError as e:
                        logger.debug("GET %s failed: %s", full, e)
                        continue

                    status = get_resp.status_code
                    if status != 200:
                        continue

                    content = get_resp.content or b""
                    plausible = _check_plausibility(path, category, content, homepage_bytes)
                    content_preview = _sanitize_preview(content)

                    # Severity escalation for env files leaking known secret keys
                    if category == "env" and plausible:
                        try:
                            text = content[:4000].decode("utf-8", errors="replace")
                            if any(k in text for k in _SECRET_KEYS):
                                severity = "critical"
                        except Exception:
                            pass

                    findings.append(
                        {
                            "path": path,
                            "category": category,
                            "severity": severity,
                            "status": status,
                            "content_preview": content_preview,
                            "plausible": plausible,
                        }
                    )
        except Exception as e:
            logger.exception("exposure scan failed: %s", e)
            return {
                "base_url": normalized,
                "scanned_at": scanned_at,
                "total_checked": 0,
                "total_found": len(findings),
                "findings": findings,
                "error": f"Scan error: {e}",
            }

        return {
            "base_url": normalized,
            "scanned_at": scanned_at,
            "total_checked": len(EXPOSURE_PATHS),
            "total_found": len(findings),
            "findings": findings,
            "error": None,
        }


_singleton: ExposureScanner | None = None


def get_scanner() -> ExposureScanner:
    global _singleton
    if _singleton is None:
        _singleton = ExposureScanner()
    return _singleton
