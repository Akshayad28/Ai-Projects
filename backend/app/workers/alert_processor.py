"""Price Alert Processor Background Worker."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from app.core.logging import get_logger
from app.database.connection import SessionLocal
from app.db.models import Notification, PriceAlert
from app.models.offer import Offer

log = get_logger(__name__)


async def process_price_alerts() -> int:
    """Evaluates active price alerts against real observed prices."""
    triggered_count = 0
    async with SessionLocal() as db:
        q = select(PriceAlert).where(PriceAlert.active == True)
        res = await db.execute(q)
        alerts = list(res.scalars().all())

        for alert in alerts:
            # Check best available price
            q_offer = (
                select(Offer)
                .where(Offer.product_id == alert.product_id)
                .order_by(Offer.price_amount.asc())
                .limit(1)
            )
            offer_res = await db.execute(q_offer)
            best_offer = offer_res.scalar_one_or_none()

            if best_offer and best_offer.price_amount:
                # Target price condition
                if alert.target_price and best_offer.price_amount <= alert.target_price:
                    notification = Notification(
                        user_id=alert.user_id,
                        kind="price_drop",
                        title=f"Price Alert Triggered: ₹{best_offer.price_amount:,.2f}",
                        body=f"Your target price of ₹{alert.target_price:,.2f} has been reached on {best_offer.retailer_name}!",
                        product_id=alert.product_id,
                    )
                    db.add(notification)
                    alert.last_triggered_at = datetime.now(timezone.utc)
                    triggered_count += 1

            alert.last_evaluated_at = datetime.now(timezone.utc)

        await db.commit()
    log.info(f"Price alert processing complete. Triggered {triggered_count} alerts.")
    return triggered_count
