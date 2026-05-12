"""Comment Harvester (P11).

Detect platform from URL and pull a comment tree (parent + recursive replies)
from YouTube / Reddit / generic forum HTML. Optionally annotate sentiment via
Ollama. Designed to be called from api/comment.py inside a background task
that publishes progress events through event_bus.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.event_bus import event_bus
from app.services.http_factory import build_client

logger = logging.getLogger("pyscrapr.comment_harvester")


# ───────────────────────── helpers ─────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_platform(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return "unknown"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "reddit.com" in host:
        return "reddit"
    if not host:
        return "unknown"
    return "forum"


def _ts_from_unix(value: Any) -> Optional[str]:
    try:
        ts = float(value)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _count_tree(nodes: list[dict]) -> tuple[int, int, int]:
    """Return (total_comments, total_replies, max_depth)."""
    total = 0
    replies = 0
    max_depth = 0

    def _walk(items: list[dict], depth: int) -> None:
        nonlocal total, replies, max_depth
        max_depth = max(max_depth, depth)
        for it in items:
            total += 1
            if depth > 0:
                replies += 1
            kids = it.get("replies") or []
            if kids:
                _walk(kids, depth + 1)

    _walk(nodes, 0)
    return total, replies, max_depth


# ───────────────────────── YouTube ─────────────────────────


async def _harvest_youtube(
    url: str,
    *,
    max_comments: int,
    include_replies: bool,
    job_id: Optional[str],
) -> dict:
    """Extract YouTube comments via yt-dlp."""

    def _run() -> dict:
        import yt_dlp  # local import; yt-dlp is heavy

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "getcomments": True,
            "extractor_args": {
                "youtube": {
                    "max_comments": [str(max_comments), str(max_comments), "all", "all"]
                    if include_replies
                    else [str(max_comments), str(max_comments), "0", "0"],
                    "comment_sort": ["top"],
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info or {}

    try:
        info = await asyncio.to_thread(_run)
    except Exception as e:
        logger.warning("yt-dlp failed for %s: %s", url, e)
        return {
            "platform": "youtube",
            "title": None,
            "comments": [],
            "error": str(e),
        }

    raw = info.get("comments") or []
    title = info.get("title")

    # yt-dlp returns flat list of comments with `parent` field referencing parent id.
    by_id: dict[str, dict] = {}
    roots: list[dict] = []
    for c in raw:
        cid = str(c.get("id") or "")
        if not cid:
            continue
        node = {
            "id": cid,
            "author": c.get("author"),
            "text": c.get("text") or "",
            "timestamp": _ts_from_unix(c.get("timestamp")),
            "upvotes": c.get("like_count"),
            "depth": 0,
            "sentiment": None,
            "replies": [],
        }
        by_id[cid] = node

    for c in raw:
        cid = str(c.get("id") or "")
        if not cid or cid not in by_id:
            continue
        parent = c.get("parent")
        if parent and parent != "root" and parent in by_id and include_replies:
            by_id[parent]["replies"].append(by_id[cid])
        else:
            roots.append(by_id[cid])

    # Assign depth
    def _set_depth(node: dict, depth: int) -> None:
        node["depth"] = depth
        for r in node["replies"]:
            _set_depth(r, depth + 1)

    for r in roots:
        _set_depth(r, 0)

    # Truncate flat count
    if max_comments and len(roots) > max_comments:
        roots = roots[:max_comments]

    if job_id:
        await event_bus.publish(
            job_id,
            {"type": "log", "message": f"YouTube comments extracted: {len(raw)} raw, {len(roots)} top-level"},
        )

    return {"platform": "youtube", "title": title, "comments": roots}


# ───────────────────────── Reddit ─────────────────────────


def _parse_reddit_listing(listing: dict, include_replies: bool, depth: int = 0) -> list[dict]:
    out: list[dict] = []
    children = (listing.get("data") or {}).get("children") or []
    for ch in children:
        kind = ch.get("kind")
        data = ch.get("data") or {}
        if kind != "t1":
            continue
        node = {
            "id": str(data.get("id") or data.get("name") or ""),
            "author": data.get("author"),
            "text": data.get("body") or "",
            "timestamp": _ts_from_unix(data.get("created_utc")),
            "upvotes": data.get("ups"),
            "depth": depth,
            "sentiment": None,
            "replies": [],
        }
        if include_replies:
            replies_field = data.get("replies")
            if isinstance(replies_field, dict):
                node["replies"] = _parse_reddit_listing(replies_field, include_replies, depth + 1)
        out.append(node)
    return out


async def _harvest_reddit(
    url: str,
    *,
    max_comments: int,
    include_replies: bool,
    job_id: Optional[str],
) -> dict:
    """Reddit public JSON API: append .json to thread URL."""
    json_url = url.split("?", 1)[0].rstrip("/") + ".json?limit=500&depth=10&raw_json=1"
    title: Optional[str] = None
    comments: list[dict] = []

    async with build_client(timeout=30, target_url=url) as client:
        try:
            resp = await client.get(
                json_url,
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.warning("Reddit JSON returned HTTP %s for %s", resp.status_code, json_url)
                return {
                    "platform": "reddit",
                    "title": None,
                    "comments": [],
                    "error": f"HTTP {resp.status_code}",
                }
            data = resp.json()
        except Exception as e:
            logger.warning("Reddit fetch failed: %s", e)
            return {"platform": "reddit", "title": None, "comments": [], "error": str(e)}

    if isinstance(data, list) and len(data) >= 2:
        # data[0] = post listing, data[1] = comments listing
        post_children = ((data[0] or {}).get("data") or {}).get("children") or []
        if post_children:
            title = ((post_children[0] or {}).get("data") or {}).get("title")
        comments = _parse_reddit_listing(data[1], include_replies, depth=0)

    # Flat-truncate top-level
    if max_comments and len(comments) > max_comments:
        comments = comments[:max_comments]

    if job_id:
        await event_bus.publish(
            job_id,
            {"type": "log", "message": f"Reddit thread parsed: {len(comments)} top-level comments"},
        )

    return {"platform": "reddit", "title": title, "comments": comments}


# ───────────────────────── Generic forum ─────────────────────────


# Common selectors used across vBulletin / phpBB / Discourse / Disqus-embed
_FORUM_POST_SELECTORS = [
    ("div.post", "div.username, .author, a.username", ".post-content, .content, .postcontent"),
    ("article.post", ".username, .author", ".post-body, .content"),
    ("li.post", ".username, .author", ".post-text, .content"),
    ("div.message", ".message-userDetails .username", ".message-body, .bbWrapper"),  # XenForo
    ("div.topic-post", ".topic-meta-data .username", ".cooked"),  # Discourse
    ("div.comment", ".comment-author, .author", ".comment-body, .comment-content"),
]


async def _harvest_forum(
    url: str,
    *,
    max_comments: int,
    include_replies: bool,
    job_id: Optional[str],
) -> dict:
    """Best-effort HTML scrape for generic forum / blog comments.

    Forums rarely encode nesting consistently, so this returns a flat list
    (depth=0). include_replies is ignored for the generic path.
    """
    async with build_client(timeout=30, target_url=url) as client:
        try:
            resp = await client.get(url)
            html = resp.text
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else None
        except Exception as e:
            logger.warning("Forum fetch failed: %s", e)
            return {"platform": "forum", "title": None, "comments": [], "error": str(e)}

    soup = BeautifulSoup(html, "html.parser")
    comments: list[dict] = []

    for post_sel, author_sel, body_sel in _FORUM_POST_SELECTORS:
        posts = soup.select(post_sel)
        if len(posts) < 2:
            continue
        for idx, p in enumerate(posts):
            if len(comments) >= max_comments:
                break
            author_el = p.select_one(author_sel)
            body_el = p.select_one(body_sel)
            text = (body_el.get_text(" ", strip=True) if body_el else p.get_text(" ", strip=True))
            text = text[:5000]
            if not text:
                continue
            comments.append({
                "id": p.get("id") or f"post-{idx}",
                "author": (author_el.get_text(strip=True) if author_el else None),
                "text": text,
                "timestamp": None,
                "upvotes": None,
                "depth": 0,
                "sentiment": None,
                "replies": [],
            })
        if comments:
            break

    if job_id:
        await event_bus.publish(
            job_id,
            {"type": "log", "message": f"Forum heuristic parse: {len(comments)} comments found"},
        )

    return {"platform": "forum", "title": title, "comments": comments}


# ───────────────────────── main entrypoint ─────────────────────────


async def harvest(
    url: str,
    *,
    max_comments: int = 500,
    include_replies: bool = True,
    sentiment: bool = False,
    job_id: Optional[str] = None,
) -> dict:
    """Harvest comments from a URL. Returns a dict shaped like CommentHarvestReport."""
    platform = _detect_platform(url)
    if job_id:
        await event_bus.publish(
            job_id,
            {"type": "log", "message": f"Platform terdeteksi: {platform}"},
        )

    if platform == "youtube":
        result = await _harvest_youtube(
            url, max_comments=max_comments, include_replies=include_replies, job_id=job_id
        )
    elif platform == "reddit":
        result = await _harvest_reddit(
            url, max_comments=max_comments, include_replies=include_replies, job_id=job_id
        )
    elif platform == "forum":
        result = await _harvest_forum(
            url, max_comments=max_comments, include_replies=include_replies, job_id=job_id
        )
    else:
        result = {"platform": "unknown", "title": None, "comments": [], "error": "URL tidak dikenali"}

    comments = result.get("comments") or []
    total, replies, max_depth = _count_tree(comments)
    sentiment_summary: Optional[dict] = None

    if sentiment and comments:
        if job_id:
            await event_bus.publish(
                job_id,
                {"type": "log", "message": f"Menjalankan analisis sentimen ({total} komentar)..."},
            )
        try:
            from app.services.comment_sentiment import annotate_tree

            sentiment_summary = await annotate_tree(comments, job_id=job_id)
        except Exception as e:
            logger.warning("Sentiment annotation failed: %s", e)
            if job_id:
                await event_bus.publish(
                    job_id,
                    {"type": "log", "message": f"Sentimen gagal: {e}"},
                )

    report = {
        "url": url,
        "platform": result.get("platform", platform),
        "title": result.get("title"),
        "fetched_at": _now_iso(),
        "total_comments": total,
        "total_replies": replies,
        "max_depth": max_depth,
        "sentiment_summary": sentiment_summary,
        "comments": comments,
    }

    if job_id:
        await event_bus.publish(
            job_id,
            {
                "type": "done",
                "total_comments": total,
                "total_replies": replies,
                "max_depth": max_depth,
            },
        )

    return report
