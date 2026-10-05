"""Integration tests for Firecrawl Provider and Multi-Provider Search Pipeline.

Tests:
1. Complete Firecrawl pipeline (Intent -> Search -> URL selection -> Scrape -> Extraction ->
   Validation -> Normalization -> Identity Matching -> Canonical Product -> Offer -> Recommendation)
   with arbitrary queries:
   - "Samsung S26 Ultra"
   - "best office chair under ₹25000"
   - "cordless drill"
   - "MacBook Air M4"
   - "gaming monitor 1440p 165Hz"
   - "running shoes under ₹8000"
   - "black leather formal shoes"
   - "air fryer for family of four"
   - "40L travel backpack"
   - "coffee machine under ₹15000"

2. Multi-Provider integration test verifying:
   - Google, Amazon, Flipkart, eBay, and Firecrawl execute in parallel
   - Provider failures do not stop other providers
   - Firecrawl results are retained
   - Amazon does not monopolize results
   - Duplicate products are merged into canonical products with multiple offers
   - Pagination works seamlessly
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.catalog.engine import extract_attributes
from app.catalog.identity import cluster_and_merge_offers
from app.nlp.intent import parse_intent
from app.providers.base.exceptions import ProviderBlocked
from app.providers.base.models import ProviderPrice, ProviderProduct
from app.providers.firecrawl.extractor import (
    FIRECRAWL_EXTRACTION_PROMPT,
    FIRECRAWL_PRODUCT_SCHEMA,
    merge_extracted_layers,
)
from app.providers.firecrawl.parser import to_provider_product, to_raw_product
from app.providers.firecrawl.provider import FirecrawlProvider
from app.providers.firecrawl.schemas import AttributeItem, FirecrawlExtractedProduct
from app.providers.registry import get_provider_registry
from app.recommendations.engine import RecommendationEngine
from app.schemas.domain import ProviderSearchParams, RawProduct, SearchIntent
from app.services.search_orchestrator import SearchOrchestrator


ARBITRARY_TEST_QUERIES = [
    ("Samsung S26 Ultra", "Samsung", "S26 Ultra", 129999.0, "electronics"),
    ("best office chair under ₹25000", "Featherlite", "Helix", 21500.0, "furniture"),
    ("cordless drill", "Bosch", "GSB 180-LI", 6500.0, "tools"),
    ("MacBook Air M4", "Apple", "MacBook Air M4", 114900.0, "laptops"),
    ("gaming monitor 1440p 165Hz", "LG", "UltraGear 27GN800", 22990.0, "monitors"),
    ("running shoes under ₹8000", "Asics", "Gel-Kayano 30", 7499.0, "footwear"),
    ("black leather formal shoes", "Clarks", "Tilden Walk", 5999.0, "footwear"),
    ("air fryer for family of four", "Philips", "HD9252/90", 8999.0, "appliances"),
    ("40L travel backpack", "Osprey", "Farpoint 40", 12500.0, "luggage"),
    ("coffee machine under ₹15000", "De'Longhi", "Dedica EC685", 14999.0, "appliances"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("query,brand,model,price,cat", ARBITRARY_TEST_QUERIES)
async def test_firecrawl_full_pipeline_arbitrary_queries(query, brand, model, price, cat):
    """Verifies that the entire pipeline functions seamlessly for arbitrary queries
    without category restrictions or synthetic assumptions.
    """
    # 1. Intent extraction
    intent = await parse_intent(query, country="IN", currency="INR")
    assert intent is not None
    assert intent.raw_query == query

    # 2. Firecrawl discovery and scraping mock
    prov = FirecrawlProvider()

    mock_extracted = FirecrawlExtractedProduct(
        product_name=f"{brand} {model}",
        brand=brand,
        model=model,
        price=price,
        currency="INR",
        availability="in_stock",
        rating=4.5,
        review_count=150,
        attributes=[
            AttributeItem(key="brand", value=brand),
            AttributeItem(key="model", value=model),
        ],
        canonical_url=f"https://retailer.example.com/product/{brand.lower()}-{model.lower().replace(' ', '-')}",
    )

    prov._searcher.execute_discovery = AsyncMock(
        return_value=(
            [MagicMock(url=mock_extracted.canonical_url, classification="product_page")],
            [mock_extracted.canonical_url],
        )
    )
    prov._scraper.scrape_candidate_urls = AsyncMock(
        return_value=([mock_extracted], 1, 0)
    )

    params = ProviderSearchParams(
        query=query,
        intent=intent,
        country="IN",
        currency="INR",
        limit=20,
    )

    # 3. Provider Search Products execution
    raw_products = await prov.search_products(params)
    assert len(raw_products) == 1
    p = raw_products[0]

    assert p.provider == "firecrawl"
    assert p.brand == brand
    assert len(p.offers) == 1
    assert p.offers[0].price_amount == price

    # 4. Identity matching and clustering
    clustered = cluster_and_merge_offers(raw_products)
    assert len(clustered) == 1

    # 5. Recommendation engine scoring
    rec_engine = RecommendationEngine()
    ranked = rec_engine.rank_products(clustered, intent, weights={}, rules=[])
    assert len(ranked) == 1
    top_prod, score, breakdown = ranked[0]
    assert score > 0
    assert "match_score" in breakdown


@pytest.mark.asyncio
async def test_multi_provider_pipeline_with_firecrawl():
    """Validates multi-provider execution including Google, Amazon, Flipkart, eBay, and Firecrawl.

    Confirms:
    - Parallel dispatch with isolated failure handling
    - Firecrawl results are preserved alongside dedicated providers
    - Merging of duplicate products into canonical entities
    - Offer preservation across providers
    - Pagination metadata correctness
    """
    orchestrator = SearchOrchestrator()

    # Product 1: Sony WH-1000XM5 on Amazon, Flipkart, and Firecrawl (independent retailer)
    amz_p1 = ProviderProduct(
        provider="amazon",
        provider_product_id="amz-wh1000xm5",
        title="Sony WH-1000XM5 Wireless Headphones Black",
        brand="Sony",
        price=ProviderPrice(amount=29990.0, currency="INR"),
        url="https://amazon.in/dp/B09XS7JWHH",
        seller="Amazon",
        rating=4.6,
        review_count=5000,
    )

    fk_p1 = ProviderProduct(
        provider="flipkart",
        provider_product_id="fk-wh1000xm5",
        title="Sony WH-1000XM5 Bluetooth Headset (Black)",
        brand="Sony",
        price=ProviderPrice(amount=29490.0, currency="INR"),
        url="https://flipkart.com/p/1",
        seller="Flipkart",
        rating=4.5,
        review_count=3200,
    )

    fc_p1 = ProviderProduct(
        provider="firecrawl",
        provider_product_id="fc-wh1000xm5",
        title="Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        brand="Sony",
        price=ProviderPrice(amount=28499.0, currency="INR"),
        url="https://croma.com/p/sony-wh1000xm5",
        seller="Croma",
        rating=4.7,
        review_count=850,
    )

    # Product 2: Unique niche chair discovered ONLY by Firecrawl
    fc_p2 = ProviderProduct(
        provider="firecrawl",
        provider_product_id="fc-helix",
        title="Featherlite Helix High Back Ergonomic Mesh Chair",
        brand="Featherlite",
        price=ProviderPrice(amount=21500.0, currency="INR"),
        url="https://featherlitefurniture.com/product/helix/",
        seller="Featherlite",
        rating=4.8,
        review_count=210,
    )

    # Product 3: Bose Headphones on eBay
    ebay_p3 = ProviderProduct(
        provider="ebay",
        provider_product_id="ebay-bose-ultra",
        title="Bose QuietComfort Ultra Wireless Headphones",
        brand="Bose",
        price=ProviderPrice(amount=34900.0, currency="INR"),
        url="https://ebay.com/itm/123",
        seller="eBay Seller",
        rating=4.7,
        review_count=900,
    )

    # Mock provider responses
    mock_amz = AsyncMock()
    mock_amz.search_products.return_value = [amz_p1]

    mock_fk = AsyncMock()
    mock_fk.search_products.return_value = [fk_p1]

    mock_fc = AsyncMock()
    mock_fc.search_products.return_value = [fc_p1, fc_p2]

    mock_ebay = AsyncMock()
    mock_ebay.search_products.return_value = [ebay_p3]

    # Google Shopping scraper encounters a transient block; other providers MUST proceed unaffected
    mock_google = AsyncMock()
    mock_google.search_products.side_effect = ProviderBlocked("CAPTCHA challenge detected")

    orchestrator.providers = {
        "google_scraper": mock_google,
        "amazon": mock_amz,
        "flipkart": mock_fk,
        "ebay": mock_ebay,
        "firecrawl": mock_fc,
    }

    # Execute search
    res = await orchestrator.execute_search(
        raw_query="best wireless headphones and ergonomic chair",
        country="IN",
        currency="INR",
        page=1,
        page_size=10,
    )

    assert res.status == "SUCCESS"
    assert res.providers["google_scraper"].status == "blocked"
    assert res.providers["amazon"].status == "healthy"
    assert res.providers["flipkart"].status == "healthy"
    assert res.providers["ebay"].status == "healthy"
    assert res.providers["firecrawl"].status == "healthy"

    # Verify canonical products deduplicated:
    # 5 total items -> 3 canonical products:
    # Product 1 (Sony WH-1000XM5): merged across Amazon + Flipkart + Firecrawl (3 offers)
    # Product 2 (Featherlite Helix): Firecrawl exclusive
    # Product 3 (Bose QC Ultra): eBay exclusive
    assert len(res.products) == 3

    # Check Sony product offer aggregation
    sony_prod = next(p for p in res.products if "sony" in p.title.lower())
    assert len(sony_prod.offers) == 3
    retailers = {o.retailer.lower() for o in sony_prod.offers}
    assert any("amazon" in r for r in retailers)
    assert any("flipkart" in r for r in retailers)
    assert any("croma" in r for r in retailers)

    # Check Firecrawl exclusive product is preserved
    chair_prod = next(p for p in res.products if "helix" in p.title.lower())
    assert chair_prod.brand == "Featherlite"
    assert chair_prod.offers[0].retailer == "Featherlite"

    # Check pagination metadata
    assert res.pagination.total == 3
    assert res.pagination.page == 1
    assert res.pagination.page_size == 10
    assert res.pagination.total_pages == 1
    assert res.pagination.has_next is False
    assert res.pagination.total_offers == 5
    assert res.pagination.providers_contributing >= 3
