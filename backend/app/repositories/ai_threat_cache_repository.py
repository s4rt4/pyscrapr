"""Data access for AIThreatCache."""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_threat_cache import AIThreatCache


class AIThreatCacheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_hash(self, file_hash: str) -> Optional[AIThreatCache]:
        if not file_hash:
            return None
        result = await self.session.execute(
            select(AIThreatCache).where(AIThreatCache.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        file_hash: str,
        risk_score: int,
        analysis: str,
        model_used: str,
        tokens_used: int,
        cost_usd: float,
        filename: Optional[str] = None,
    ) -> AIThreatCache:
        entry = AIThreatCache(
            file_hash=file_hash,
            filename=filename,
            risk_score=risk_score,
            analysis=analysis,
            model_used=model_used,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_recent(self, days: int = 30, limit: int = 100) -> list[AIThreatCache]:
        cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=days)
        stmt = (
            select(AIThreatCache)
            .where(AIThreatCache.created_at >= cutoff)
            .order_by(desc(AIThreatCache.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def usage_stats(self, days: int = 30) -> dict:
        cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=days)
        stmt = select(
            func.count(AIThreatCache.id),
            func.coalesce(func.sum(AIThreatCache.tokens_used), 0),
            func.coalesce(func.sum(AIThreatCache.cost_usd), 0.0),
        ).where(AIThreatCache.created_at >= cutoff)
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "total_calls_30d": int(row[0] or 0),
            "total_tokens_30d": int(row[1] or 0),
            "total_cost_30d": float(row[2] or 0.0),
        }
