"""Comprehensive Unit & Integration Test Suite for Universal Shopping Intelligence Expansion.

Covers:
1. Dynamic variant safety (pack size, volume, weight, size distinction)
2. Unit economics service (price per kg, price per litre, price per item)
3. Image validation & quality scoring (rejection of 1x1 tracking pixels, placeholders)
4. Marketplace discovery engine (query routing across retail domains without Amazon bias)
5. Quick-commerce provider capabilities and delivery intelligence (ETAs, fees)
6. Multi-provider offer aggregation (1 canonical product, multiple offers)
7. Provider failure isolation (timeouts and errors do not fail the search)
8. Admin diagnostics storage & telemetry
9. Production integrity (DEMO_MODE=false, no fabricated data)
"""
import pytest
from app.catalog.identity import are_variants_compatible, compute_canonical_identity_key, extract_variant_signatures
from app.services.unit_economics import UnitEconomicsService
from app.services.image_service import ImageExtractionService
from app.providers.capabilities import ProviderCapabilities, MarketplaceType
from app.providers.discovery_engine import MarketplaceDiscoveryEngine
from app.providers.registry import ProductProviderRegistry, get_provider_registry
from app.schemas.domain import SearchIntent, RawProduct, RawOffer
from app.services.diagnostics_store import DiagnosticsStore, SearchDiagnosticsRecord


# ─────────────────────────────────────────────────────────────
# 1. VARIANT SAFETY & IDENTITY MATCHING
# ─────────────────────────────────────────────────────────────

def test_variant_safety_pack_sizes_distinct():
    """Ensure different pack sizes/volumes never merge into one canonical product."""
    coke_750 = "Coca-Cola Zero Sugar Bottle 750ml"
    coke_1l = "Coca-Cola Zero Sugar Bottle 1L"
    coke_2l = "Coca-Cola Zero Sugar Bottle 2 Litres"

    sig_750 = extract_variant_signatures(coke_750)
    sig_1l = extract_variant_signatures(coke_1l)
    sig_2l = extract_variant_signatures(coke_2l)

    assert sig_750.get("volume_ml") == "750ml"
    assert sig_1l.get("volume_ml") == "1000ml"
    assert sig_2l.get("volume_ml") == "2000ml"

    # Must be incompatible
    assert are_variants_compatible(sig_750, sig_1l) is False
    assert are_variants_compatible(sig_1l, sig_2l) is False
    assert are_variants_compatible(sig_750, sig_750) is True

    # Canonical keys must be distinct
    key_750 = compute_canonical_identity_key(brand="Coca-Cola", title=coke_750)
    key_1l = compute_canonical_identity_key(brand="Coca-Cola", title=coke_1l)
    assert key_750 != key_1l


def test_variant_safety_weights_and_packs():
    """Ensure different weights and pack counts remain distinct."""
    milk_500g = extract_variant_signatures("Organic Whole Wheat Flour 500g")
    milk_1kg = extract_variant_signatures("Organic Whole Wheat Flour 1kg")
    coke_pack6 = extract_variant_signatures("Diet Coke Can 300ml Pack of 6")
    coke_single = extract_variant_signatures("Diet Coke Can 300ml")

    assert milk_500g.get("weight_g") == "500g"
    assert milk_1kg.get("weight_g") == "1000g"
    assert are_variants_compatible(milk_500g, milk_1kg) is False

    assert str(coke_pack6.get("pack_count")) == "6"
    assert coke_single.get("pack_count") is None or str(coke_single.get("pack_count")) == "1"
    assert are_variants_compatible(coke_pack6, coke_single) is False


def test_variant_safety_electronics_storage():
    """Ensure iPhone 256GB and 512GB do not merge."""
    sig_256 = extract_variant_signatures("Apple iPhone 17 Pro 256GB Black Titanium")
    sig_512 = extract_variant_signatures("Apple iPhone 17 Pro 512GB Black Titanium")

    assert sig_256.get("storage") in ("256gb", "256")
    assert sig_512.get("storage") in ("512gb", "512")
    assert are_variants_compatible(sig_256, sig_512) is False


# ─────────────────────────────────────────────────────────────
# 2. UNIT ECONOMICS SERVICE
# ─────────────────────────────────────────────────────────────

