"""Automated Tests for Google Shopping Scraper Provider.

Tests HTML fixture parsing, price/currency parsing, URL resolution, rating extraction,
error isolation, model conversion, and configuration flags without hitting live Google.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.providers.base.exceptions import ProviderBlocked, ProviderTimeout, ProviderUnavailable
from app.providers.base.models import SearchQuery
from app.providers.google_scraper.models import GoogleScrapedItem
from app.providers.google_scraper.parser import (
    clean_retailer_name,
    extract_destination_url,
    parse_google_shopping_page,
    parse_price_and_currency,
    parse_rating_and_reviews,
)
from app.providers.google_scraper.provider import GoogleScraperProvider
from app.schemas.domain import ProviderSearchParams, SearchIntent
from app.services.search_orchestrator import SearchOrchestrator

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "google_shopping_fixture.html"


def load_fixture() -> str:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


# 1. Provider Initialization
def test_google_scraper_provider_initialization():
    provider = GoogleScraperProvider()
    assert provider.name == "google_scraper"
    assert provider.label == "Google Shopping"
    assert provider.is_demo is False
    assert "IN" in provider.countries
    assert "US" in provider.countries
    assert provider.is_configured() is True


# 2. Query Construction & Scraping URL
def test_google_scraper_query_and_url():
    scraper = GoogleScraperProvider()._scraper
    # Check domain mapping
    from app.providers.google_scraper.scraper import COUNTRY_DOMAIN_CONFIG
    assert COUNTRY_DOMAIN_CONFIG["IN"]["domain"] == "www.google.co.in"
    assert COUNTRY_DOMAIN_CONFIG["US"]["domain"] == "www.google.com"
    assert COUNTRY_DOMAIN_CONFIG["DE"]["gl"] == "de"
    assert COUNTRY_DOMAIN_CONFIG["GB"]["gl"] == "gb"
    assert COUNTRY_DOMAIN_CONFIG["AE"]["gl"] == "ae"
    assert COUNTRY_DOMAIN_CONFIG["SG"]["gl"] == "sg"


# 3. Price Parser handles various currencies
@pytest.mark.parametrize(
    "price_str,default_curr,expected_price,expected_curr",
    [
        ("₹29,999", "INR", 29999.0, "INR"),
        ("₹29 999", "INR", 29999.0, "INR"),
        ("₹28,999.00", "INR", 28999.0, "INR"),
        ("$299.99", "USD", 299.99, "USD"),
        ("£299", "GBP", 299.0, "GBP"),
        ("€499", "EUR", 499.0, "EUR"),
        ("AED 1,299", "AED", 1299.0, "AED"),
        ("S$ 450", "SGD", 450.0, "SGD"),
    ],
)
def test_price_parsing_supported_formats(price_str, default_curr, expected_price, expected_curr):
    price, curr = parse_price_and_currency(price_str, default_currency=default_curr)
    assert price == expected_price
    assert curr == expected_curr


# 4. Missing price returns None
def test_missing_price_returns_none():
    price, curr = parse_price_and_currency("")
    assert price is None
    assert curr is None

    price, curr = parse_price_and_currency("Currently unavailable")
    assert price is None


# 5 & 6. Rating and Review count parsing
def test_rating_and_review_parsing():
    rating, reviews = parse_rating_and_reviews("4.6", "(1,250 reviews)")
    assert rating == 4.6
    assert reviews == 1250

    rating, reviews = parse_rating_and_reviews("4.4 out of 5", "(3.4k)")
    assert rating == 4.4
    assert reviews == 3400

    rating, reviews = parse_rating_and_reviews(None, None)
    assert rating is None
    assert reviews is None


# 7. Retailer parsing
def test_retailer_cleaning():
    assert clean_retailer_name("From Croma") == "Croma"
    assert clean_retailer_name("Amazon.in") == "Amazon.in"
    assert clean_retailer_name("By Flipkart") == "Flipkart"
    assert clean_retailer_name("") is None


# 8. URL extraction (redirect unquoting & direct)
def test_url_extraction():
    google_redirect = "/url?url=https%3A%2F%2Fwww.croma.com%2Flg-monitor%2Fp%2F271828&rct=j&q="
    target = extract_destination_url(google_redirect)
    assert target == "https://www.croma.com/lg-monitor/p/271828"

    direct_url = "https://www.amazon.in/dp/B08M9V9GKG"
    assert extract_destination_url(direct_url) == direct_url


# 9, 10, 11. Parsing HTML fixture: multiple products, missing fields, malformed skipped
def test_fixture_parsing_and_quality():
    html_content = load_fixture()
    items = parse_google_shopping_page(html_content, country="IN", currency="INR")

    # From 7 cards in fixture:
    # Card 1: LG (Valid, Croma, strikethrough price)
    # Card 2: Samsung (Valid, Amazon)
    # Card 3: BenQ (Valid, missing rating)
    # Card 4: Acer (Valid, missing image)
    # Card 5: ASUS (Missing price -> skipped)
    # Card 6: Empty title -> skipped
    # Card 7: Dell (Valid, $299.99 from Best Buy)
    assert len(items) == 5

    # Check Card 1
    lg = items[0]
    assert "LG UltraGear" in lg.title
    assert lg.price_amount == 28999.0
    assert lg.currency == "INR"
    assert lg.original_price == 36000.0
    assert lg.retailer_name == "Croma"
    assert lg.rating == 4.6
    assert lg.review_count == 1250
    assert lg.shipping_text == "Free delivery"
    assert lg.url == "https://www.croma.com/lg-monitor/p/271828"
    assert lg.image_url == "https://images.example.com/lg-27gr83q.jpg"

    # Check Card 3 (missing rating/review count does not crash)
    benq = items[2]
    assert "BenQ MOBIUZ" in benq.title
    assert benq.rating is None
    assert benq.review_count is None

    # Check Card 4 (missing image does not crash)
    acer = items[3]
    assert "Acer Nitro" in acer.title
    assert acer.image_url is None

    # Check Card 7 (US currency)
    dell = items[4]
    assert "Dell G2724D" in dell.title
    assert dell.price_amount == 299.99
    assert dell.currency == "USD"
    assert dell.retailer_name == "Best Buy"


# 12. Conversion to RawProduct and ProviderProduct
def test_model_conversions():
    html_content = load_fixture()
    items = parse_google_shopping_page(html_content, country="IN", currency="INR")
    item = items[0]

    raw_prod = item.to_raw_product()
    assert raw_prod.provider == "google_scraper"
    assert "LG UltraGear" in raw_prod.title
    assert len(raw_prod.offers) == 1
    assert raw_prod.offers[0].price_amount == 28999.0
    assert raw_prod.offers[0].retailer_name == "Croma"

    prov_prod = item.to_provider_product()
    assert prov_prod.provider == "google_scraper"
    assert prov_prod.price.amount == 28999.0
    assert prov_prod.price.discount == 7001.0
    assert prov_prod.seller == "Croma"


# 13. Provider failure isolation in SearchOrchestrator
@pytest.mark.asyncio
async def test_google_provider_failure_isolation():
    orchestrator = SearchOrchestrator()
    # Mock google_scraper to raise ProviderBlocked
    mock_google = AsyncMock()
    mock_google.search_products.side_effect = ProviderBlocked("Google verification challenge")

    mock_amazon = AsyncMock()
    from app.providers.base.models import ProviderPrice, ProviderProduct
    mock_amazon.search_products.return_value = [
        ProviderProduct(
            provider="amazon",
            provider_product_id="amz-123",
            title="Sony WH-1000XM5 Headphones",
            price=ProviderPrice(amount=29990.0, currency="INR"),
            seller="Amazon",
        )
    ]

    orchestrator.providers = {
        "google_scraper": mock_google,
        "amazon": mock_amazon,
    }

    res = await orchestrator.execute_search("sony headphones", country="IN", currency="INR")
    # Verify search did NOT crash
    assert res.status == "SUCCESS"
    assert res.providers["google_scraper"].status == "blocked"
    assert res.providers["amazon"].status in ("healthy", "success")
    assert len(res.products) == 1
    assert "Sony" in res.products[0].title


# 14. Configuration disable flag
def test_google_provider_can_be_disabled():
    settings = get_settings()
    settings.google_scraper_enabled = False
    provider = GoogleScraperProvider()
    assert provider.is_configured() is False
    # Re-enable
    settings.google_scraper_enabled = True
    assert provider.is_configured() is True
