"""Optional live integration test for Google Shopping Scraper.

Disabled by default so CI and local test suites remain hermetic and deterministic.
To run live: RUN_GOOGLE_LIVE_TESTS=true pytest tests/integration/test_google_scraper_live.py
"""
from __future__ import annotations

import os
import pytest

from app.providers.base.models import SearchQuery
from app.providers.google_scraper.provider import GoogleScraperProvider


@pytest.mark.skipif(
    os.getenv("RUN_GOOGLE_LIVE_TESTS", "false").lower() != "true",
    reason="Live Google tests disabled by default. Set RUN_GOOGLE_LIVE_TESTS=true to enable.",
)
@pytest.mark.asyncio
async def test_live_google_shopping_search():
    provider = GoogleScraperProvider()
    query = SearchQuery(
        query="gaming monitor under 30000",
        country="IN",
        currency="INR",
        limit=5,
    )
    products = await provider.search_products(query)
    assert isinstance(products, list)
    if products:
        p0 = products[0]
        assert p0.title
        assert p0.provider == "google_scraper"
