"""Link bypass engine — resolve shortened URLs and ad-gateway links.

Supports:
  1. Direct redirects (bit.ly, t.co, tinyurl, etc.) — follow HTTP 3xx chain
  2. Ad-gateways (adf.ly, linkvertise, ouo.io, shrinkme.io, etc.) — parse JS/HTML to extract final URL
"""
import asyncio
import base64
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote, urlparse

import certifi
import httpx


@dataclass
class BypassResult:
    original: str
    final: str
    chain: list[str]  # redirect chain
    method: str  # "redirect" | "adf.ly" | "ouo.io" | "linkvertise" | "generic_js" | "failed"
    error: Optional[str] = None


# ─── Known ad-gateway patterns ───

_ADFLY_HOSTS = {"adf.ly", "j.gs", "q.gs", "ay.gy"}
_OUO_HOSTS = {"ouo.io", "ouo.press"}
_SHRINKME_HOSTS = {"shrinkme.io", "shrinke.me"}
_LINKVERTISE_HOSTS = {"linkvertise.com", "link-to.net", "direct-link.net"}

# Generic patterns to find hidden URLs in page source
_JS_URL_PATTERNS = [
    re.compile(r'var\s+url\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'window\.location\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'location\.replace\(["\']([^"\']+)["\']\)', re.IGNORECASE),
    re.compile(r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\'][\d;]*\s*url=([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'href\s*=\s*["\']([^"\']*(?:https?://)[^"\']+)["\']', re.IGNORECASE),
]

_BASE64_URL_RE = re.compile(r'(?:atob|decode)\(["\']([A-Za-z0-9+/=]{20,})["\']', re.IGNORECASE)


def _extract_host(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def _is_gateway(url: str) -> str | None:
    host = _extract_host(url)
    if host in _ADFLY_HOSTS or any(host.endswith(f".{h}") for h in _ADFLY_HOSTS):
        return "adf.ly"
    if host in _OUO_HOSTS:
        return "ouo.io"
    if host in _SHRINKME_HOSTS:
        return "shrinkme.io"
    if host in _LINKVERTISE_HOSTS:
        return "linkvertise"
    return None


async def _follow_redirects(client: httpx.AsyncClient, url: str) -> tuple[str, list[str]]:
    """Follow redirect chain, return (final_url, chain)."""
    chain = [url]
    current = url
    for _ in range(15):  # max redirect depth
        try:
            r = await client.get(current, follow_redirects=False)
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("location", "")
                if not loc:
                    break
                if not loc.startswith("http"):
                    from urllib.parse import urljoin
                    loc = urljoin(current, loc)
                chain.append(loc)
                current = loc
            else:
                break
        except Exception:
            break
    return current, chain


def _try_decode_base64_urls(html: str) -> list[str]:
    """Find base64-encoded URLs in page source."""
    urls = []
    for m in _BASE64_URL_RE.finditer(html):
        try:
            decoded = base64.b64decode(m.group(1)).decode(errors="ignore")
            if decoded.startswith("http"):
                urls.append(decoded)
        except Exception:
            pass
    return urls


def _extract_urls_from_html(html: str) -> list[str]:
    """Find any URLs hidden in JavaScript or meta tags."""
    urls = []
    for pattern in _JS_URL_PATTERNS:
        for m in pattern.finditer(html):
            u = m.group(1)
            if u.startswith("http") and "gateway" not in u.lower():
                urls.append(u)
    urls.extend(_try_decode_base64_urls(html))
    return urls


async def _bypass_adfly(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """adf.ly stores the real URL in a base64-encoded var or ysmm variable."""
    try:
        r = await client.get(url)
        html = r.text
        # Look for var ysmm = '...'
        m = re.search(r"var\s+ysmm\s*=\s*'([^']+)'", html)
        if m:
            encoded = m.group(1)
            # adf.ly uses a custom encoding: swap chars at odd/even positions then base64
            left = ""
            right = ""
            for i, c in enumerate(encoded):
                if i % 2 == 0:
                    left += c
                else:
                    right = c + right
            decoded = base64.b64decode(left + right).decode(errors="ignore")
            if decoded.startswith("http"):
                return decoded
        # Fallback: look for generic URLs
        found = _extract_urls_from_html(html)
        return found[0] if found else None
    except Exception:
        return None


async def _bypass_ouo(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """ouo.io — follow the form submission chain."""
    try:
        r = await client.get(url)
        html = r.text
        # ouo.io often has a form with action URL
        m = re.search(r'<form[^>]*action="([^"]+)"', html)
        if m:
            action = m.group(1)
            if not action.startswith("http"):
                from urllib.parse import urljoin
                action = urljoin(url, action)
            # Submit empty form to get redirect
            r2 = await client.post(action, data={}, follow_redirects=True)
            if r2.url and str(r2.url) != url:
                return str(r2.url)
        found = _extract_urls_from_html(html)
        return found[0] if found else None
    except Exception:
        return None


async def bypass_single(url: str) -> BypassResult:
    """Resolve a single URL — detect type and apply appropriate strategy."""
    async with httpx.AsyncClient(
        timeout=20,
        verify=certifi.where(),
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    ) as client:
        gateway = _is_gateway(url)

        if gateway == "adf.ly":
            final = await _bypass_adfly(client, url)
            if final:
                return BypassResult(original=url, final=final, chain=[url, final], method="adf.ly")

        elif gateway == "ouo.io":
            final = await _bypass_ouo(client, url)
            if final:
                return BypassResult(original=url, final=final, chain=[url, final], method="ouo.io")

        elif gateway == "linkvertise":
            # Linkvertise is JS-heavy — try basic HTML extraction first
            try:
                r = await client.get(url)
                found = _extract_urls_from_html(r.text)
                if found:
                    return BypassResult(original=url, final=found[0], chain=[url, found[0]], method="linkvertise")
            except Exception:
                pass
            return BypassResult(original=url, final=url, chain=[url], method="failed",
                                error="Linkvertise requires JS rendering (Playwright). Basic bypass failed.")

        elif gateway == "shrinkme.io":
            try:
                r = await client.get(url)
                found = _extract_urls_from_html(r.text)
                if found:
                    return BypassResult(original=url, final=found[0], chain=[url, found[0]], method="shrinkme.io")
            except Exception:
                pass

        # Default: follow HTTP redirects
        final, chain = await _follow_redirects(client, url)
        if final != url:
            return BypassResult(original=url, final=final, chain=chain, method="redirect")

        # Last resort: fetch page and scan for hidden URLs
        try:
            r = await client.get(url, follow_redirects=True)
            found = _extract_urls_from_html(r.text)
            if found and found[0] != url:
                return BypassResult(original=url, final=found[0], chain=[url, found[0]], method="generic_js")
        except Exception:
            pass

        return BypassResult(original=url, final=url, chain=[url], method="failed",
                            error="Could not resolve final URL")


async def bypass_batch(urls: list[str], concurrency: int = 5) -> list[BypassResult]:
    """Resolve multiple URLs in parallel."""
    sem = asyncio.Semaphore(concurrency)

    async def _one(u: str) -> BypassResult:
        async with sem:
            return await bypass_single(u)

    return await asyncio.gather(*[_one(u) for u in urls])
