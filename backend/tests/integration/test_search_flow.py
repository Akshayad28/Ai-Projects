"""Integration tests for Search Orchestrator and Failure Isolation."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.providers.base.exceptions import ProviderBlocked
from app.providers.base.models import ProviderPrice, ProviderProduct
from app.services.search_orchestrator import SearchOrchestrator


@pytest.mark.asyncio
async def test_search_flow_failure_isolation():
    """Critical: If Amazon is BLOCKED but Flipkart succeeds, return Flipkart products.
    Never fail the entire search or return fake items.
    """
    orchestrator = SearchOrchestrator()

    # Mock Amazon as BLOCKED
    orchestrator.providers["amazon"].search_products = AsyncMock(
        side_effect=ProviderBlocked("Retailer access challenged")
    )
    for name, prov in orchestrator.providers.items():
        if name not in ("amazon", "flipkart"):
            prov.search_products = AsyncMock(return_value=[])

    # Mock Flipkart as SUCCESS with 1 real item
    fk_item = ProviderProduct(
        provider="flipkart",
        provider_product_id="ACCG6ZFF",
        title="Sony WH-1000XM5 Wireless Headphones, Black",
        brand="Sony",
        price=ProviderPrice(amount=29490.0, original_price=34990.0),
        rating=4.6,
        review_count=3100,
        availability="in_stock",
    )
    orchestrator.providers["flipkart"].search_products = AsyncMock(return_value=[fk_item])

    res = await orchestrator.execute_search(
        raw_query="best wireless headphones under 30000",
        country="IN",
        currency="INR",
    )

    assert res.status == "SUCCESS"
    assert res.providers["amazon"].status == "blocked"
    assert res.providers["flipkart"].status in ("healthy", "success")
    assert len(res.products) == 1
    assert res.products[0].title == "Sony WH-1000XM5 Wireless Headphones, Black"
    assert res.products[0].offers[0].retailer == "Flipkart"
    assert res.products[0].offers[0].price == 29490.0


@pytest.mark.asyncio
async def test_search_flow_no_live_data_never_fakes_products():
    """Critical: If all providers fail, return empty list and NO_LIVE_DATA status.
    NEVER hallucinate or fabricate products.
    """
    orchestrator = SearchOrchestrator()

    for prov in orchestrator.providers.values():
        prov.search_products = AsyncMock(side_effect=ProviderBlocked("Robot verification"))

    res = await orchestrator.execute_search(
        raw_query="mechanical keyboard under 5000",
        country="IN",
        currency="INR",
    )

    assert len(res.products) == 0
    assert res.status in ("NO_LIVE_DATA", "BLOCKED")
    assert "fake" not in res.message.lower()
    assert "temporarily unavailable" in res.message.lower()
