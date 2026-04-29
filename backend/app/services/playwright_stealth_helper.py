"""Centralized helpers for applying anti-detection stealth to Playwright.

Two layers:
1. Browser launch args - free, no dep, hides AutomationControlled flag.
2. playwright-stealth - 17 evasions (navigator.webdriver, chrome object,
   WebGL renderer, plugins, languages, permissions API, etc).

Both are gated by `playwright_stealth_enabled` setting (default True).
Lazy import + try/except so missing playwright-stealth never breaks
scraping. Returns silently if stealth is disabled or unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services import settings_store

logger = logging.getLogger("pyscrapr.playwright")


def stealth_launch_args(extra: list[str] | None = None) -> list[str]:
    """Return chromium.launch args list with anti-detection flag prepended.

    Returns empty list (or just `extra`) if stealth is disabled.
    """
    if not settings_store.get("playwright_stealth_enabled", True):
        return list(extra or [])
    args = ["--disable-blink-features=AutomationControlled"]
    if extra:
        args.extend(extra)
    return args


async def apply_stealth_to_page(page: Any) -> None:
    """Apply playwright-stealth evasions to a freshly-created page.

    Silently no-ops if:
    - The setting is disabled
    - playwright-stealth isn't installed
    - Stealth raises any error (logged at debug)

    Never raises - calling code can wrap unconditionally.
    """
    if not settings_store.get("playwright_stealth_enabled", True):
        return
    try:
        from playwright_stealth import stealth_async  # type: ignore
    except ImportError:
        logger.debug(
            "playwright-stealth tidak terpasang, skip stealth (pip install playwright-stealth)"
        )
        return
    try:
        await stealth_async(page)
    except Exception as exc:
        logger.debug("playwright-stealth apply gagal (non-fatal): %s", exc)
