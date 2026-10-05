"""Provider Domain Models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class SearchQuery(BaseModel):
    query: str
    category: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    currency: str = "INR"
    country: str = "IN"
    limit: int = 20
    page: int = 1


class ProviderPrice(BaseModel):
    amount: Optional[float] = None
    currency: str = "INR"
    original_price: Optional[float] = None
    discount: Optional[float] = None


class ProviderOffer(BaseModel):
    retailer: str
    seller: Optional[str] = None
    seller_rating: Optional[float] = None
    url: Optional[str] = None
    price: Optional[float] = None
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
    store_id: Optional[str] = None
    location_checked: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None
    source: str
    fetched_at: str = Field(default_factory=utcnow_str)


class ProviderProduct(BaseModel):
    provider: str
    provider_product_id: str
    title: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    primary_image: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    brand: Optional[str] = None
    model: Optional[str] = None
    price: ProviderPrice = Field(default_factory=ProviderPrice)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    availability: str = "unknown"
    seller: Optional[str] = None
    identifiers: Dict[str, str] = Field(default_factory=dict)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    variant_attributes: Dict[str, str] = Field(default_factory=dict)  # storage, ram, color, size, pack_size
    data_coverage_score: Optional[float] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = False
    fetched_at: str = Field(default_factory=utcnow_str)


class ProviderHealth(BaseModel):
    name: str
    enabled: bool = True
    status: str = "healthy"  # healthy | degraded | blocked | unavailable
    last_success: Optional[str] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
