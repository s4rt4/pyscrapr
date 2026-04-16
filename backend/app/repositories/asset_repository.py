"""Data access layer for Asset."""
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetStatus


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def bulk_create(self, assets: list[Asset]) -> None:
        self.session.add_all(assets)
        await self.session.flush()

    async def list_for_job(self, job_id: str, limit: int = 500) -> list[Asset]:
        stmt = (
            select(Asset)
            .where(Asset.job_id == job_id)
            .order_by(desc(Asset.id))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, job_id: str) -> dict[str, int]:
        stmt = (
            select(Asset.status, func.count())
            .where(Asset.job_id == job_id)
            .group_by(Asset.status)
        )
        result = await self.session.execute(stmt)
        return {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in result.all()}

    async def find_by_hash(self, job_id: str, sha1: str) -> Optional[Asset]:
        stmt = select(Asset).where(Asset.job_id == job_id, Asset.sha1 == sha1).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
