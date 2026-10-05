"""Unit tests for Recommendation Service."""
from __future__ import annotations

from app.providers.base.models import ProviderPrice, ProviderProduct
from app.schemas.search import ExtractedQueryIntent
from app.services.recommendation_service import RecommendationService


def test_recommendation_scoring():
    service = RecommendationService()

    intent = ExtractedQueryIntent(
        original="best wireless headphones under 30000 with ANC",
        category="headphones",
        max_price=30000.0,
        currency="INR",
        required_features={"noise_cancellation": True, "wireless": True},
        preferred_features={},
    )

    prod = ProviderProduct(
        provider="amazon",
        provider_product_id="B09XS7JWHH",
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones, Black",
        brand="Sony",
        price=ProviderPrice(amount=29990.0, original_price=34990.0),
        rating=4.5,
        review_count=1200,
        availability="in_stock",
    )

    rec = service.evaluate_product(prod, intent)
    assert 85 <= rec.match_score <= 100
    assert "Includes requested noise cancellation" in rec.reasons
    assert "Includes requested wireless" in rec.reasons
    assert any("budget" in r.lower() for r in rec.reasons)