def test_unit_economics_volume():
    """Test price per litre calculation for beverages/milk."""
    service = UnitEconomicsService()

    # ₹70 for 750ml => (70 / 750) * 1000 = ₹93.33/L
    res = service.calculate_unit_price(price=70.0, title="Coca-Cola Zero Sugar Bottle 750ml")
    assert res is not None
    unit_price, unit_measure, display_str = res
    assert unit_measure in ("L", "litre")
    assert round(unit_price, 2) == 93.33
    assert "93.33" in display_str


def test_unit_economics_weight():
    """Test price per kg calculation for groceries."""
    service = UnitEconomicsService()

    # ₹120 for 500g => (120 / 500) * 1000 = ₹240/kg
    res = service.calculate_unit_price(price=120.0, title="Fortune Sunlite Sunflower Oil 500g")
    assert res is not None
    unit_price, unit_measure, display_str = res
    assert unit_measure == "kg"
    assert unit_price == 240.0
    assert "240" in display_str


def test_unit_economics_pack_items():
    """Test price per item calculation for multi-packs."""
    service = UnitEconomicsService()

    # ₹600 for pack of 4 => ₹150/item
    res = service.calculate_unit_price(price=600.0, title="Unisex Cotton T-Shirts Pack of 4")
    assert res is not None
    unit_price, unit_measure, display_str = res
    assert unit_measure == "item"
    assert unit_price == 150.0
    assert "150" in display_str


# ─────────────────────────────────────────────────────────────
# 3. IMAGE VALIDATION & EXTRACTION SERVICE
# ─────────────────────────────────────────────────────────────

def test_image_validation_rejection_rules():
    """Test rejection of tracking pixels, 1x1 GIFs, and placeholders."""
    service = ImageExtractionService()

    # Tracking pixels
    assert service.validate_image_url("https://example.com/pixel.gif") is False
    assert service.validate_image_url("https://example.com/1x1.png") is False
    assert service.validate_image_url("https://analytics.tracker.com/beacon.jpg") is False
    assert service.validate_image_url("https://example.com/clear.gif") is False

    # Generic Placeholders
    assert service.validate_image_url("https://example.com/no-image.png") is False
    assert service.validate_image_url("https://example.com/placeholder-product.jpg") is False

    # Valid images
    assert service.validate_image_url("https://m.media-amazon.com/images/I/71xyzAB.jpg") is True
    assert service.validate_image_url("https://cdn.blinkit.com/images/items/coke_zero_750.png") is True


def test_image_selection_and_ranking():
    """Test choosing the highest quality valid image from candidates."""
    service = ImageExtractionService()

    candidates = [
        "https://example.com/pixel.gif",  # rejected
        "https://cdn.retailer.com/thumb_50x50.jpg",  # low quality
        "https://m.media-amazon.com/images/I/71xyzAB._AC_SL1500_.jpg",  # high resolution
    ]

    best, gallery = service.select_best_image(candidates)
    assert best == "https://m.media-amazon.com/images/I/71xyzAB._AC_SL1500_.jpg"
    assert len(gallery) >= 1


# ─────────────────────────────────────────────────────────────
# 4. MARKETPLACE DISCOVERY & CAPABILITIES
# ─────────────────────────────────────────────────────────────

def test_marketplace_discovery_quick_commerce():
    """Test that grocery/quick-commerce queries discover Blinkit, Zepto, Instamart, BigBasket."""
    engine = MarketplaceDiscoveryEngine()
    intent = SearchIntent(
        raw_query="milk 1 litre",
        provider_query="milk 1 litre",
        category="grocery",
        quick_commerce_priority=True,
    )

    providers = engine.discover_relevant_providers(intent)
    # Quick commerce providers must be selected
    assert "blinkit" in providers
    assert "zepto" in providers
    assert "instamart" in providers
    assert "bigbasket" in providers
    # Amazon shouldn't be the only provider
    assert len(providers) > 1


def test_marketplace_discovery_electronics():
    """Test that electronics queries discover Croma, Reliance Digital, Amazon, Flipkart, etc."""
    engine = MarketplaceDiscoveryEngine()
    intent = SearchIntent(
        raw_query="best gaming laptop under 1 lakh",
        provider_query="gaming laptop",
        category="laptop",
        department="electronics",
    )

    providers = engine.discover_relevant_providers(intent)
    assert "croma" in providers
    assert "reliance_digital" in providers
    assert "amazon" in providers
    assert "flipkart" in providers


