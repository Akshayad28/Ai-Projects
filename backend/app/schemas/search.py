"""Search Request and Response Schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.product import DynamicCardAttribute, RecommendationBreakdown
from app.schemas.offer import OfferSchema
from app.schemas.price_history import PriceSummary


class SearchQueryPayload(BaseModel):
    query: str
    country: str = "IN"
    currency: str = "INR"
    sort_by: str = "recommended"  # recommended | price_asc | price_desc | rating
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    page: int = 1
    page_size: int = 24


class ExtractedQueryIntent(BaseModel):
    original: str
    product_type: Optional[str] = None
    category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "INR"
    brand: Optional[str] = None
    model: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
    use_cases: List[str] = Field(default_factory=list)
    required_features: Dict[str, Any] = Field(default_factory=dict)
    preferred_features: Dict[str, Any] = Field(default_factory=dict)
    condition: str = "new"
    clean_provider_query: Optional[str] = None
    quick_commerce_priority: bool = False
    delivery_priority: bool = False
    department: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    pack_size: Optional[str] = None


class CanonicalSearchProduct(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category_id: Optional[str] = None
    image: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    recommendation: RecommendationBreakdown
    offers: List[OfferSchema] = Field(default_factory=list)
    price_summary: PriceSummary
    sources: List[str] = Field(default_factory=list)
    card_attributes: List[DynamicCardAttribute] = Field(default_factory=list)
    freshness_label: str = "Live Real-Time Data"
    data_coverage_score: Optional[float] = None
    is_quick_commerce: bool = False
    quick_commerce_eta: Optional[str] = None
    best_unit_price: Optional[str] = None


class ProviderExecutionStatus(BaseModel):
    status: str  # healthy | success | degraded | blocked | timeout | unavailable | error
    result_count: int = 0
    products_found: Optional[int] = None
    duration_ms: int = 0
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    reason: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.products_found is None:
            self.products_found = self.result_count
        if self.latency_ms is None:
            self.latency_ms = float(self.duration_ms)


class PaginationMetadata(BaseModel):
    page: int = 1
    page_size: int = 24
    total: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False
    total_offers: int = 0
    providers_contributing: int = 0


class UnifiedSearchResponse(BaseModel):
    search_id: str
    query: ExtractedQueryIntent
    products: List[CanonicalSearchProduct] = Field(default_factory=list)
    providers: Dict[str, ProviderExecutionStatus] = Field(default_factory=dict)
    search_duration_ms: int = 0
    total_products_found: int = 0
    deduped_count: int = 0
    pagination: PaginationMetadata = Field(default_factory=PaginationMetadata)
    status: str = "SUCCESS"  # SUCCESS | NO_LIVE_DATA | BLOCKED | DEGRADED | ERROR
    message: Optional[str] = None
    is_cached: bool = False
    is_revalidating: bool = False
    time_to_first_product_ms: Optional[int] = None
    timing_breakdown: Dict[str, Any] = Field(default_factory=dict)

