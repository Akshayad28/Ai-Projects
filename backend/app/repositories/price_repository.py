"""Price History Repository."""
from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.price_history import PriceHistory


class PriceRepository:
    """Database persistence for price observations."""

    async def get_history(self, db: AsyncSession, product_id: str) -> List[PriceHistory]:
        q = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.captured_at.asc())
        )
        res = await db.execute(q)
        return list(res.scalars().all())

    async def add_observation(self, db: AsyncSession, observation: PriceHistory) -> PriceHistory:
        db.add(observation)
        await db.commit()
        await db.refresh(observation)
        return observation
