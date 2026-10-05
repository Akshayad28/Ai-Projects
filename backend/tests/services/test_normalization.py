"""Unit tests for Normalization Service."""
from __future__ import annotations

from app.providers.base.models import ProviderPrice, ProviderProduct
from app.services.normalization_service import NormalizationService
from app.utils.text_normalization import normalize_text, extract_brand_from_title


def test_text_normalization():
    raw = "Apple MacBook Air 15\" (M3 Chip, 16GB RAM) - Space Grey!!"
    norm = normalize_text(raw)
    assert "apple macbook air 15 m3 chip 16gb ram - space grey" in norm


def test_brand_extraction():
    assert extract_brand_from_title("Sony WH-1000XM5") == "Sony"
    assert extract_brand_from_title("Apple iPhone 16") == "Apple"
    assert extract_brand_from_title("Bose QuietComfort Ultra") == "Bose"
    assert extract_brand_from_title("JBL Tune 760NC") == "JBL"


def test_product_normalization():
    service = NormalizationService()
    p = ProviderProduct(
        provider="amazon",
        provider_product_id="B09XS7JWHH",
        title="Sony WH-1000XM5 Wireless Headphones, Black",
        price=ProviderPrice(amount=29990.0, original_price=34990.0),
        rating=4.5,
        review_count=1200,
        image_url="https://example.com/sony.jpg",
    )
    canonical = service.normalize_provider_product(p, category_id="headphones")
    assert canonical.brand == "Sony"
    assert canonical.category_id == "headphones"
    assert canonical.data_quality_score >= 0.8
