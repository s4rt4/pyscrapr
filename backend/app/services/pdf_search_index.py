"""Lightweight in-memory full-text index for PDF Harvester jobs.

Keyed by job_id then pdf_id. Substring (case-insensitive) match — good
enough for personal-use scale (hundreds of PDFs, thousands of chars each).
"""
from __future__ import annotations

import threading
from typing import Optional


class PdfSearchIndex:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, str]] = {}

    def add(self, job_id: str, pdf_id: str, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._store.setdefault(job_id, {})[pdf_id] = text

    def clear_job(self, job_id: str) -> None:
        with self._lock:
            self._store.pop(job_id, None)

    def search(
        self, job_id: str, query: str, *, snippet_span: int = 80, limit: int = 100
    ) -> list[dict]:
        """Return list of {pdf_id, snippet, match_count}."""
        if not query or not query.strip():
            return []
        q = query.strip().lower()
        results: list[dict] = []
        with self._lock:
            bucket = dict(self._store.get(job_id) or {})
        for pdf_id, text in bucket.items():
            lower = text.lower()
            idx = lower.find(q)
            if idx < 0:
                continue
            count = lower.count(q)
            a = max(0, idx - snippet_span // 2)
            b = min(len(text), idx + len(q) + snippet_span // 2)
            snippet = text[a:b].replace("\n", " ").strip()
            results.append({
                "pdf_id": pdf_id,
                "snippet": snippet,
                "match_count": count,
            })
            if len(results) >= limit:
                break
        results.sort(key=lambda r: -r["match_count"])
        return results


_index: Optional[PdfSearchIndex] = None


def get_index() -> PdfSearchIndex:
    global _index
    if _index is None:
        _index = PdfSearchIndex()
    return _index
