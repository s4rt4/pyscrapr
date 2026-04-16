"""Data access for crawl_frontier — persistent BFS queue for pause/resume."""
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_frontier import CrawlFrontier


class CrawlFrontierRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, job_id: str, url: str, depth: int, parent_node_id: Optional[int]
    ) -> bool:
        """Insert-or-ignore on (job_id, url) unique index.

        Returns True if the row was inserted, False if a duplicate was ignored.
        Uses SQLite's native ON CONFLICT DO NOTHING so we don't poison the
        session transaction with a failed INSERT.
        """
        stmt = (
            sqlite_insert(CrawlFrontier)
            .values(
                job_id=job_id,
                url=url,
                depth=depth,
                parent_node_id=parent_node_id,
            )
            .on_conflict_do_nothing(index_elements=["job_id", "url"])
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def pop_batch(self, job_id: str, limit: int = 10) -> list[CrawlFrontier]:
        """Fetch next batch and remove from queue atomically."""
        stmt = (
            select(CrawlFrontier)
            .where(CrawlFrontier.job_id == job_id)
            .order_by(CrawlFrontier.depth, CrawlFrontier.id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        for item in items:
            await self.session.delete(item)
        await self.session.flush()
        return items

    async def size(self, job_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(CrawlFrontier)
            .where(CrawlFrontier.job_id == job_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def clear(self, job_id: str) -> None:
        stmt = delete(CrawlFrontier).where(CrawlFrontier.job_id == job_id)
        await self.session.execute(stmt)
