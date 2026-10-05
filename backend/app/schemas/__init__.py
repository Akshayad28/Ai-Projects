"""Schemas Package."""
from __future__ import annotations

from app.schemas.product import (
    DynamicCardAttribute,
    RecommendationBreakdown,
    ProductVariantSchema,
    CanonicalProductDetail,
)
from app.schemas.offer import OfferSchema, TrueCostBreakdown
from app.schemas.price_history import PricePoint, PriceSummary, PriceHistoryResponse
from app.schemas.review import ReviewItem, ReviewAnalysisResponse
from app.schemas.search import (
    SearchQueryPayload,
    ExtractedQueryIntent,
    CanonicalSearchProduct,
    ProviderExecutionStatus,
    UnifiedSearchResponse,
)

from app.schemas.comparison import (
    ComparisonRequest,
    ComparisonProductItem,
    ScorecardDimension,
    ComparisonAttributeRow,
    ComparisonSection,
    ProductBuyingInsights,
    ComparisonAIVerdict,
    ComparisonResponse,
)

__all__ = [
    "DynamicCardAttribute",
    "RecommendationBreakdown",
    "ProductVariantSchema",
    "CanonicalProductDetail",
    "OfferSchema",
    "TrueCostBreakdown",
    "PricePoint",
    "PriceSummary",
    "PriceHistoryResponse",
    "ReviewItem",
    "ReviewAnalysisResponse",
    "SearchQueryPayload",
    "ExtractedQueryIntent",
    "CanonicalSearchProduct",
    "ProviderExecutionStatus",
    "UnifiedSearchResponse",
    "ComparisonRequest",
    "ComparisonProductItem",
    "ScorecardDimension",
    "ComparisonAttributeRow",
    "ComparisonSection",
    "ProductBuyingInsights",
    "ComparisonAIVerdict",
    "ComparisonResponse",
]

