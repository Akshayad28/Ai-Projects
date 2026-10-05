"""Backend unit tests for ShopBuddy AI Shopping Engine."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from app.catalog.engine import extract_attributes, resolve_category_from_text, seed_categories_if_empty
from app.core.config import get_settings
from app.db.models import Category, CategoryAttribute, CategoryRule
from app.db.session import SessionLocal, create_all
from app.main import app
from app.nlp.intent import parse_intent_with_rules
from app.providers.demo_provider import DemoProvider
from app.providers.registry import ProductProviderRegistry, compute_identity_key
from app.recommendations.engine import RecommendationEngine
from app.schemas.domain import ProviderSearchParams, RawOffer, RawProduct, SearchIntent


def test_intent_parser_laptop():
    query = "best laptop under ₹1 lakh for programming"
    intent = parse_intent_with_rules(query, country="IN", currency="INR")
    assert intent.budget.max == 100000.0
    assert intent.budget.currency == "INR"
    assert "programming" in intent.use_cases
    assert "laptop" in intent.provider_query.lower()


def test_intent_parser_running_shoes():
    query = "running shoes under ₹10,000"
    intent = parse_intent_with_rules(query, country="IN", currency="INR")
    assert intent.budget.max == 10000.0
    assert "running" in intent.use_cases


def test_identity_clustering():
    key1 = compute_identity_key("Sony", "Sony WH-1000XM5 Wireless Headphones Black", None, None)
    key2 = compute_identity_key("Sony", "Sony WH-1000XM5 Noise Cancelling Headphones - Black Edition", None, None)
    assert "sony" in key1 and "wh-1000xm5" in key1


def test_attribute_extractor():
    attrs = [
        CategoryAttribute(key="ram_gb", label="RAM", value_type="number", unit="GB", extract_patterns=[r"(\d{1,3})\s?GB\s*RAM"], source_keys=[]),
        CategoryAttribute(key="storage_gb", label="Storage", value_type="number", unit="GB", extract_patterns=[r"(\d{3,4})\s?GB\s*SSD"], source_keys=[]),
    ]
    title = "MacBook Pro 16GB RAM 512GB SSD"
    extracted = extract_attributes(title, "", {}, attrs)
    assert extracted.get("ram_gb") == 16
    assert extracted.get("storage_gb") == 512


def test_recommendation_scoring():
    rec = RecommendationEngine()
    prod = RawProduct(
        provider="test",
        external_id="p1",
        title="Laptop 16GB RAM",
        rating=4.7,
        review_count=500,
        specs={"ram_gb": 16},
        offers=[RawOffer(provider="test", retailer_name="Amazon", price_amount=80000.0, currency="INR", availability="in_stock")]
    )
    intent = parse_intent_with_rules("laptop under ₹90,000 for programming")
    rules = [
        CategoryRule(rule_type="requirement", payload={"match": ["programming"], "label": "16GB RAM for dev", "conditions": [{"attribute": "ram_gb", "op": ">=", "value": 16}]})
    ]
    ranked = rec.rank_products([prod], intent, {"requirement_match": 0.3, "price_fit": 0.3}, rules)
    assert len(ranked) == 1
    p, score, breakdown = ranked[0]
    assert breakdown["match_score"] >= 70
    assert any("budget" in r.lower() for r in breakdown["reasons"])


@pytest.mark.asyncio
async def test_search_api_no_fake_fallback_when_demo_mode_false():
    """Rule 38 & 42: When DEMO_MODE=false and no external providers configured, returns zero products and honest notice."""
    settings = get_settings()
    orig_demo = settings.demo_mode
    orig_google = settings.google_scraper_enabled
    orig_firecrawl = settings.firecrawl_enabled
    settings.demo_mode = False
    settings.google_scraper_enabled = False
    settings.firecrawl_enabled = False

    try:
        await create_all()
        async with SessionLocal() as session:
            await seed_categories_if_empty(session)

        transport = ASGITransport(app=app)
        with patch.object(ProductProviderRegistry, "search_parallel", new_callable=AsyncMock, return_value=([], [])):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                res = await ac.post("/api/v1/search", json={"query": "best laptop under ₹1 lakh for programming", "currency": "INR", "country": "IN"})
                assert res.status_code == 200
                data = res.json()
                assert len(data["products"]) == 0
                assert data["search_metadata"]["products_found"] == 0
                assert "no live products" in data["search_metadata"]["demo_notice"].lower() or "unavailable" in data["search_metadata"]["demo_notice"].lower()
    finally:
        settings.demo_mode = orig_demo
        settings.google_scraper_enabled = orig_google
        settings.firecrawl_enabled = orig_firecrawl


@pytest.mark.asyncio
async def test_search_api_zero_fake_products_even_if_demo_mode():
    """Verifies that demo products are never injected into production search results."""
    settings = get_settings()
    settings.demo_mode = True

    await create_all()
    async with SessionLocal() as session:
        await seed_categories_if_empty(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/search", json={"query": "nonexistent query for zero results", "currency": "INR", "country": "IN"})
        assert res.status_code == 200
        data = res.json()
        # Strictly zero fake/demo products returned
        assert all(not p.get("is_demo", False) for p in data["products"])
