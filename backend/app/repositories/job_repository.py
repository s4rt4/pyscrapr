"""Data access layer for Job — keeps SQL out of services."""
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, JobType


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.flush()
        return job

    async def find_by_id(self, job_id: str) -> Optional[Job]:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_recent(
        self, limit: int = 30, job_type: Optional[JobType] = None
    ) -> list[Job]:
        stmt = select(Job).order_by(desc(Job.created_at)).limit(limit)
        if job_type is not None:
            stmt = stmt.where(Job.type == job_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
    ) -> None:
        job = await self.find_by_id(job_id)
        if job:
            job.status = status
            if error is not None:
                job.error_message = error

    async def update_stats(self, job_id: str, stats: dict) -> None:
        job = await self.find_by_id(job_id)
        if job:
            job.stats = stats
