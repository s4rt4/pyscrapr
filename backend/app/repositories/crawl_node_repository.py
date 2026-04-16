"""Data access for crawl_nodes."""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_node import CrawlNode


class CrawlNodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, node: CrawlNode) -> CrawlNode:
        self.session.add(node)
        await self.session.flush()
        return node

    async def find_by_url(self, job_id: str, url: str) -> Optional[CrawlNode]:
        stmt = select(CrawlNode).where(
            CrawlNode.job_id == job_id, CrawlNode.url == url
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, job_id: str, url: str) -> bool:
        node = await self.find_by_url(job_id, url)
        return node is not None

    async def list_for_job(self, job_id: str, limit: int = 20000) -> list[CrawlNode]:
        stmt = (
            select(CrawlNode)
            .where(CrawlNode.job_id == job_id)
            .order_by(CrawlNode.depth, CrawlNode.id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, job_id: str) -> int:
        stmt = select(func.count()).select_from(CrawlNode).where(CrawlNode.job_id == job_id)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def count_broken(self, job_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(CrawlNode)
            .where(CrawlNode.job_id == job_id, CrawlNode.status_code >= 400)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def avg_response_ms(self, job_id: str) -> int:
        stmt = (
            select(func.avg(CrawlNode.response_ms))
            .where(CrawlNode.job_id == job_id, CrawlNode.response_ms.is_not(None))
        )
        result = await self.session.execute(stmt)
        val = result.scalar()
        return int(val) if val else 0
