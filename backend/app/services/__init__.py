"""Services Package."""
from __future__ import annotations

from app.services.intent_service import IntentService
from app.services.normalization_service import NormalizationService
from app.services.product_identity_service import ProductIdentityService, ProductMatchResult
from app.services.offer_service import OfferService, TrueCostService
from app.services.price_service import PriceService
from app.services.availability_service import AvailabilityService
from app.services.review_service import ReviewService
from app.services.recommendation_service import RecommendationService
from app.services.data_quality_service import DataQualityService
from app.services.freshness_service import FreshnessService
from app.services.search_orchestrator import SearchOrchestrator

from app.services.comparison_service import ComparisonService

__all__ = [
    "IntentService",
    "NormalizationService",
    "ProductIdentityService",
    "ProductMatchResult",
    "OfferService",
    "TrueCostService",
    "PriceService",
    "AvailabilityService",
    "ReviewService",
    "RecommendationService",
    "DataQualityService",
    "FreshnessService",
    "SearchOrchestrator",
    "ComparisonService",
]

