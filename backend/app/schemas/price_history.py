"""Price History Schemas."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class PricePoint(BaseModel):
    date: str
    price: float
    currency: str = "INR"
    retailer: str


class PriceSummary(BaseModel):
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None
    historical_low: Optional[float] = None
    historical_high: Optional[float] = None
    price_change: Optional[float] = None
    price_change_percentage: Optional[float] = None
    currency: str = "INR"
    observations_count: int = 0
    price_position: str = "typical"  # great_deal | below_average | typical | above_average


class PriceHistoryResponse(BaseModel):
    product_id: str
    summary: PriceSummary
    history: List[PricePoint] = []
