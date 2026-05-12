"""Comment sentiment scoring via Ollama (P11).

Lazy + opt-in. Caches results by text hash in a process-local dict so repeat
scans of the same thread do not re-call Ollama. Batches ~10 comments per LLM
call to amortize per-request overhead.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

from app.services.event_bus import event_bus
from app.services.llm_client import chat_completion
from app.services.settings_store import get as get_setting

logger = logging.getLogger("pyscrapr.comment_sentiment")

_CACHE: dict[str, dict] = {}
_BATCH_SIZE = 10
_VALID_LABELS = {"positive", "neutral", "negative"}


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


def _truncate(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


async def _score_batch(texts: list[str]) -> list[dict]:
    """Score a batch of comments. Returns list of {label, confidence} in same order."""
    if not texts:
        return []

    provider = (get_setting("llm_provider", "ollama") or "ollama").lower()
    api_key = (
        get_setting("deepseek_api_key", "")
        if provider == "deepseek"
        else get_setting("openai_api_key", "")
        if provider == "openai"
        else ""
    )

    numbered = "\n".join(f"{i + 1}. {_truncate(t)}" for i, t in enumerate(texts))
    system = (
        "You score short comments for sentiment. Reply with ONLY JSON in the form "
        '{"results":[{"i":1,"label":"positive|neutral|negative","confidence":0..1}, ...]}. '
        "No prose."
    )
    user = f"Score sentiment of these comments:\n{numbered}\nReturn JSON now."

    try:
        result = await chat_completion(
            provider=provider,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_key=api_key or "",
            max_tokens=400,
            temperature=0.0,
            timeout=60,
        )
        content = (result or {}).get("content", "")
    except Exception as e:
        logger.warning("Sentiment batch call failed: %s", e)
        return [{"label": "neutral", "confidence": 0.0} for _ in texts]

    # Strip markdown fences if any
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    parsed_results: list[dict] = []
    try:
        data = json.loads(content)
        for r in (data.get("results") or []):
            label = str(r.get("label", "neutral")).lower()
            if label not in _VALID_LABELS:
                label = "neutral"
            try:
                conf = float(r.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            parsed_results.append({"label": label, "confidence": max(0.0, min(1.0, conf))})
    except json.JSONDecodeError:
        logger.warning("Sentiment JSON parse failed: %s", content[:200])

    # Pad/truncate to match input length
    while len(parsed_results) < len(texts):
        parsed_results.append({"label": "neutral", "confidence": 0.0})
    return parsed_results[: len(texts)]


async def score_comment(text: str) -> dict:
    """Score a single comment. Cached by text hash."""
    h = _hash(text)
    if h in _CACHE:
        return _CACHE[h]
    out = await _score_batch([text])
    res = out[0] if out else {"label": "neutral", "confidence": 0.0}
    _CACHE[h] = res
    return res


async def annotate_tree(nodes: list[dict], job_id: Optional[str] = None) -> dict:
    """Walk the comment tree, fill node['sentiment'] for each, return summary counts."""
    summary = {"positive": 0, "neutral": 0, "negative": 0}

    # Flatten to a list of (node, text) pairs that still need scoring
    pending: list[tuple[dict, str]] = []

    def _walk(items: list[dict]) -> None:
        for it in items:
            txt = it.get("text") or ""
            if not txt.strip():
                it["sentiment"] = {"label": "neutral", "confidence": 0.0}
                summary["neutral"] += 1
                continue
            h = _hash(txt)
            if h in _CACHE:
                it["sentiment"] = _CACHE[h]
                summary[_CACHE[h]["label"]] = summary.get(_CACHE[h]["label"], 0) + 1
            else:
                pending.append((it, txt))
            kids = it.get("replies") or []
            if kids:
                _walk(kids)

    _walk(nodes)

    total_pending = len(pending)
    if not total_pending:
        return summary

    processed = 0
    for i in range(0, total_pending, _BATCH_SIZE):
        batch = pending[i : i + _BATCH_SIZE]
        texts = [t for _, t in batch]
        results = await _score_batch(texts)
        for (node, txt), score in zip(batch, results):
            node["sentiment"] = score
            _CACHE[_hash(txt)] = score
            summary[score["label"]] = summary.get(score["label"], 0) + 1
        processed += len(batch)
        if job_id:
            await event_bus.publish(
                job_id,
                {
                    "type": "progress",
                    "stage": "sentiment",
                    "processed": processed,
                    "total": total_pending,
                },
            )

    return summary
