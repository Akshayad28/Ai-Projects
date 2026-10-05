"""Unit tests for Firecrawl Provider.

Covers all 20 required validation scenarios:
1. Firecrawl search response parsing
2. Firecrawl scrape response parsing
3. Structured product extraction
4. JSON-LD extraction
5. Missing fields
6. Invalid price
7. Invalid URL
8. Missing image
9. Missing rating
10. Missing review count
11. Multiple variants
12. Product identity extraction
13. Retailer extraction
14. Offer extraction
15. Duplicate products
16. Provider timeout
17. Provider failure
18. API key missing
19. Empty Firecrawl response
20. Malformed Firecrawl response
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.catalog.identity import cluster_and_merge_offers
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.firecrawl.cache import FirecrawlCache
from app.providers.firecrawl.client import FirecrawlClient
from app.providers.firecrawl.exceptions import (
    FirecrawlAPIError,
    FirecrawlAuthError,
    FirecrawlBlockedError,
    FirecrawlRateLimitError,
    FirecrawlTimeoutError,
)
from app.providers.firecrawl.extractor import (
    extract_json_ld,
    extract_opengraph_metadata,
    merge_extracted_layers,
    parse_json_ld_product,
)
from app.providers.firecrawl.parser import (
    extract_retailer_info,
    parse_price_string,
    to_provider_product,
    to_raw_product,
)
from app.providers.firecrawl.provider import FirecrawlProvider
from app.providers.firecrawl.schemas import (
    AttributeItem,
    FirecrawlExtractedProduct,
    FirecrawlSearchResultItem,
    URLClassification,
)
from app.providers.firecrawl.validators import (
    classify_url,
    clean_availability,
    is_valid_url,
    validate_extracted_product,
)
from app.schemas.domain import ProviderSearchParams, SearchIntent


# 1. Firecrawl search response parsing
@pytest.mark.asyncio
async def test_search_response_parsing():
    client = FirecrawlClient(api_key="fc-test-key")
    client._app = MagicMock()
    client._app.search = AsyncMock(
        return_value={
            "success": True,
            "data": [
                {
                    "title": "Ergonomic Office Chair - Green Soul",
                    "url": "https://greensoul.online/products/jupiter-chair",
                    "description": "High back mesh office chair with lumbar support under ₹25000",
                },
                {
                    "title": "Featherlite Helix Chair",
                    "url": "https://featherlitefurniture.com/product/helix/",
                    "description": "Premium ergonomic seating",
                },
            ],
        }
    )

    results = await client.search("best office chair under ₹25000")
    assert len(results) == 2
    assert results[0]["title"] == "Ergonomic Office Chair - Green Soul"
    assert results[1]["url"] == "https://featherlitefurniture.com/product/helix/"


# 2. Firecrawl scrape response parsing
@pytest.mark.asyncio
async def test_scrape_response_parsing():
    client = FirecrawlClient(api_key="fc-test-key")
    client._app = MagicMock()

    mock_resp = MagicMock()
    mock_resp.html = "<html><body><h1>Test Chair</h1></body></html>"
    mock_resp.json_field = {
        "product_name": "Test Ergonomic Chair",
        "brand": "TestBrand",
        "price": 14999.0,
        "currency": "INR",
    }
    client._app.scrape_url = AsyncMock(return_value=mock_resp)

    res = await client.scrape_url("https://example.com/product/chair")
    assert res.html is not None
    assert res.json_field["product_name"] == "Test Ergonomic Chair"
    assert res.json_field["price"] == 14999.0


# 3. Structured product extraction
def test_structured_product_extraction():
    sdk_json = {
        "product_name": "ASUS TUF Gaming VG27AQ 27 inch 165Hz Monitor",
        "brand": "ASUS",
        "model": "VG27AQ",
        "price": 26999.0,
        "currency": "INR",
        "attributes": [
            {"key": "screen_size", "value": "27 inch"},
            {"key": "refresh_rate", "value": "165 Hz"},
            {"key": "resolution", "value": "2560 x 1440"},
        ],
        "image_url": "https://example.com/monitor.jpg",
    }

    merged = merge_extracted_layers(
        json_ld_prod=None,
        og_meta={},
        sdk_json=sdk_json,
        source_url="https://example.com/products/vg27aq",
    )

    assert merged.product_name == "ASUS TUF Gaming VG27AQ 27 inch 165Hz Monitor"
    assert merged.brand == "ASUS"
    assert merged.price == 26999.0
    assert len(merged.attributes) == 3
    assert merged.attributes[0].key == "screen_size"
    assert merged.attributes[0].value == "27 inch"


# 4. JSON-LD extraction
def test_json_ld_extraction():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org/",
          "@type": "Product",
          "name": "Sony WH-1000XM5 Wireless Headphones",
          "image": ["https://example.com/sony.jpg"],
          "description": "Noise cancelling headphones",
          "sku": "WH1000XM5B",
          "mpn": "WH1000XM5",
          "gtin13": "4548736132566",
          "brand": {
            "@type": "Brand",
            "name": "Sony"
          },
          "offers": {
            "@type": "Offer",
            "price": "29990",
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock"
          },
          "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.6",
            "reviewCount": "1250"
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    raw_ld = extract_json_ld(html)
    assert raw_ld is not None
    assert raw_ld["@type"] == "Product"

    prod = parse_json_ld_product(raw_ld)
    assert prod.product_name == "Sony WH-1000XM5 Wireless Headphones"
    assert prod.brand == "Sony"
    assert prod.gtin == "4548736132566"
    assert prod.price == 29990.0
    assert prod.currency == "INR"
    assert prod.availability == "in_stock"
    assert prod.rating == 4.6
    assert prod.review_count == 1250


# 5. Missing fields (A product with name + URL is still valid)
def test_missing_optional_fields_valid():
    prod = FirecrawlExtractedProduct(
        product_name="Minimalist Wooden Desk",
        product_url="https://example.com/desk",
    )
    is_valid, reason = validate_extracted_product(prod)
    assert is_valid is True
    assert reason is None


# 6. Invalid price (negative or non-numeric)
def test_invalid_price_rejected():
    prod = FirecrawlExtractedProduct(
        product_name="Chair with negative price",
        product_url="https://example.com/chair",
        price=-500.0,
    )
    is_valid, reason = validate_extracted_product(prod)
    assert is_valid is False
    assert "Invalid non-numeric or negative price" in reason


# 7. Invalid URL rejected
def test_invalid_url_rejected():
    assert is_valid_url("not-a-url") is False
    assert is_valid_url("ftp://example.com") is False
    assert is_valid_url("https://example.com/product") is True

    prod = FirecrawlExtractedProduct(
        product_name="Valid Name",
        product_url="invalid-url-path",
    )
    is_valid, reason = validate_extracted_product(prod)
    assert is_valid is False
    assert "Invalid product URL" in reason


# 8. Missing image gracefully handled
def test_missing_image_handled():
    prod = FirecrawlExtractedProduct(
        product_name="Chair without image",
        product_url="https://example.com/chair",
        image_url=None,
    )
    is_valid, _ = validate_extracted_product(prod)
    assert is_valid is True
    assert prod.image_url is None

    raw = to_raw_product(prod, "https://example.com/chair")
    assert raw.image_urls == []


# 9. Missing rating gracefully handled
def test_missing_rating_handled():
    prod = FirecrawlExtractedProduct(
        product_name="Unrated Product",
        product_url="https://example.com/p",
        rating=None,
    )
    is_valid, _ = validate_extracted_product(prod)
    assert is_valid is True
    raw = to_raw_product(prod, "https://example.com/p")
    assert raw.rating is None


# 10. Missing review count gracefully handled
def test_missing_review_count_handled():
    prod = FirecrawlExtractedProduct(
        product_name="Product No Reviews",
        product_url="https://example.com/p",
        review_count=None,
    )
    is_valid, _ = validate_extracted_product(prod)
    assert is_valid is True
    raw = to_raw_product(prod, "https://example.com/p")
    assert raw.review_count is None


# 11. Multiple variants are preserved
def test_multiple_variants_preserved():
    p1 = FirecrawlExtractedProduct(
        product_name="MacBook Air M3 16GB 512GB Space Gray",
        product_url="https://retailer.com/macbook-16-512",
        price=124900.0,
        attributes=[
            AttributeItem(key="ram", value="16GB"),
            AttributeItem(key="storage", value="512GB"),
        ],
    )
    p2 = FirecrawlExtractedProduct(
        product_name="MacBook Air M3 24GB 512GB Silver",
        product_url="https://retailer.com/macbook-24-512",
        price=144900.0,
        attributes=[
            AttributeItem(key="ram", value="24GB"),
            AttributeItem(key="storage", value="512GB"),
        ],
    )

    raw1 = to_raw_product(p1, "https://retailer.com/macbook-16-512")
    raw2 = to_raw_product(p2, "https://retailer.com/macbook-24-512")

    # Clustered via ProductIdentityEngine
    clustered = cluster_and_merge_offers([raw1, raw2])
    # Different RAM variants must NOT merge into a single canonical product
    assert len(clustered) == 2


# 12. Product identity extraction
def test_product_identity_extraction():
    prod = FirecrawlExtractedProduct(
        product_name="Samsung Galaxy S24 Ultra",
        brand="Samsung",
        gtin="8806095312345",
        asin="B0CQ2BBHLF",
        mpn="SM-S928B",
        product_url="https://example.com/s24u",
    )
    raw = to_raw_product(prod, "https://example.com/s24u")
    assert raw.gtin == "8806095312345"
    assert raw.asin == "B0CQ2BBHLF"
    assert raw.mpn == "SM-S928B"
    assert raw.brand == "Samsung"


# 13. Retailer extraction
def test_retailer_extraction():
    domain1, name1 = extract_retailer_info("https://www.amazon.in/dp/B09XS7JWHH")
    assert name1 == "Amazon India"

    domain2, name2 = extract_retailer_info("https://featherlitefurniture.com/product/helix/")
    assert name2 == "Featherlite"

    domain3, name3 = extract_retailer_info("https://greensoul.online/products/jupiter")
    assert name3 == "Green Soul"

    domain4, name4 = extract_retailer_info("https://www.unknownstore.co/products/chair")
    assert name4 == "Unknownstore"


# 14. Offer extraction
def test_offer_extraction():
    prod = FirecrawlExtractedProduct(
        product_name="Featherlite Helix Mesh Chair",
        price=21500.0,
        currency="INR",
        original_price=26000.0,
        availability="in_stock",
        shipping_cost=0.0,
        delivery_information="Free Delivery in 3-5 days",
        return_policy="10-day replacement",
        warranty="3 Years Manufacturer Warranty",
        product_url="https://featherlitefurniture.com/product/helix/",
    )
    raw = to_raw_product(prod, "https://featherlitefurniture.com/product/helix/")
    assert len(raw.offers) == 1
    offer = raw.offers[0]
    assert offer.retailer_name == "Featherlite"
    assert offer.price_amount == 21500.0
    assert offer.currency == "INR"
    assert offer.availability == "in_stock"
    assert offer.warranty == "3 Years Manufacturer Warranty"
    assert offer.delivery_estimate == "Free Delivery in 3-5 days"


# 15. Duplicate products merge into one canonical product with multiple offers
def test_duplicate_products_merge():
    # Sony WH-1000XM5 on Amazon and on a Firecrawl-discovered independent retailer
    raw_amz = to_raw_product(
        FirecrawlExtractedProduct(
            product_name="Sony WH-1000XM5 Wireless Headphones",
            brand="Sony",
            model="WH-1000XM5",
            price=29990.0,
            currency="INR",
            product_url="https://www.amazon.in/dp/B09XS7JWHH",
        ),
        "https://www.amazon.in/dp/B09XS7JWHH",
    )
    raw_amz.provider = "amazon"

    raw_firecrawl = to_raw_product(
        FirecrawlExtractedProduct(
            product_name="Sony WH-1000XM5 Wireless Headphones",
            brand="Sony",
            model="WH-1000XM5",
            price=28999.0,
            currency="INR",
            product_url="https://croma.com/p/sony-wh-1000xm5",
        ),
        "https://croma.com/p/sony-wh-1000xm5",
    )
    raw_firecrawl.provider = "firecrawl"

    clustered = cluster_and_merge_offers([raw_amz, raw_firecrawl])
    assert len(clustered) == 1
    canonical = clustered[0]
    assert len(canonical.offers) == 2
    retailers = {o.retailer_name for o in canonical.offers}
    assert "Amazon India" in retailers
    assert "Croma" in retailers


# 16. Provider timeout handling
@pytest.mark.asyncio
async def test_provider_timeout_handling():
    client = FirecrawlClient(api_key="fc-test-key", timeout_seconds=0.01)
    client._app = MagicMock()

    async def _slow_search(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.1)
        return []

    client._app.search = _slow_search

    with pytest.raises(ProviderTimeout):
        await client.search("query")


# 17. Provider failure handling
@pytest.mark.asyncio
async def test_provider_failure_handling():
    prov = FirecrawlProvider()
    prov._settings.firecrawl_api_key = "fc-test-key"
    prov._settings.firecrawl_enabled = True
    prov._searcher.execute_discovery = AsyncMock(side_effect=Exception("API gateway connection refused"))

    params = ProviderSearchParams(
        query="gaming monitor 1440p",
        intent=SearchIntent(raw_query="gaming monitor 1440p", provider_query="gaming monitor 1440p"),
        country="IN",
        currency="INR",
    )

    with pytest.raises(ProviderUnavailable):
        await prov.search_products(params)


# 18. API key missing results in UNAVAILABLE status
def test_api_key_missing_unavailable():
    with patch("app.providers.firecrawl.provider.get_settings") as mock_settings:
        mock_settings.return_value.firecrawl_api_key = None
        mock_settings.return_value.firecrawl_enabled = True
        mock_settings.return_value.firecrawl_request_timeout_seconds = 30.0
        mock_settings.return_value.firecrawl_concurrency = 5
        mock_settings.return_value.firecrawl_cache_ttl_seconds = 900

        prov = FirecrawlProvider()
        assert prov.is_configured() is False
        assert prov.diagnostics.status == "UNAVAILABLE"


# 19. Empty Firecrawl response handled gracefully
@pytest.mark.asyncio
async def test_empty_firecrawl_response():
    client = FirecrawlClient(api_key="fc-test-key")
    client._app = MagicMock()
    client._app.search = AsyncMock(return_value={"success": True, "data": []})

    results = await client.search("arbitrary obscure query")
    assert results == []


# 20. Malformed Firecrawl response handled safely
@pytest.mark.asyncio
async def test_malformed_firecrawl_response():
    client = FirecrawlClient(api_key="fc-test-key")
    client._app = MagicMock()
    client._app.search = AsyncMock(return_value="not-a-dict-or-list")

    results = await client.search("arbitrary query")
    assert results == []
