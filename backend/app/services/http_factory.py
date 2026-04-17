"""Factory for pre-configured httpx.AsyncClient + Downloader.

Centralizes UA rotation, proxy selection, cookie injection, and retry config
so all orchestrators (harvester, mapper, ripper, media, etc.) share the same
network behavior based on user settings.
"""
import logging
from typing import Optional

import certifi
import httpx

from app.config import settings as app_config
from app.services.auth_vault import get_profile
from app.services.downloader import Downloader
from app.services.proxy_manager import ProxyManager
from app.services.settings_store import get as get_setting
from app.services.ua_rotator import UARotator

logger = logging.getLogger("pyscrapr.http")


def build_proxy_manager() -> ProxyManager:
    raw = get_setting("proxy_list", "") or ""
    mode = get_setting("proxy_mode", "round_robin") or "round_robin"
    proxies = [line.strip() for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]
    return ProxyManager(proxies=proxies, mode=mode)


def build_ua_rotator() -> UARotator:
    mode = get_setting("ua_mode", "random") or "random"
    return UARotator(mode=mode)


def build_client(
    *,
    timeout: Optional[int] = None,
    target_url: Optional[str] = None,
    extra_headers: Optional[dict] = None,
) -> httpx.AsyncClient:
    """Build a configured httpx.AsyncClient with proxy + base headers + auth vault cookies.

    target_url: if provided, looks up matching auth vault profile and injects cookies/headers.
    """
    timeout_val = timeout or int(get_setting("default_timeout", app_config.default_timeout) or app_config.default_timeout)
    ua = get_setting("user_agent", app_config.default_user_agent) or app_config.default_user_agent

    headers: dict[str, str] = {"User-Agent": ua}
    cookies: dict[str, str] = {}

    # Auth vault integration — resolve domain from URL
    if target_url:
        try:
            from urllib.parse import urlparse
            host = urlparse(target_url).netloc.lower()
            # Try exact match first, then strip www., then try parent domain
            for candidate in (host, host.removeprefix("www."), ".".join(host.split(".")[-2:])):
                profile = get_profile(candidate)
                if profile:
                    if profile.get("headers"):
                        headers.update(profile["headers"])
                    if profile.get("cookies"):
                        cookies.update(profile["cookies"])
                    logger.info("Auth vault profile applied: %s", candidate)
                    break
        except Exception as e:
            logger.debug("Auth vault lookup failed: %s", e)

    if extra_headers:
        headers.update(extra_headers)

    # Proxy
    proxy_mgr = build_proxy_manager()
    proxy = proxy_mgr.get_httpx_proxy_arg() if proxy_mgr.enabled else None

    kwargs: dict = {
        "timeout": timeout_val,
        "headers": headers,
        "cookies": cookies,
        "verify": certifi.where(),
        "follow_redirects": True,
    }
    if proxy:
        kwargs["proxy"] = proxy
        logger.info("Using proxy: %s", proxy.split("@")[-1] if "@" in proxy else proxy)

    return httpx.AsyncClient(**kwargs)


def build_downloader(
    client: httpx.AsyncClient,
    max_concurrency: Optional[int] = None,
) -> Downloader:
    """Build a Downloader with UA rotator + retry config from settings."""
    concurrency = max_concurrency or int(
        get_setting("default_concurrency", app_config.max_concurrent_downloads) or 8
    )
    max_retries = int(get_setting("max_retries", 3) or 3)
    ua_rotator = build_ua_rotator()

    return Downloader(
        client=client,
        max_concurrency=concurrency,
        max_retries=max_retries,
        ua_rotator=ua_rotator,
    )
