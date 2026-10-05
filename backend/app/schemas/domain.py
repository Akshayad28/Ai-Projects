"""Provider-level (pre-normalization) and pipeline domain models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AvailabilityStatus = Literal["in_stock", "limited", "out_of_stock", "preorder", "unknown"]
Condition = Literal["new", "refurbished", "used", "open_box"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Budget(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[str] = None


class SearchIntent(BaseModel):
    """Structured interpretation of the user's request. Contains NO product facts."""

    raw_query: str
    provider_query: str
    category: Optional[str] = None
    category_confidence: float = 0.0
    subcategory: Optional[str] = None
    budget: Budget = Field(default_factory=Budget)
    use_cases: List[str] = []
    requirements: List[str] = []
    optional_features: List[str] = []
    preferred_brands: List[str] = []
    required_brands: List[str] = []
    excluded_brands: List[str] = []
    quantity: Optional[int] = None
    size: Optional[str] = None
    color: Optional[str] = None
    condition: Condition = "new"
    country: str = "IN"
    delivery: Optional[str] = None
    keywords: List[str] = []
    parser: Literal["llm", "rules"] = "rules"
    quick_commerce_priority: bool = False
    delivery_priority: bool = False
    department: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    pack_size: Optional[str] = None


class RawOffer(BaseModel):
    provider: str
    retailer_name: str
    retailer_domain: Optional[str] = None
    seller_name: str = ""
    seller_rating: Optional[float] = None
    seller_rating_count: Optional[int] = None
    country: Optional[str] = None
    price_amount: Optional[float] = None
    currency: Optional[str] = None
    original_price: Optional[float] = None
    shipping_amount: Optional[float] = None
    shipping_text: Optional[str] = None
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
    availability_checked_at: Optional[datetime] = None
    delivery_checked_at: Optional[datetime] = None
    tax_amount: Optional[float] = None
    coupon_text: Optional[str] = None
    cashback_text: Optional[str] = None
    availability: AvailabilityStatus = "unknown"
    condition: Condition = "new"
    url: Optional[str] = None
    affiliate_url: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None
    confidence: float = 1.0
    checked_at: datetime = Field(default_factory=now_utc)

    @property
    def price_verified(self) -> bool:
        return self.price_amount is not None and self.price_amount > 0 and bool(self.currency)


class RawReview(BaseModel):
    source: str
    external_id: str
    rating: Optional[float] = None
    title: Optional[str] = None
    text: Optional[str] = None
    review_date: Optional[datetime] = None
    verified: Optional[bool] = None


class RawProduct(BaseModel):
    provider: str
    external_id: str
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    gtin: Optional[str] = None
    upc: Optional[str] = None
    ean: Optional[str] = None
    mpn: Optional[str] = None
    asin: Optional[str] = None
    sku: Optional[str] = None
    url: Optional[str] = None
    primary_image: Optional[str] = None
    image_urls: List[str] = []
    rating: Optional[float] = None
    review_count: Optional[int] = None
    rating_source: Optional[str] = None
    specs: Dict[str, Any] = {}
    variant_attributes: Dict[str, str] = {}
    data_coverage_score: Optional[float] = None
    condition: Condition = "new"
    category_hint: Optional[str] = None
    country: Optional[str] = None
    offers: List[RawOffer] = []
    reviews: List[RawReview] = []
    extra: Dict[str, Any] = {}
    is_demo: bool = False


class ProviderSearchParams(BaseModel):
    query: str
    intent: SearchIntent
    country: str
    currency: str
    limit: int = 30
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        if self.min_price is None and hasattr(self.intent, "budget") and self.intent.budget:
            self.min_price = getattr(self.intent.budget, "min", None)
        if self.max_price is None and hasattr(self.intent, "budget") and self.intent.budget:
            self.max_price = getattr(self.intent.budget, "max", None)


class ProviderAvailability(BaseModel):
    provider: str
    status: AvailabilityStatus
    checked_at: datetime = Field(default_factory=now_utc)
    detail: Optional[str] = None


class ProviderSearchResult(BaseModel):
    provider: str
    products: List[RawProduct] = []
    status: Literal["ok", "error", "timeout", "skipped", "rate_limited"] = "ok"
    error: Optional[str] = None
    latency_ms: int = 0
