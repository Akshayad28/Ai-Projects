"""API request and response schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.domain import AvailabilityStatus, Condition, SearchIntent


from pydantic import field_validator

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=300, description="Natural language search query")
    currency: str = Field("INR", min_length=3, max_length=3)
    country: str = Field("IN", min_length=2, max_length=2)
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_by: Optional[str] = Field("recommended", max_length=32, description="recommended | price_asc | price_desc | rating | match")
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(24, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def sanitize_search_query(cls, v: str) -> str:
        from app.core.sanitizer import sanitize_query
        clean = sanitize_query(v, max_length=300)
        if len(clean) < 2:
            raise ValueError("Query must contain at least 2 valid characters.")
        return clean



class DynamicCardAttribute(BaseModel):
    key: str
    label: str
    value: Any
    unit: Optional[str] = None


class OfferItemResponse(BaseModel):
    id: Optional[int] = None
    provider: str
    retailer_name: str
    retailer_domain: Optional[str] = None
    seller_name: str = ""
    seller_rating: Optional[float] = None
    country: Optional[str] = None
    price_amount: Optional[float] = None
    currency: Optional[str] = None
    original_price: Optional[float] = None
    discount_percent: Optional[int] = None
    shipping_text: Optional[str] = None
    delivery_estimate: Optional[str] = None
    availability: AvailabilityStatus = "unknown"
    condition: Condition = "new"
    url: Optional[str] = None
    affiliate_url: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None
    confidence: float = 1.0
    checked_at: str


class RecommendationBreakdownResponse(BaseModel):
    match_score: int
    reasons: List[str] = []
    drawbacks: List[str] = []
    why_not_higher: List[str] = []


class ProductCardResponse(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: List[str] = []
    rating: Optional[float] = None
    review_count: Optional[int] = None
    best_price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "INR"
    discount_percent: Optional[int] = None
    primary_retailer: str = "Verified Seller"
    offers_count: int = 1
    availability: AvailabilityStatus = "unknown"
    card_attributes: List[DynamicCardAttribute] = []
    recommendation: RecommendationBreakdownResponse
    sources: List[str] = []
    is_demo: bool = False
    last_updated: str
    is_quick_commerce: bool = False
    quick_commerce_eta: Optional[str] = None
    best_unit_price: Optional[str] = None
    data_coverage_score: Optional[float] = None
    offers: List[OfferItemResponse] = []


class PaginationMetadataResponse(BaseModel):
    page: int = 1
    page_size: int = 24
    total: int = 0
    total_pages: int = 1
    has_next: bool = False
    total_offers: int = 0
    providers_contributing: int = 0


class SearchMetadataResponse(BaseModel):
    search_id: str
    search_duration_ms: int
    providers_used: List[str] = []
    products_found: int
    deduped_count: int
    total_offers: Optional[int] = None
    providers_contributing: Optional[int] = None
    pagination: Optional[PaginationMetadataResponse] = None
    providers: Optional[Dict[str, Any]] = None
    is_live: bool = True
    live_providers_configured: int = 0
    live_providers: List[Dict[str, Any]] = []
    freshness_label: str = "Live Real-Time Data"
    is_demo: bool = False
    demo_mode_active: bool = False
    demo_notice: Optional[str] = None
    unconfigured_notice: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    intent: SearchIntent
    products: List[ProductCardResponse] = []
    search_metadata: SearchMetadataResponse
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None
    has_next: Optional[bool] = None
    providers: Optional[Dict[str, Any]] = None
    marketplaces: Optional[List[Dict[str, Any]]] = None



class CategoryResponse(BaseModel):
    id: str
    name: str
    department: str
    keywords: List[str] = []
    sort_order: int


class WishlistItemCreate(BaseModel):
    product_id: str
    target_price: Optional[float] = None
    currency: str = "INR"
    notes: Optional[str] = None


class PriceAlertCreate(BaseModel):
    product_id: str
    alert_type: str = "target_price"
    target_price: Optional[float] = None
    percent_drop: Optional[float] = None
    currency: str = "INR"
