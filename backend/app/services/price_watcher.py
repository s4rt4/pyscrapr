"""Price Watcher — fetches product pages, extracts price, stores history, alerts on threshold.

Auto-detect heuristics ordered by reliability:
  1. <meta property="product:price:amount" content="..."> (Open Graph product)
  2. <meta property="og:price:amount" content="...">
  3. <meta itemprop="price" content="..."> / <span itemprop="price">
  4. schema.org JSON-LD Product offers.price
  5. Common attribute hooks: [data-price], [data-test-id*=price], [data-testid*=price]
  6. Amazon: .a-price .a-offscreen
  7. Generic class names: .price, .product-price, .harga, .current-price, .price-current
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup

from app.db.session import AsyncSessionLocal
from app.models.price_product import PriceProduct
from app.repositories.price_repository import PriceRepository
from app.services.http_factory import build_client
from app.services.webhook import notify

logger = logging.getLogger("pyscrapr.price_watcher")

# ───── HTML fetch cache (60s TTL) ─────
_HTML_CACHE: dict[str, tuple[float, str]] = {}
_HTML_CACHE_TTL = 60.0


def _cache_get(url: str) -> Optional[str]:
    entry = _HTML_CACHE.get(url)
    if not entry:
        return None
    ts, html = entry
    if time.time() - ts > _HTML_CACHE_TTL:
        _HTML_CACHE.pop(url, None)
        return None
    return html


def _cache_put(url: str, html: str) -> None:
    _HTML_CACHE[url] = (time.time(), html)


async def _fetch_html(url: str, timeout: int = 25) -> str:
    cached = _cache_get(url)
    if cached is not None:
        return cached
    async with build_client(timeout=timeout, target_url=url) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        html = r.text
        _cache_put(url, html)
        return html


# ───── price text parsing ─────

_CURRENCY_TOKENS = (
    "rp", "idr", "usd", "eur", "sgd", "myr", "gbp", "aud", "jpy", "krw",
    "cny", "rmb", "inr", "thb", "vnd", "php",
    "$", "€", "£", "¥", "₩", "₫", "₱", "฿", "₹",
)
_DIGITS_RE = re.compile(r"[\d.,\s]+")


def parse_price_text(text: str) -> Optional[float]:
    """Robust price parser. Returns float or None.

    Handles:
      - "Rp 1.234.567" (Indonesian thousand separators)
      - "$1,234.56" (English thousand + decimal)
      - "1234,56 €" (European: comma decimal)
      - "USD 99.99"
      - free text like "Harga termurah: Rp99.000 saja!"
    """
    if not text:
        return None

    raw = text.strip()
    lower = raw.lower()

    # Strip known currency tokens
    cleaned = lower
    for tok in _CURRENCY_TOKENS:
        cleaned = cleaned.replace(tok, " ")

    # Find first run of digits + separators
    m = _DIGITS_RE.search(cleaned)
    if not m:
        return None
    candidate = m.group(0).strip()
    candidate = re.sub(r"\s+", "", candidate)
    if not candidate or not any(ch.isdigit() for ch in candidate):
        return None

    # Determine decimal separator. Convention:
    # - If both . and , present, the rightmost is the decimal separator.
    # - If only one separator and it appears once with 1-2 trailing digits, treat as decimal.
    # - If only one separator and it appears multiple times, treat as thousand separator.
    has_dot = "." in candidate
    has_comma = "," in candidate

    if has_dot and has_comma:
        if candidate.rfind(",") > candidate.rfind("."):
            # Comma is decimal: 1.234,56
            candidate = candidate.replace(".", "").replace(",", ".")
        else:
            # Dot is decimal: 1,234.56
            candidate = candidate.replace(",", "")
    elif has_comma:
        parts = candidate.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            candidate = candidate.replace(",", ".")
        else:
            candidate = candidate.replace(",", "")
    elif has_dot:
        parts = candidate.split(".")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            # Decimal point
            pass
        else:
            # Thousand separator (Indonesian style)
            candidate = candidate.replace(".", "")

    try:
        return float(candidate)
    except ValueError:
        return None


# ───── auto-detect extraction ─────

_AUTO_SELECTORS = [
    # OG / meta first
    ('meta[property="product:price:amount"]', "content"),
    ('meta[property="og:price:amount"]', "content"),
    ('meta[property="og:product:price:amount"]', "content"),
    ('meta[itemprop="price"]', "content"),
    ('meta[name="price"]', "content"),
    # itemprop spans
    ('[itemprop="price"]', None),
    # Common data attributes
    ("[data-price]", "data-price"),
    ('[data-testid*="price" i]', None),
    ('[data-test-id*="price" i]', None),
    # Amazon
    (".a-price .a-offscreen", None),
    (".a-price-whole", None),
    # Common class names (English + Indonesian)
    (".product-price", None),
    (".price-current", None),
    (".current-price", None),
    (".sale-price", None),
    (".price", None),
    (".harga", None),
    (".harga-produk", None),
]


def _extract_jsonld_price(soup: BeautifulSoup) -> Optional[str]:
    """Walk schema.org JSON-LD blocks looking for Product/Offer price."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        # Could be a list or a single object
        candidates = data if isinstance(data, list) else [data]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                candidates.extend(g for g in graph if isinstance(g, dict))
            t = node.get("@type", "")
            t_list = t if isinstance(t, list) else [t]
            if not any(str(x).lower() in ("product", "offer", "aggregateoffer") for x in t_list):
                # Still check offers nested under any type
                pass
            offers = node.get("offers")
            if offers:
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("lowPrice")
                    if price:
                        return str(price)
                elif isinstance(offers, list):
                    for off in offers:
                        if isinstance(off, dict):
                            price = off.get("price") or off.get("lowPrice")
                            if price:
                                return str(price)
            price = node.get("price")
            if price:
                return str(price)
    return None


