"""Unit tests for Product Identity Service and Variant Disambiguation."""
from __future__ import annotations

from app.providers.base.models import ProviderPrice, ProviderProduct
from app.services.product_identity_service import ProductIdentityService


def test_product_matching_same_model_across_retailers():
    service = ProductIdentityService()

    # Amazon listing
    p_amz = ProviderProduct(
        provider="amazon",
        provider_product_id="B09XS7JWHH",
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones, Black",
        brand="Sony",
        price=ProviderPrice(amount=29990.0),
    )

    # Flipkart listing
    p_fk = ProviderProduct(
        provider="flipkart",
        provider_product_id="ACCG6ZFFHGZHZHYG",
        title="SONY WH-1000XM5 Wireless Active Noise Cancelling Headphones, Black",
        brand="Sony",
        price=ProviderPrice(amount=29490.0),
    )

    res = service.match_products(p_amz, p_fk)
    assert res.matched is True
    assert res.confidence >= 0.90
    assert res.method in ("brand_model", "brand_spec_token")


def test_variant_rejection_different_storage():
    """Critical Rule: iPhone 256GB and iPhone 512GB MUST NEVER be merged."""
    service = ProductIdentityService()

    p_256 = ProviderProduct(
        provider="amazon",
        provider_product_id="B0CHX1",
        title="Apple iPhone 16 Pro (256 GB) - Natural Titanium",
        brand="Apple",
        variant_attributes={"storage": "256GB", "color": "Natural Titanium"},
        price=ProviderPrice(amount=119900.0),
    )

    p_512 = ProviderProduct(
        provider="flipkart",
        provider_product_id="FK16PRO512",
        title="Apple iPhone 16 Pro (512 GB) - Natural Titanium",
        brand="Apple",
        variant_attributes={"storage": "512GB", "color": "Natural Titanium"},
        price=ProviderPrice(amount=139900.0),
    )

    res = service.match_products(p_256, p_512)
    assert res.matched is False
    assert res.method == "variant_incompatible"
