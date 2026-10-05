"""Review Repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.review import Review, ReviewAnalysis


class ReviewRepository:
    """Database persistence for customer reviews and generated analyses."""

    async def get_reviews(self, db: AsyncSession, product_id: str, limit: int = 50) -> List[Review]:
        q = select(Review).where(Review.product_id == product_id).limit(limit)
        res = await db.execute(q)
        return list(res.scalars().all())

    async def get_analysis(self, db: AsyncSession, product_id: str) -> Optional[ReviewAnalysis]:
        q = select(ReviewAnalysis).where(ReviewAnalysis.product_id == product_id)
        res = await db.execute(q)
        return res.scalar_one_or_none()
