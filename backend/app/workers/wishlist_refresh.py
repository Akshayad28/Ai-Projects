"""Wishlist Refresh Background Worker."""
from __future__ import annotations

from sqlalchemy import select
from app.core.logging import get_logger
from app.database.connection import SessionLocal
from app.db.models import WishlistItem
from app.workers.price_refresh import refresh_product_price

log = get_logger(__name__)


async def refresh_wishlist_items() -> None:
    """Prioritizes price updates for items users have saved in their wishlists."""
    async with SessionLocal() as db:
        q = select(WishlistItem.product_id).distinct()
        res = await db.execute(q)
        product_ids = list(res.scalars().all())

    log.info(f"Refreshing {len(product_ids)} wishlist products")
    for pid in product_ids:
        await refresh_product_price(pid)
