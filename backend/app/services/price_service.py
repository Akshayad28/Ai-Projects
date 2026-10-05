"""Price Service.

Tracks price observations over time and computes actual historical metrics.
NEVER generates synthetic historical values from assumptions.
Only uses verified stored observations.
"""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory
from app.schemas.price_history import PriceHistoryResponse, PricePoint, PriceSummary


class PriceService:
    """Manages price history records and real-world price trends."""

    async def record_observation(
        self,
        db: AsyncSession,
        product_id: str,
        retailer: str,
        price: float,
        currency: str = "INR",
        offer_id: Optional[int] = None,
    ) -> PriceHistory:
        obs = PriceHistory(
            product_id=product_id,
            retailer=retailer,
            price=price,
            currency=currency,
            offer_id=offer_id,
        )
        db.add(obs)
        return obs

    async def get_price_history(self, db: AsyncSession, product_id: str) -> PriceHistoryResponse:
        q = (
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.captured_at.asc())
        )
        res = await db.execute(q)
        records = list(res.scalars().all())

        if not records:
            return PriceHistoryResponse(
                product_id=product_id,
                summary=PriceSummary(),
                history=[],
            )

        points = [
            PricePoint(
                date=r.captured_at.strftime("%Y-%m-%d"),
                price=r.price,
                currency=r.currency,
                retailer=r.retailer,
            )
            for r in records
        ]

        prices = [r.price for r in records]
        current_price = prices[-1]
        hist_low = min(prices)
        hist_high = max(prices)
        avg = round(sum(prices) / len(prices), 2)

        change = None
        change_pct = None
        if len(prices) > 1:
            first_p = prices[0]
            change = round(current_price - first_p, 2)
            if first_p > 0:
                change_pct = round((change / first_p) * 100, 1)

        position = "typical"
        if current_price <= hist_low:
            position = "great_deal"
        elif current_price < avg:
            position = "below_average"
        elif current_price > avg:
            position = "above_average"

        summary = PriceSummary(
            lowest_price=current_price,
            average_price=avg,
            historical_low=hist_low,
            historical_high=hist_high,
            price_change=change,
            price_change_percentage=change_pct,
            currency=records[0].currency,
            observations_count=len(records),
            price_position=position,
        )

        return PriceHistoryResponse(
            product_id=product_id,
            summary=summary,
            history=points,
        )
