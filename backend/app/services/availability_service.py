"""Availability Service.

Tracks stock availability across retailer offers.
Valid statuses: IN_STOCK, LOW_STOCK, OUT_OF_STOCK, PREORDER, UNKNOWN.
Never assumes stock availability.
"""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability_history import AvailabilityHistory


class AvailabilityService:
    """Records and retrieves retailer offer availability trends."""

    async def record_status(
        self,
        db: AsyncSession,
        offer_id: int,
        status: str,
    ) -> AvailabilityHistory:
        normalized_status = status.upper()
        if normalized_status not in {"IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK", "PREORDER", "UNKNOWN"}:
            normalized_status = "UNKNOWN"

        rec = AvailabilityHistory(
            offer_id=offer_id,
            status=normalized_status,
        )
        db.add(rec)
        return rec

    async def get_latest_status(self, db: AsyncSession, offer_id: int) -> str:
        q = (
            select(AvailabilityHistory)
            .where(AvailabilityHistory.offer_id == offer_id)
            .order_by(AvailabilityHistory.captured_at.desc())
            .limit(1)
        )
        res = await db.execute(q)
        latest = res.scalar_one_or_none()
        return latest.status if latest else "UNKNOWN"