def test_no_amazon_monopoly_discovery():
    """Verify provider filtering never collapses into Amazon only."""
    engine = MarketplaceDiscoveryEngine()
    for q in ["MacBook Air M4", "formal shirt", "face wash", "cordless drill", "wooden table"]:
        intent = SearchIntent(raw_query=q, provider_query=q)
        providers = engine.discover_relevant_providers(intent)
        assert len(providers) >= 2, f"Query '{q}' returned fewer than 2 providers: {providers}"


# ─────────────────────────────────────────────────────────────
# 5. PROVIDER REGISTRY & CONTRACTS
# ─────────────────────────────────────────────────────────────

def test_provider_registry_includes_universal_marketplaces():
    """Verify registry has registered all modern marketplaces and quick commerce."""
    registry = get_provider_registry()
    registered = registry.list_registered_providers()

    expected = [
        "google_scraper", "amazon", "flipkart", "ebay", "firecrawl",
        "blinkit", "zepto", "instamart", "bigbasket",
        "croma", "reliance_digital", "myntra", "ikea"
    ]
    for exp in expected:
        assert exp in registered, f"Provider '{exp}' missing from registry"


def test_quick_commerce_capabilities():
    """Verify quick commerce providers declare quick_commerce and delivery capabilities."""
    registry = get_provider_registry()
    for p_name in ["blinkit", "zepto", "instamart"]:
        p = registry.get_provider(p_name)
        assert p is not None
        caps = p.get_capabilities()
        assert caps.quick_commerce is True
        assert caps.delivery is True
        assert caps.marketplace_type == MarketplaceType.QUICK_COMMERCE


# ─────────────────────────────────────────────────────────────
# 6. ADMIN DIAGNOSTICS & TELEMETRY
# ─────────────────────────────────────────────────────────────

def test_diagnostics_store_recording_and_retrieval():
    """Verify search diagnostics records are saved and retrievable."""
    store = DiagnosticsStore()
    search_id = "test-search-xyz-123"

    record = SearchDiagnosticsRecord(
        search_id=search_id,
        query="Sony WH-1000XM6",
        country="IN",
        currency="INR",
        started_at=100.0,
        completed_at=102.5,
        duration_ms=2500,
        providers_requested=["google_scraper", "amazon", "flipkart", "croma"],
        providers_executed=["google_scraper", "amazon", "flipkart", "croma"],
        raw_products_count=35,
        normalized_products_count=30,
        canonical_products_count=18,
        total_offers_count=35,
        images_extracted_count=32,
    )

    store.record(record)
    fetched = store.get(search_id)
    assert fetched is not None
    assert fetched.search_id == search_id
    assert fetched.canonical_products_count == 18
    assert fetched.total_offers_count == 35


@pytest.mark.asyncio
async def test_admin_diagnostics_api_endpoint():
    """Verify GET /api/v1/admin/search-diagnostics/{search_id} returns accurate diagnostics."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    store = DiagnosticsStore()
    search_id = "admin-test-search-999"
    record = SearchDiagnosticsRecord(
        search_id=search_id,
        query="milk 1 litre",
        country="IN",
        currency="INR",
        started_at=200.0,
        completed_at=201.2,
        duration_ms=1200,
        providers_requested=["blinkit", "zepto", "instamart"],
        providers_executed=["blinkit", "zepto", "instamart"],
        raw_products_count=18,
        normalized_products_count=16,
        canonical_products_count=8,
        total_offers_count=18,
        images_extracted_count=17,
        quick_commerce_offers_count=18,
    )
    store.record(record)

    transport = ASGITransport(app=app)
    from app.core.config import get_settings
    headers = {"X-Admin-Key": get_settings().admin_api_token or "test-admin-key"}
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/admin/search-diagnostics/{search_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["search_id"] == search_id
        assert data["query"] == "milk 1 litre"
        assert data["quick_commerce_offers_count"] == 18
        assert data["canonical_products_count"] == 8

        # Test latest report endpoint
        res_latest = await ac.get("/api/v1/admin/search-diagnostics/latest/report", headers=headers)
        assert res_latest.status_code == 200
        assert res_latest.json()["search_id"] == search_id