async def _extract_price_auto(html: str) -> dict[str, Any]:
    """Run auto-detect heuristics. Returns {price, raw_text, matched_on} or {price: None}."""
    soup = BeautifulSoup(html, "html.parser")

    # 1) JSON-LD
    jsonld_price = _extract_jsonld_price(soup)
    if jsonld_price:
        price = parse_price_text(jsonld_price)
        if price is not None:
            return {"price": price, "raw_text": jsonld_price, "matched_on": "jsonld"}

    # 2) Selector list
    for selector, attr in _AUTO_SELECTORS:
        try:
            el = soup.select_one(selector)
        except Exception:
            continue
        if not el:
            continue
        if attr:
            value = el.get(attr) or ""
        else:
            value = el.get_text(" ", strip=True)
        if not value:
            continue
        price = parse_price_text(str(value))
        if price is not None:
            return {"price": price, "raw_text": str(value)[:300], "matched_on": selector}

    return {"price": None, "raw_text": None, "matched_on": None}


def _extract_by_css(html: str, selector: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    try:
        el = soup.select_one(selector)
    except Exception as e:
        return {"price": None, "raw_text": None, "error": f"selector error: {e}"}
    if not el:
        return {"price": None, "raw_text": None, "error": "selector matched nothing"}
    # Prefer content attribute if it's a meta tag
    if el.name == "meta":
        raw = el.get("content", "") or ""
    else:
        raw = el.get_text(" ", strip=True)
        # Fallback to data-price-like attributes
        if not raw:
            for a in ("content", "data-price", "value"):
                if el.get(a):
                    raw = str(el.get(a))
                    break
    price = parse_price_text(raw)
    return {"price": price, "raw_text": raw[:300] if raw else None}


def _extract_by_xpath(html: str, xpath: str) -> dict[str, Any]:
    try:
        from lxml import html as lxml_html  # type: ignore
    except ImportError:
        return {"price": None, "raw_text": None, "error": "lxml not installed"}
    try:
        tree = lxml_html.fromstring(html)
        nodes = tree.xpath(xpath)
    except Exception as e:
        return {"price": None, "raw_text": None, "error": f"xpath error: {e}"}
    if not nodes:
        return {"price": None, "raw_text": None, "error": "xpath matched nothing"}
    node = nodes[0]
    if hasattr(node, "text_content"):
        raw = node.text_content().strip()
    else:
        raw = str(node).strip()
    price = parse_price_text(raw)
    return {"price": price, "raw_text": raw[:300] if raw else None}


def _extract_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Prefer OG title
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            return str(og["content"]).strip()[:300]
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:300]
    except Exception:
        pass
    return ""


# ───── public API ─────

async def check_product(product: PriceProduct) -> dict[str, Any]:
    """Run a single check for the given product. Does NOT persist — caller is responsible."""
    try:
        html = await _fetch_html(product.url)
    except Exception as e:
        logger.warning("Price fetch failed for %s: %s", product.url, e)
        return {
            "price": None,
            "status": "error",
            "raw_text": None,
            "error": f"fetch failed: {e}",
        }

    selector_type = (product.selector_type or "auto").lower()
    selector = (product.selector or "").strip()

    if selector_type == "auto" or not selector:
        result = await _extract_price_auto(html)
        if result["price"] is not None:
            return {
                "price": result["price"],
                "status": "ok",
                "raw_text": result["raw_text"],
                "error": None,
                "matched_on": result.get("matched_on"),
            }
        return {
            "price": None,
            "status": "not_found",
            "raw_text": None,
            "error": "auto-detect: no price element found",
        }

    if selector_type == "xpath":
        result = _extract_by_xpath(html, selector)
    else:
        result = _extract_by_css(html, selector)

    if result.get("price") is not None:
        return {
            "price": result["price"],
            "status": "ok",
            "raw_text": result.get("raw_text"),
            "error": None,
        }
    return {
        "price": None,
        "status": "not_found" if "matched nothing" in (result.get("error") or "") else "error",
        "raw_text": result.get("raw_text"),
        "error": result.get("error") or "no price extracted",
    }


