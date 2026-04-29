"""Data access for HashReputationCache.

Self-contained repository that uses AsyncSessionLocal directly so
service-layer callers (hash_reputation.py) do not need to thread a
session through. Negative cache entries expire after NEGATIVE_TTL_DAYS;
positive hits are cached forever because file-hash -> reputation is
an immutable association.
"""
from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Optional

from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models.hash_reputation_cache import HashReputationCache

logger = logging.getLogger("pyscrapr.hash_reputation")

NEGATIVE_TTL_DAYS = 7


class HashRepCacheRepo:
    async def get(self, sha256: str, source: str) -> Optional[dict[str, Any]]:
        """Return cached payload or None if missing / stale.

        Positive hits (found=True) are returned forever. Negative hits
        (found=False) are treated as a miss once older than NEGATIVE_TTL_DAYS.
        """
        if not sha256 or not source:
            return None
        async with AsyncSessionLocal() as session:
            stmt = select(HashReputationCache).where(
                HashReputationCache.sha256 == sha256,
                HashReputationCache.source == source,
            )
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if entry is None:
                return None
            if not entry.found:
                age = _dt.datetime.utcnow() - entry.fetched_at
                if age > _dt.timedelta(days=NEGATIVE_TTL_DAYS):
                    return None
            payload = dict(entry.payload or {})
            return payload

    async def save(
        self, sha256: str, source: str, payload: dict[str, Any], found: bool
    ) -> None:
        """Upsert: delete any existing row for (sha256, source) then insert."""
        if not sha256 or not source:
            return
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    delete(HashReputationCache).where(
                        HashReputationCache.sha256 == sha256,
                        HashReputationCache.source == source,
                    )
                )
                entry = HashReputationCache(
                    sha256=sha256,
                    source=source,
                    found=bool(found),
                    payload=payload or {},
                    fetched_at=_dt.datetime.utcnow(),
                )
                session.add(entry)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.warning("hash reputation cache save gagal: %s", e)

    async def stats(self) -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            total_stmt = select(func.count(HashReputationCache.id))
            pos_stmt = select(func.count(HashReputationCache.id)).where(
                HashReputationCache.found == True  # noqa: E712
            )
            neg_stmt = select(func.count(HashReputationCache.id)).where(
                HashReputationCache.found == False  # noqa: E712
            )
            vt_stmt = select(func.count(HashReputationCache.id)).where(
                HashReputationCache.source == "vt"
            )
            mb_stmt = select(func.count(HashReputationCache.id)).where(
                HashReputationCache.source == "mb"
            )
            total = (await session.execute(total_stmt)).scalar_one()
            positive = (await session.execute(pos_stmt)).scalar_one()
            negative = (await session.execute(neg_stmt)).scalar_one()
            vt = (await session.execute(vt_stmt)).scalar_one()
            mb = (await session.execute(mb_stmt)).scalar_one()
            return {
                "total_entries": int(total or 0),
                "positive_count": int(positive or 0),
                "negative_count": int(negative or 0),
                "vt_count": int(vt or 0),
                "mb_count": int(mb or 0),
            }

    async def clear_all(self) -> int:
        async with AsyncSessionLocal() as session:
            try:
                count_stmt = select(func.count(HashReputationCache.id))
                count = (await session.execute(count_stmt)).scalar_one()
                await session.execute(delete(HashReputationCache))
                await session.commit()
                return int(count or 0)
            except Exception as e:
                await session.rollback()
                logger.warning("hash reputation cache clear gagal: %s", e)
                return 0
