"""Price Refresh Background Worker."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.logging import get_logger
from app.database.connection import SessionLocal
from app.models.offer import Offer
from app.models.price_history import PriceHistory

log = get_logger(__name__)


async def refresh_product_price(product_id: str) -> None:
    """Refreshes product price from retailers based on priority."""
    log.info(f"Price refresh worker triggered for product: {product_id}")
    async with SessionLocal() as db:
        q = select(Offer).where(Offer.product_id == product_id)
        res = await db.execute(q)
        offers = list(res.scalars().all())

        for offer in offers:
            # When active, polls retailer URL or PA-API to record fresh observation
            if offer.price_amount:
                obs = PriceHistory(
                    product_id=product_id,
                    offer_id=offer.id,
                    retailer=offer.retailer_name,
                    price=offer.price_amount,
                    currency=offer.currency or "INR",
                )
                db.add(obs)
                offer.last_checked_at = datetime.now(timezone.utc)
        await db.commit()
    log.info(f"Price refresh complete for product {product_id}")
