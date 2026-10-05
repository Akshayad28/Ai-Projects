"""Comprehensive tests for Multi-Provider Search, Aggregation, Offer Preservation, and Pagination."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.providers.base.exceptions import ProviderBlocked, ProviderRateLimited
from app.providers.base.models import ProviderPrice, ProviderProduct
from app.services.search_orchestrator import SearchOrchestrator
from app.nlp.intent import parse_intent


@pytest.mark.asyncio
async def test_multi_provider_parallel_dispatch_and_aggregation():
    """Verify that Google, Amazon, Flipkart, eBay, and Merchant Feeds all contribute,
    duplicate products are unified, and offers from ALL providers survive.
    """
    orchestrator = SearchOrchestrator()

    # Product A is on Google, Amazon, and Flipkart
    # Product B is on Flipkart and eBay
    # Product C is only on eBay
    google_item = ProviderProduct(
        provider="google_scraper",
        provider_product_id="goog-1",
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        brand="Sony",
        price=ProviderPrice(amount=28990.0, currency="INR"),
        url="https://google.com/shopping/1",
        seller="Google Merchant",
        rating=4.7,
        review_count=4500,
    )

    amazon_item = ProviderProduct(
        provider="amazon",
        provider_product_id="amz-1",
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black",
        brand="Sony",
        price=ProviderPrice(amount=29990.0, currency="INR"),
        url="https://amazon.in/dp/B09XS7JWHH",
        seller="Amazon",
        rating=4.6,
        review_count=5200,
    )

    flipkart_item_a = ProviderProduct(
        provider="flipkart",
        provider_product_id="fk-1",
        title="Sony WH-1000XM5 Bluetooth Headset (Black)",
        brand="Sony",
        price=ProviderPrice(amount=29490.0, currency="INR"),
        url="https://flipkart.com/p/1",
        seller="Flipkart",
        rating=4.5,
        review_count=3100,
    )

    flipkart_item_b = ProviderProduct(
        provider="flipkart",
        provider_product_id="fk-2",
        title="Bose QuietComfort Ultra Headphones",
        brand="Bose",
        price=ProviderPrice(amount=35900.0, currency="INR"),
        url="https://flipkart.com/p/2",
        seller="Flipkart",
        rating=4.6,
        review_count=1200,
    )

    ebay_item_b = ProviderProduct(
        provider="ebay",
        provider_product_id="ebay-2",
        title="Bose QuietComfort Ultra Noise Cancelling Headphones Black",
        brand="Bose",
        price=ProviderPrice(amount=34500.0, currency="INR"),
        url="https://ebay.com/itm/2",
        seller="eBay Seller",
        rating=4.8,
        review_count=800,
    )

    ebay_item_c = ProviderProduct(
        provider="ebay",
        provider_product_id="ebay-3",
        title="Sennheiser Momentum 4 Wireless Headphones",
        brand="Sennheiser",
        price=ProviderPrice(amount=24990.0, currency="INR"),
        url="https://ebay.com/itm/3",
        seller="eBay Seller",
        rating=4.4,
        review_count=950,
    )

    # Mock providers
    mock_google = AsyncMock()
    mock_google.search_products.return_value = [google_item]
    mock_amazon = AsyncMock()
    mock_amazon.search_products.return_value = [amazon_item]
    mock_flipkart = AsyncMock()
    mock_flipkart.search_products.return_value = [flipkart_item_a, flipkart_item_b]
    mock_ebay = AsyncMock()
    mock_ebay.search_products.return_value = [ebay_item_b, ebay_item_c]

    orchestrator.providers = {
        "google_scraper": mock_google,
        "amazon": mock_amazon,
        "flipkart": mock_flipkart,
        "ebay": mock_ebay,
    }

    res = await orchestrator.execute_search(
        raw_query="best wireless headphones under 40000",
        country="IN",
        currency="INR",
        page=1,
        page_size=24,
    )

    assert res.status == "SUCCESS"
    assert len(res.products) == 3  # Sony XM5, Bose QC Ultra, Sennheiser Momentum 4
    assert res.pagination.total == 3
    assert res.pagination.total_offers == 6  # 3 on Sony, 2 on Bose, 1 on Sennheiser
    assert res.pagination.providers_contributing == 4

    # Check Sony XM5 offers
    sony_prod = next(p for p in res.products if "Sony" in p.title or "WH-1000XM5" in p.title)
    assert len(sony_prod.offers) == 3
    sony_retailers = {o.retailer.lower() for o in sony_prod.offers}
    assert "google merchant" in sony_retailers or "google_scraper" in sony_retailers
    assert "amazon" in sony_retailers
    assert "flipkart" in sony_retailers

    # Check Bose QC Ultra offers
    bose_prod = next(p for p in res.products if "Bose" in p.title)
    assert len(bose_prod.offers) == 2
    bose_retailers = {o.retailer.lower() for o in bose_prod.offers}
    assert "flipkart" in bose_retailers
    assert "ebay" in bose_retailers


@pytest.mark.asyncio
async def test_pagination_mechanics():
    """Verify backend pagination properly divides results across pages without losing products."""
    orchestrator = SearchOrchestrator()

    # Generate 50 distinct items across various brands
    items = []
    for i in range(50):
        items.append(
            ProviderProduct(
                provider="amazon",
                provider_product_id=f"item-{i}",
                title=f"Ergonomic Chair Series {chr(65 + (i % 26))}{i}",
                brand=f"Brand{i+1}",
                price=ProviderPrice(amount=10000.0 + (i * 100), currency="INR"),
            )
        )

    mock_amazon = AsyncMock()
    mock_amazon.search_products.return_value = items
    orchestrator.providers = {"amazon": mock_amazon}

    # Page 1 (24 items)
    page1 = await orchestrator.execute_search(
        raw_query="office chair",
        page=1,
        page_size=24,
    )
    assert len(page1.products) == 24
    assert page1.pagination.page == 1
    assert page1.pagination.page_size == 24
    assert page1.pagination.total == 50
    assert page1.pagination.total_pages == 3
    assert page1.pagination.has_next is True

    # Page 2 (24 items)
    page2 = await orchestrator.execute_search(
        raw_query="office chair",
        page=2,
        page_size=24,
    )
    assert len(page2.products) == 24
    assert page2.pagination.page == 2
    assert page2.pagination.has_next is True

    # Page 3 (2 items)
    page3 = await orchestrator.execute_search(
        raw_query="office chair",
        page=3,
        page_size=24,
    )
    assert len(page3.products) == 2
    assert page3.pagination.page == 3
    assert page3.pagination.has_next is False


@pytest.mark.asyncio
async def test_universal_search_intent_unclassified_category():
    """Verify queries with unknown or novel categories are not rejected."""
    intent = await parse_intent("something good for organizing cables under my desk under ₹1,500")
    assert intent.raw_query == "something good for organizing cables under my desk under ₹1,500"
    assert intent.budget.max == 1500.0
    assert intent.budget.currency == "INR"
    assert "cable" in intent.provider_query.lower() or "organizing" in intent.provider_query.lower()


@pytest.mark.asyncio
async def test_provider_blocked_isolation_google_and_amazon():
    """Verify if Google Scraper and Amazon are blocked, Flipkart and eBay still deliver results."""
    orchestrator = SearchOrchestrator()

    mock_google = AsyncMock()
    mock_google.search_products.side_effect = ProviderBlocked("Google Bot Detection")

    mock_amazon = AsyncMock()
    mock_amazon.search_products.side_effect = ProviderBlocked("Amazon Bot Detection")

    fk_item = ProviderProduct(
        provider="flipkart",
        provider_product_id="fk-101",
        title="Green Soul Monster Ultimate Office Chair",
        brand="Green Soul",
        price=ProviderPrice(amount=18990.0, currency="INR"),
    )
    mock_flipkart = AsyncMock()
    mock_flipkart.search_products.return_value = [fk_item]

    orchestrator.providers = {
        "google_scraper": mock_google,
        "amazon": mock_amazon,
        "flipkart": mock_flipkart,
    }

    res = await orchestrator.execute_search("green soul chair isolation test", country="IN", currency="INR")
    assert res.status == "SUCCESS"
    assert res.providers["google_scraper"].status == "blocked"
    assert res.providers["amazon"].status == "blocked"
    assert res.providers["flipkart"].status in ("healthy", "success")
    assert len(res.products) == 1
    assert "Green Soul" in res.products[0].title
