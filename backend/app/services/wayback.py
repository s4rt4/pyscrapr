"""Wayback Machine (web.archive.org) integration.

Uses the public CDX API for snapshot listing, the /save/ endpoint for
on-demand archiving, and the id_ mode (identity) for fetching raw snapshot
content without the Wayback toolbar injection.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.wayback")

CDX_API = "https://web.archive.org/cdx/search/cdx"
SAVE_API = "https://web.archive.org/save/"
SNAPSHOT_FMT = "https://web.archive.org/web/{ts}/{url}"
SNAPSHOT_RAW_FMT = "https://web.archive.org/web/{ts}id_/{url}"


async def list_snapshots(
    url: str,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Query CDX API for historical snapshots of ``url``."""
    params: dict[str, Any] = {
        "url": url,
        "output": "json",
        "limit": max(1, min(int(limit or 200), 10000)),
    }
    if from_year:
        params["from"] = f"{int(from_year)}0101"
    if to_year:
        params["to"] = f"{int(to_year)}1231"

    async with build_client(timeout=30) as client:
        try:
            resp = await client.get(CDX_API, params=params)
        except httpx.HTTPError as e:
            logger.warning("CDX fetch failed for %s: %s", url, e)
            raise
    if resp.status_code != 200:
        raise RuntimeError(f"CDX returned status {resp.status_code}")

    try:
        rows = resp.json()
    except Exception as e:
        raise RuntimeError(f"CDX bad json: {e}")

    if not isinstance(rows, list) or len(rows) < 2:
        return []

    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}

    def g(row, key, default=""):
        i = idx.get(key)
        return row[i] if i is not None and i < len(row) else default

    out: list[dict[str, Any]] = []
    for row in rows[1:]:
        ts = g(row, "timestamp")
        original = g(row, "original")
        out.append({
            "timestamp": ts,
            "url": original,
            "status": g(row, "statuscode"),
            "digest": g(row, "digest"),
            "length": g(row, "length"),
            "mimetype": g(row, "mimetype"),
            "snapshot_url": SNAPSHOT_FMT.format(ts=ts, url=original),
        })
    return out


async def save_now(url: str) -> dict[str, Any]:
    """Submit URL to Wayback. Returns {saved, timestamp, snapshot_url}."""
    target = SAVE_API + url
    async with build_client(timeout=60) as client:
        try:
            resp = await client.get(target)
        except httpx.HTTPError as e:
            logger.warning("Wayback save failed for %s: %s", url, e)
            return {"saved": False, "error": str(e)}

    final_url = str(resp.url)
    # Expected shape: https://web.archive.org/web/<timestamp>/<original>
    ts = None
    if "/web/" in final_url:
        try:
            part = final_url.split("/web/", 1)[1]
            ts_candidate = part.split("/", 1)[0]
            if ts_candidate.isdigit() and 8 <= len(ts_candidate) <= 14:
                ts = ts_candidate
        except Exception:
            pass

    # Content-Location header also often carries the snapshot path
    if not ts:
        cl = resp.headers.get("content-location") or resp.headers.get("Content-Location")
        if cl and "/web/" in cl:
            try:
                ts_candidate = cl.split("/web/", 1)[1].split("/", 1)[0]
                if ts_candidate.isdigit():
                    ts = ts_candidate
            except Exception:
                pass

    if not ts:
        return {
            "saved": False,
            "status_code": resp.status_code,
            "final_url": final_url,
            "error": "could not extract timestamp from response",
        }

    return {
        "saved": True,
        "timestamp": ts,
        "snapshot_url": SNAPSHOT_FMT.format(ts=ts, url=url),
        "status_code": resp.status_code,
    }


async def get_snapshot_content(url: str, timestamp: str) -> str:
    """Fetch raw snapshot content using id_ (identity) mode."""
    target = SNAPSHOT_RAW_FMT.format(ts=timestamp, url=url)
    async with build_client(timeout=30) as client:
        resp = await client.get(target)
    if resp.status_code >= 400:
        raise RuntimeError(f"snapshot fetch status {resp.status_code}")
    return resp.text
