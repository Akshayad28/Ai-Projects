"""Availability Refresh Background Worker."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from app.core.logging import get_logger
from app.database.connection import SessionLocal
from app.models.availability_history import AvailabilityHistory
from app.models.offer import Offer

log = get_logger(__name__)


async def refresh_availability(offer_id: int) -> None:
    """Verifies stock status for an offer and records historical observation."""
    async with SessionLocal() as db:
        q = select(Offer).where(Offer.id == offer_id)
        res = await db.execute(q)
        offer = res.scalar_one_or_none()

        if offer:
            rec = AvailabilityHistory(
                offer_id=offer.id,
                status=offer.availability or "UNKNOWN",
            )
            db.add(rec)
            offer.last_checked_at = datetime.now(timezone.utc)
            await db.commit()
            log.info(f"Availability recorded for offer {offer_id}: {offer.availability}")
