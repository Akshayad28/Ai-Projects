"""Product Repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductRepository:
    """Database persistence for canonical products."""

    async def get_by_id(self, db: AsyncSession, product_id: str) -> Optional[Product]:
        q = (
            select(Product)
            .options(selectinload(Product.sources), selectinload(Product.offers))
            .where(Product.id == product_id)
        )
        res = await db.execute(q)
        return res.scalar_one_or_none()

    async def get_by_identity_key(self, db: AsyncSession, identity_key: str) -> Optional[Product]:
        q = select(Product).where(Product.identity_key == identity_key)
        res = await db.execute(q)
        return res.scalar_one_or_none()

    async def save(self, db: AsyncSession, product: Product) -> Product:
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product
