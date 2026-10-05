"""Deterministic tests for Google Shopping Scraping resilience.

Validates layout detection, modular parsers, multi-layer extraction, candidate validation,
CAPTCHA / block detection, circuit breaker lifecycle, rate limiting, and degradation metrics
using local HTML fixtures without hitting live Google.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import time
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.providers.base.exceptions import ProviderBlocked, ProviderTimeout
from app.providers.google_scraper.extraction import (
    extract_image_url,
    extract_merchant,
    extract_price,
    extract_title,
    extract_url,
    parse_price_and_currency,
)
from app.providers.google_scraper.health import (
    GoogleCircuitBreaker,
    GoogleRateLimiter,
    detect_google_block,
)
from app.providers.google_scraper.models import (
    CircuitState,
    ExtractionHealth,
    GoogleLayout,
    GoogleScrapedItem,
)
from app.providers.google_scraper.parser import (
    CarouselParser,
    GenericParser,
    GoogleParserDispatcher,
    GridParser,
    ListParser,
)
from app.providers.google_scraper.provider import GoogleScraperProvider
from app.providers.google_scraper.validation import is_product_candidate, validate_price, validate_title
from app.services.product_identity_service import ProductIdentityService

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "google"


def read_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── 1 & 2. Layout Detection and Grid Parsing ────────────────────────
def test_grid_layout_v1_parsing():
    html_content = read_fixture("shopping_grid_v1.html")
    dispatcher = GoogleParserDispatcher()
    soup = BeautifulSoup(html_content, "lxml")
    layout = dispatcher.detect_layout(soup)
    assert layout == GoogleLayout.SHOPPING_GRID

    items, health = dispatcher.parse(html_content, country="IN", currency="INR")
    assert len(items) == 2
    assert health.layout == GoogleLayout.SHOPPING_GRID
    assert health.cards_found == 2
    assert health.products_parsed == 2

    p1 = items[0]
    assert "LG UltraGear" in p1.title
    assert p1.price_amount == 24999.0
    assert p1.currency == "INR"
    assert p1.original_price == 32000.0
    assert p1.retailer_name == "Amazon.in"
    assert p1.rating == 4.5
    assert p1.review_count == 1420
    assert p1.url == "https://www.amazon.in/dp/B08CF4PS44"
    assert p1.image_url == "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_lg_monitor"


# ── 3. Grid Parsing V2 (Alternative selectors, EUR, German) ───────────
def test_grid_layout_v2_parsing():
    html_content = read_fixture("shopping_grid_v2.html")
    dispatcher = GoogleParserDispatcher()
    items, health = dispatcher.parse(html_content, country="DE", currency="EUR")
    assert len(items) == 2
    assert health.layout == GoogleLayout.SHOPPING_GRID

    asus = items[0]
    assert "ASUS TUF Gaming" in asus.title
    assert asus.price_amount == 299.0
    assert asus.currency == "EUR"
    assert asus.retailer_name == "MediaMarkt"
    assert asus.url == "https://www.mediamarkt.de/product/asus-tuf-123"
    assert asus.image_url == "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_asus_de"


# ── 4 & 5. Carousel Layout Parsing (PLA units & scrolling carousel) ──
def test_carousel_layout_v1_parsing():
    html_content = read_fixture("shopping_carousel_v1.html")
    dispatcher = GoogleParserDispatcher()
    soup = BeautifulSoup(html_content, "lxml")
    layout = dispatcher.detect_layout(soup)
    assert layout == GoogleLayout.SHOPPING_CAROUSEL

    items, health = dispatcher.parse(html_content, country="IN", currency="INR")
    assert len(items) == 2
    nike = items[0]
    assert "Nike Air Zoom Pegasus" in nike.title
    assert nike.price_amount == 9695.0
    assert nike.retailer_name == "Nike.in"
    assert nike.rating == 4.6
    assert nike.review_count == 3200


def test_carousel_layout_v2_srcset_image():
    html_content = read_fixture("shopping_carousel_v2.html")
    dispatcher = GoogleParserDispatcher()
    items, health = dispatcher.parse(html_content, country="IN", currency="INR")
    assert len(items) == 2
    fryer1 = items[0]
    assert "Philips Essential Air Fryer" in fryer1.title
    assert fryer1.price_amount == 6999.0
    assert fryer1.retailer_name == "Croma"
    # Verify srcset selected the higher resolution image
    assert fryer1.image_url == "https://images.google.com/fryer1_large.jpg"
    assert fryer1.url == "https://www.croma.com/philips-airfryer/p/1234"


# ── 6. List Layout Parsing ───────────────────────────────────────────
def test_list_layout_v1_parsing():
    html_content = read_fixture("shopping_list_v1.html")
    dispatcher = GoogleParserDispatcher()
    soup = BeautifulSoup(html_content, "lxml")
    layout = dispatcher.detect_layout(soup)
    assert layout == GoogleLayout.SHOPPING_LIST

    items, health = dispatcher.parse(html_content, country="IN", currency="INR")
    assert len(items) == 2
    lenovo = items[0]
    assert "Lenovo ThinkPad E14" in lenovo.title
    assert lenovo.price_amount == 64990.0
    assert lenovo.retailer_name == "Lenovo Official Store"


# ── 7. Unknown Layout / Semantic Heuristics ───────────────────────────
def test_unknown_layout_semantic_fallback():
    html_content = read_fixture("unknown_layout.html")
    dispatcher = GoogleParserDispatcher()
    soup = BeautifulSoup(html_content, "lxml")
    layout = dispatcher.detect_layout(soup)
    assert layout == GoogleLayout.UNKNOWN

    items, health = dispatcher.parse(html_content, country="IN", currency="INR")
    assert len(items) == 2
    assert health.layout == GoogleLayout.UNKNOWN

    k2 = items[0]
    assert "Keychron K2" in k2.title
    assert k2.price_amount == 7499.0
    assert k2.retailer_name == "Keychron India"
    assert k2.url == "https://keychron.in/product/k2-v2"


# ── 8. Product Candidate Validation ──────────────────────────────────
def test_product_candidate_validation():
    # Valid candidate with price and link
    soup_valid = BeautifulSoup(
        "<div><h3>Wireless Mouse</h3><span class='price'>₹999</span><a href='/buy'>Buy</a></div>",
        "html.parser",
    )
    assert is_product_candidate(soup_valid.div) is True

    # Invalid: navigation element
    soup_nav = BeautifulSoup("<nav><a href='/home'>Home</a><a href='/about'>About</a></nav>", "html.parser")
    assert is_product_candidate(soup_nav.nav) is False

    # Invalid: ad choices disclaimer
    soup_ad = BeautifulSoup("<div>Sponsored Why this ad? Learn more</div>", "html.parser")
    assert is_product_candidate(soup_ad.div) is False


# ── 9. Partial Products & Missing Fields ─────────────────────────────
def test_partial_products_handling():
    html_content = read_fixture("partial_product.html")
    dispatcher = GoogleParserDispatcher()
    items, health = dispatcher.parse(html_content, country="IN", currency="INR")

    # Item 1: Complete Bose
    # Item 2: Missing price (skipped)
    # Item 3: Missing image & rating (parsed with None)
    # Item 4: Non-product Ad choices (skipped by validation)
    assert len(items) == 2

    bose = items[0]
    assert "Bose QuietComfort 45" in bose.title
    assert bose.price_amount == 22900.0

    ath = items[1]
    assert "Audio-Technica ATH-M50x" in ath.title
    assert ath.price_amount == 13500.0
    assert ath.image_url is None
    assert ath.rating is None
    assert ath.review_count is None


# ── 10. CAPTCHA / Access Block Detection ─────────────────────────────
def test_detect_google_block_from_html():
    captcha_html = read_fixture("captcha.html")
    reason = detect_google_block(html_content=captcha_html)
    assert reason in ("UNUSUAL_TRAFFIC", "CAPTCHA_DETECTED", "GOOGLE_SORRY_PAGE")


def test_detect_google_block_from_status_and_url():
    assert detect_google_block(status_code=429) == "HTTP_429"
    assert detect_google_block(status_code=403) == "HTTP_403"
    assert detect_google_block(current_url="https://www.google.com/sorry/index?continue=...") == "GOOGLE_SORRY_REDIRECT"
    assert detect_google_block(status_code=200, current_url="https://www.google.com/search?tbm=shop") is None


# ── 11. Circuit Breaker Lifecycle (CLOSED -> OPEN -> HALF_OPEN -> CLOSED) ──
@pytest.mark.asyncio
async def test_circuit_breaker_lifecycle():
    cb = GoogleCircuitBreaker(cooldown_seconds=1.0)
    assert cb.state == CircuitState.CLOSED
    assert await cb.can_request() is True

    # Record block
    await cb.record_block("CAPTCHA_DETECTED")
    assert cb.state == CircuitState.OPEN
    assert cb.last_block_reason == "CAPTCHA_DETECTED"
    # Immediately subsequent request is rejected
    assert await cb.can_request() is False

    # Wait for cooldown
    await asyncio.sleep(1.1)
    # Moving to HALF_OPEN probe
    assert await cb.can_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Probe succeeds -> resets to CLOSED
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert await cb.can_request() is True


# ── 12. Rate Limiter Throttle ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_rate_limiter_throttles():
    limiter = GoogleRateLimiter(requests_per_second=5.0)  # 200ms interval
    t0 = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - t0
    # Second acquire should have slept ~0.2s
    assert elapsed >= 0.15


# ── 13. Extraction Health & Degradation Detection ────────────────────
def test_extraction_health_metrics():
    health = ExtractionHealth(
        layout=GoogleLayout.SHOPPING_GRID,
        cards_found=20,
        products_detected=18,
        products_parsed=18,
        products_with_title=18,
        products_with_price=18,
        products_with_image=16,
        products_with_merchant=17,
        products_with_url=18,
    )
    assert health.price_success_rate == 1.0
    assert health.image_success_rate == 0.89
    assert health.merchant_success_rate == 0.94
    assert health.url_success_rate == 1.0
    assert health.is_degraded(threshold=0.2) is False

    # Degraded scenario: 25 cards found, only 2 parsed
    degraded_health = ExtractionHealth(
        layout=GoogleLayout.SHOPPING_GRID,
        cards_found=25,
        products_parsed=2,
    )
    assert degraded_health.is_degraded(threshold=0.2) is True


# ── 14. Deduplication and Identity Compatibility ─────────────────────
def test_google_scraped_items_cluster_with_identity_service():
    html_content = read_fixture("shopping_grid_v1.html")
    items = GoogleParserDispatcher().parse(html_content)[0]

    # Convert to ProviderProduct
    p1 = items[0].to_provider_product()
    # Create duplicate offer from different merchant
    p2 = items[0].to_provider_product()
    p2.seller = "Croma"
    p2.price.amount = 25499.0

    identity_service = ProductIdentityService()
    clusters = identity_service.cluster_products([p1, p2])
    # Both identical products should be clustered together
    assert len(clusters) == 1
    assert len(clusters[0]) == 2
