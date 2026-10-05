"""Offer Repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.offer import Offer


class OfferRepository:
    """Database persistence for retailer offers."""

    async def get_by_product_id(self, db: AsyncSession, product_id: str) -> List[Offer]:
        q = select(Offer).where(Offer.product_id == product_id)
        res = await db.execute(q)
        return list(res.scalars().all())

    async def save(self, db: AsyncSession, offer: Offer) -> Offer:
        db.add(offer)
        await db.commit()
        await db.refresh(offer)
        return offer