async def extract_preview(
    url: str,
    selector: str = "",
    selector_type: str = "auto",
) -> dict[str, Any]:
    """Test extraction without persisting. Also returns detected page title."""
    try:
        html = await _fetch_html(url)
    except Exception as e:
        return {
            "price": None,
            "status": "error",
            "raw_text": None,
            "error": f"fetch failed: {e}",
            "title": "",
        }

    title = _extract_title(html)
    selector_type = (selector_type or "auto").lower()

    if selector_type == "auto" or not selector:
        result = await _extract_price_auto(html)
        return {
            "price": result["price"],
            "status": "ok" if result["price"] is not None else "not_found",
            "raw_text": result.get("raw_text"),
            "error": None if result["price"] is not None else "auto-detect: no price element found",
            "matched_on": result.get("matched_on"),
            "title": title,
        }

    if selector_type == "xpath":
        result = _extract_by_xpath(html, selector)
    else:
        result = _extract_by_css(html, selector)
    return {
        "price": result.get("price"),
        "status": "ok" if result.get("price") is not None else (
            "not_found" if "matched nothing" in (result.get("error") or "") else "error"
        ),
        "raw_text": result.get("raw_text"),
        "error": result.get("error"),
        "title": title,
    }


async def _maybe_alert(product: PriceProduct, new_price: float, prev_price: Optional[float]) -> None:
    """Fire webhook alert if price crossed threshold."""
    fired_reason = None
    if product.alert_below is not None and new_price < product.alert_below:
        # Only fire if previous price was above (or not set), to avoid spamming
        if prev_price is None or prev_price >= product.alert_below:
            fired_reason = f"harga turun di bawah {product.alert_below:,.0f} {product.currency}"
    if product.alert_above is not None and new_price > product.alert_above:
        if prev_price is None or prev_price <= product.alert_above:
            fired_reason = f"harga naik di atas {product.alert_above:,.0f} {product.currency}"

    if not fired_reason:
        return

    delta = ""
    if prev_price is not None:
        diff = new_price - prev_price
        pct = (diff / prev_price * 100.0) if prev_price else 0.0
        delta = f" (Δ {diff:+,.0f}, {pct:+.1f}%)"

    payload = {
        "title": f"PyScrapr Price Alert: {product.title or product.url[:60]}",
        "description": f"{fired_reason}{delta}",
        "color": 0x22c55e if (product.alert_below and new_price < product.alert_below) else 0xef4444,
        "fields": [
            {"name": "Harga sekarang", "value": f"{new_price:,.0f} {product.currency}", "inline": True},
            {"name": "Harga sebelumnya", "value": (
                f"{prev_price:,.0f} {product.currency}" if prev_price is not None else "—"
            ), "inline": True},
            {"name": "URL", "value": product.url[:500], "inline": False},
        ],
    }
    try:
        await notify(payload)
    except Exception as e:
        logger.warning("Price alert webhook failed for %s: %s", product.id, e)


async def run_check(product_id: str) -> dict[str, Any]:
    """Fetch + extract + persist history + update product + fire alerts."""
    async with AsyncSessionLocal() as session:
        repo = PriceRepository(session)
        product = await repo.get_product(product_id)
        if not product:
            return {"ok": False, "error": "product not found"}

        prev_price = product.last_price
        result = await check_product(product)
        now = datetime.utcnow()

        product.last_checked_at = now
        product.last_status = result["status"]
        product.last_error = result.get("error")
        if result["price"] is not None:
            product.last_price = result["price"]

        # Always record a history entry (price=0 for non-ok so chart can show gaps)
        await repo.add_history(
            product_id=product.id,
            price=result["price"] if result["price"] is not None else 0.0,
            status=result["status"],
            raw_text=result.get("raw_text"),
        )
        await session.commit()

        if result["status"] == "ok" and result["price"] is not None:
            await _maybe_alert(product, result["price"], prev_price)

        return {
            "ok": True,
            "product_id": product.id,
            "price": result["price"],
            "status": result["status"],
            "error": result.get("error"),
            "checked_at": now.isoformat(),
        }


async def check_all_due() -> dict[str, Any]:
    """Iterate enabled products whose interval has elapsed, run checks sequentially."""
    async with AsyncSessionLocal() as session:
        repo = PriceRepository(session)
        due = await repo.list_enabled_due()
        ids = [p.id for p in due]

    checked = 0
    errors = 0
    for pid in ids:
        try:
            r = await run_check(pid)
            if r.get("status") == "ok":
                checked += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            logger.exception("Price check failed for %s: %s", pid, e)
        await asyncio.sleep(0.5)  # gentle pacing across different domains
    return {"checked": checked, "errors": errors, "total_due": len(ids)}


# ───── scheduler integration ─────

_SCHEDULER_JOB_ID = "price_watcher_loop"


def register_scheduler() -> None:
    """Register a recurring APScheduler job that fires check_all_due() every 5 minutes."""
    try:
        from apscheduler.triggers.interval import IntervalTrigger

        from app.services.scheduler import get_scheduler
    except Exception as e:
        logger.warning("Could not register price watcher scheduler: %s", e)
        return

    sched = get_scheduler()
    try:
        sched.add_job(
            check_all_due,
            trigger=IntervalTrigger(minutes=5),
            id=_SCHEDULER_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Price watcher scheduler registered (every 5 minutes)")
    except Exception as e:
        logger.warning("Failed to register price watcher job: %s", e)
