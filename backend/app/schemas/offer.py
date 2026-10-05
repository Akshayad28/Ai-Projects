"""Offer Schemas."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class TrueCostBreakdown(BaseModel):
    price: float
    shipping: Optional[float] = None
    tax: Optional[float] = None
    discounts: Optional[float] = None
    true_cost: Optional[float] = None
    status: str = "INCOMPLETE"  # COMPLETE | INCOMPLETE


class OfferSchema(BaseModel):
    id: Optional[int] = None
    product_id: str
    retailer: str
    seller: Optional[str] = None
    seller_rating: Optional[float] = None
    url: Optional[str] = None
    price: Optional[float] = None
    price_amount: Optional[float] = None
    currency: str = "INR"
    original_price: Optional[float] = None
    discount: Optional[float] = None
    shipping_cost: Optional[float] = None
    tax: Optional[float] = None
    final_price: Optional[float] = None
    availability: str = "unknown"  # IN_STOCK | LOW_STOCK | OUT_OF_STOCK | PREORDER | UNKNOWN
    condition: str = "new"
    delivery_estimate: Optional[str] = None
    delivery_eta_minutes: Optional[int] = None
    delivery_window: Optional[str] = None
    is_quick_commerce: bool = False
    delivery_fee: Optional[float] = None
    platform_fee: Optional[float] = None
    handling_fee: Optional[float] = None
    surge_fee: Optional[float] = None
    pack_size: Optional[str] = None
    unit_price: Optional[float] = None
    unit_measure: Optional[str] = None
    store_name: Optional[str] = None
    location_checked: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None
    source: str = "unknown"
    fetched_at: str = "Just now"
    freshness_label: Optional[str] = None
    true_cost: Optional[TrueCostBreakdown] = None

    def model_post_init(self, __context: Any) -> None:
        if self.price_amount is None and self.price is not None:
            self.price_amount = self.price
        elif self.price is None and self.price_amount is not None:
            self.price = self.price_amount
        if self.final_price is None and self.price is not None:
            self.final_price = self.price

