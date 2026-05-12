"""Data access for PriceProduct and PriceHistory."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory
from app.models.price_product import PriceProduct


class PriceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ───── PriceProduct CRUD ─────

    async def create_product(self, product: PriceProduct) -> PriceProduct:
        self.session.add(product)
        await self.session.flush()
        return product

    async def get_product(self, product_id: str) -> Optional[PriceProduct]:
        result = await self.session.execute(
            select(PriceProduct).where(PriceProduct.id == product_id)
        )
        return result.scalar_one_or_none()

    async def list_products(self) -> list[PriceProduct]:
        result = await self.session.execute(
            select(PriceProduct).order_by(desc(PriceProduct.created_at))
        )
        return list(result.scalars().all())

    async def list_enabled_due(self, now: Optional[datetime] = None) -> list[PriceProduct]:
        """Return enabled products whose interval has elapsed since last_checked_at."""
        now = now or datetime.utcnow()
        result = await self.session.execute(
            select(PriceProduct).where(PriceProduct.enabled.is_(True))
        )
        out: list[PriceProduct] = []
        for p in result.scalars().all():
            if p.last_checked_at is None:
                out.append(p)
                continue
            elapsed = (now - p.last_checked_at).total_seconds() / 60.0
            if elapsed >= p.interval_minutes:
                out.append(p)
        return out

    async def update_product(self, product: PriceProduct, **fields) -> PriceProduct:
        for key, value in fields.items():
            if hasattr(product, key):
                setattr(product, key, value)
        await self.session.flush()
        return product

    async def delete_product(self, product_id: str) -> bool:
        product = await self.get_product(product_id)
        if not product:
            return False
        await self.session.execute(
            delete(PriceHistory).where(PriceHistory.product_id == product_id)
        )
        await self.session.delete(product)
        await self.session.flush()
        return True

    # ───── PriceHistory ─────

    async def add_history(
        self,
        *,
        product_id: str,
        price: float,
        status: str,
        raw_text: Optional[str] = None,
    ) -> PriceHistory:
        entry = PriceHistory(
            product_id=product_id,
            price=price,
            status=status,
            raw_text=raw_text,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_history(
        self,
        product_id: str,
        limit: int = 500,
        since: Optional[datetime] = None,
    ) -> list[PriceHistory]:
        stmt = select(PriceHistory).where(PriceHistory.product_id == product_id)
        if since is not None:
            stmt = stmt.where(PriceHistory.checked_at >= since)
        stmt = stmt.order_by(PriceHistory.checked_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_price(self, product_id: str) -> Optional[PriceHistory]:
        stmt = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(desc(PriceHistory.checked_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def history_since(self, product_id: str, days: int) -> list[PriceHistory]:
        since = datetime.utcnow() - timedelta(days=days)
        return await self.list_history(product_id=product_id, since=since, limit=5000)
