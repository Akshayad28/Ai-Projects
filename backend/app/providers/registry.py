"""Provider Registry and parallel search orchestrator.

Determines which live providers can answer a query, executes searches in parallel
with per-provider timeouts and token-bucket rate limits, collects normalized products,
deduplicates and merges offers into canonical products via ProductIdentityEngine,
and strictly enforces production integrity (NO fabricated product data).
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.catalog.identity import cluster_and_merge_offers, compute_identity_key
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.amazon import AmazonProvider
from app.providers.base import ProductProvider
from app.providers.bestbuy import BestBuyProvider
from app.providers.ebay import EbayProvider
from app.providers.firecrawl import FirecrawlProvider
from app.providers.flipkart import FlipkartProvider
from app.providers.google_scraper import GoogleScraperProvider
from app.providers.merchant_feed import MerchantFeedProvider
from app.providers.serp_shopping import SerpShoppingProvider
from app.schemas.domain import (
    ProviderSearchParams,
    ProviderSearchResult,
    RawOffer,
    RawProduct,
)
from app.providers.quick_commerce import (
    BigBasketProvider,
    BlinkitProvider,
    InstamartProvider,
    ZeptoProvider,
)
from app.providers.specialists import (
    CromaProvider,
    IkeaProvider,
    MyntraProvider,
    RelianceDigitalProvider,
)
from app.providers.capabilities import MarketplaceType, ProviderCapabilities, ProviderMetadata
from app.providers.discovery_engine import MarketplaceDiscoveryEngine


def provider_product_to_raw_product(p: Any) -> RawProduct:
    """Converts a legacy ProviderProduct into a standard catalog RawProduct."""
    if isinstance(p, RawProduct):
        return p
    offer = RawOffer(
        provider=p.provider,
        retailer_name=getattr(p, "seller", None) or p.provider.capitalize(),
        price_amount=p.price.amount if getattr(p, "price", None) else None,
        currency=p.price.currency if getattr(p, "price", None) and p.price.currency else "INR",
        original_price=p.price.original_price if getattr(p, "price", None) else None,
        availability=getattr(p, "availability", "in_stock") or "in_stock",
        url=p.url,
        confidence=0.9,
    )
    identifiers = getattr(p, "identifiers", None) or {}
    return RawProduct(
        provider=p.provider,
        external_id=getattr(p, "provider_product_id", None) or f"{p.provider}_{hashlib.md5(p.url.encode()).hexdigest()[:10]}",
        title=p.title,
        brand=getattr(p, "brand", None),
        model=getattr(p, "model", None),
        url=p.url,
        image_urls=getattr(p, "image_urls", None) or ([p.image_url] if getattr(p, "image_url", None) else []),
        rating=getattr(p, "rating", None),
        review_count=getattr(p, "review_count", None),
        gtin=identifiers.get("gtin"),
        upc=identifiers.get("upc"),
        ean=identifiers.get("ean"),
        mpn=identifiers.get("mpn"),
        asin=identifiers.get("asin"),
        sku=identifiers.get("sku"),
        specs=getattr(p, "specifications", None) or {},
        offers=[offer],
    )

log = get_logger(__name__)


class ProductProviderRegistry:
    def __init__(self) -> None:
        settings = get_settings()

        # All Live Providers across General Marketplaces, Quick Commerce, and Specialists
        self.providers: Dict[str, ProductProvider] = {
            GoogleScraperProvider.name: GoogleScraperProvider(),
            FirecrawlProvider.name: FirecrawlProvider(),
            AmazonProvider.name: AmazonProvider(),
            FlipkartProvider.name: FlipkartProvider(),
            EbayProvider.name: EbayProvider(),
            CromaProvider.name: CromaProvider(),
            RelianceDigitalProvider.name: RelianceDigitalProvider(),
            MyntraProvider.name: MyntraProvider(),
            IkeaProvider.name: IkeaProvider(),
            BlinkitProvider.name: BlinkitProvider(),
            ZeptoProvider.name: ZeptoProvider(),
            InstamartProvider.name: InstamartProvider(),
            BigBasketProvider.name: BigBasketProvider(),
            SerpShoppingProvider.name: SerpShoppingProvider(),
            BestBuyProvider.name: BestBuyProvider(),
            MerchantFeedProvider.name: MerchantFeedProvider(),
        }

        self.discovery_engine = MarketplaceDiscoveryEngine()
        self._register_discovery_metadata()

    def _register_discovery_metadata(self) -> None:
        """Configures marketplace routing metadata for all providers."""
        self.discovery_engine.register_metadata(
            GoogleScraperProvider.name,
            ProviderMetadata(
                name=GoogleScraperProvider.name,
                label=GoogleScraperProvider.label,
                marketplace_type=MarketplaceType.WEB_DISCOVERY,
                priority=10,
            ),
        )
        self.discovery_engine.register_metadata(
            FirecrawlProvider.name,
            ProviderMetadata(
                name=FirecrawlProvider.name,
                label=FirecrawlProvider.label,
                marketplace_type=MarketplaceType.WEB_DISCOVERY,
                priority=20,
            ),
        )
        self.discovery_engine.register_metadata(
            AmazonProvider.name,
            ProviderMetadata(
                name=AmazonProvider.name,
                label=AmazonProvider.label,
                marketplace_type=MarketplaceType.GENERAL_MARKETPLACE,
                countries={"IN", "US"},
                priority=30,
            ),
        )
        self.discovery_engine.register_metadata(
            FlipkartProvider.name,
            ProviderMetadata(
                name=FlipkartProvider.name,
                label=FlipkartProvider.label,
                marketplace_type=MarketplaceType.GENERAL_MARKETPLACE,
                countries={"IN"},
                priority=30,
            ),
        )
        self.discovery_engine.register_metadata(
            EbayProvider.name,
            ProviderMetadata(
                name=EbayProvider.name,
                label=EbayProvider.label,
                marketplace_type=MarketplaceType.GENERAL_MARKETPLACE,
                priority=40,
            ),
        )
        self.discovery_engine.register_metadata(
            CromaProvider.name,
            ProviderMetadata(
                name=CromaProvider.name,
                label=CromaProvider.label,
                marketplace_type=MarketplaceType.ELECTRONICS,
                countries={"IN"},
                priority=50,
            ),
        )
        self.discovery_engine.register_metadata(
            RelianceDigitalProvider.name,
            ProviderMetadata(
                name=RelianceDigitalProvider.name,
                label=RelianceDigitalProvider.label,
                marketplace_type=MarketplaceType.ELECTRONICS,
                countries={"IN"},
                priority=50,
            ),
        )
        self.discovery_engine.register_metadata(
            MyntraProvider.name,
            ProviderMetadata(
                name=MyntraProvider.name,
                label=MyntraProvider.label,
                marketplace_type=MarketplaceType.FASHION,
                countries={"IN"},
                priority=50,
            ),
        )
        self.discovery_engine.register_metadata(
            IkeaProvider.name,
            ProviderMetadata(
                name=IkeaProvider.name,
                label=IkeaProvider.label,
                marketplace_type=MarketplaceType.HOME_FURNITURE,
                countries={"IN"},
                priority=50,
            ),
        )
        # Quick Commerce
        for qc_cls in [BlinkitProvider, ZeptoProvider, InstamartProvider, BigBasketProvider]:
            self.discovery_engine.register_metadata(
                qc_cls.name,
                ProviderMetadata(
                    name=qc_cls.name,
                    label=qc_cls.label,
                    marketplace_type=MarketplaceType.QUICK_COMMERCE,
                    capabilities=ProviderCapabilities(quick_commerce=True, unit_economics=True, location_aware=True),
                    countries={"IN"},
                    priority=25,
                ),
            )

    def get_configured_providers(self, country: str, category: Optional[str]) -> List[ProductProvider]:
        configured: List[ProductProvider] = []
        for p in self.providers.values():
            if p.is_configured() and p.supports(country, category):
                configured.append(p)
        return configured

    def get_provider_status(self) -> List[dict]:
        status_list = []
        for name, p in self.providers.items():
            diag = p.get_diagnostics() if hasattr(p, "get_diagnostics") else {}
            status_val = diag.get("status", "healthy" if p.is_configured() else "unavailable")
            status_list.append({
                "name": name,
                "label": p.label,
                "configured": p.is_configured(),
                "status": status_val.lower(),
                "is_demo": getattr(p, "is_demo", False),
                "required_env": p.required_env,
                "countries": list(p.countries) if p.countries else ["all"],
                "rate_limit_per_second": p.rate_limit_per_second,
                "diagnostics": diag,
            })
        return status_list

    def get_provider(self, name: str) -> Optional[ProductProvider]:
        return self.providers.get(name)

    def list_registered_providers(self) -> List[str]:
        return list(self.providers.keys())

    def count_live_configured(self) -> int:
        return sum(1 for p in self.providers.values() if p.is_configured() and not getattr(p, "is_demo", False))

    async def search_parallel(self, params: ProviderSearchParams) -> Tuple[List[RawProduct], List[ProviderSearchResult]]:
        providers = self.get_configured_providers(params.country, params.intent.category)
        if not providers:
            log.warning(
                "No live providers configured or matching query constraints",
                extra={"country": params.country, "category": params.intent.category, "available_live_count": self.count_live_configured()}
            )
            return [], []

        timeout = get_settings().provider_timeout_seconds

        async def _run_provider(prov: ProductProvider) -> ProviderSearchResult:
            t0 = time.perf_counter()
            try:
                products = await asyncio.wait_for(prov.search_products(params), timeout=timeout)
                elapsed = int((time.perf_counter() - t0) * 1000)
                raw_products = [
                    p if isinstance(p, RawProduct) else provider_product_to_raw_product(p)
                    for p in (products or [])
                ]
                return ProviderSearchResult(
                    provider=prov.name,
                    products=raw_products,
                    status="ok",
                    latency_ms=elapsed
                )
            except asyncio.TimeoutError:
                elapsed = int((time.perf_counter() - t0) * 1000)
                log.warning(f"Provider {prov.name} timed out after {timeout}s")
                return ProviderSearchResult(
                    provider=prov.name,
                    products=[],
                    status="timeout",
                    error="Timeout exceeded",
                    latency_ms=elapsed
                )
            except Exception as exc:
                elapsed = int((time.perf_counter() - t0) * 1000)
                log.error(f"Provider {prov.name} error: {exc}")
                return ProviderSearchResult(
                    provider=prov.name,
                    products=[],
                    status="error",
                    error=str(exc),
                    latency_ms=elapsed
                )

        tasks = [_run_provider(p) for p in providers]
        results = await asyncio.gather(*tasks)

        # Collect products across all live providers
        all_raw_products: List[RawProduct] = []
        for r in results:
            all_raw_products.extend(r.products)

        # Execute canonical Product Identity Matching and offer aggregation
        deduped = cluster_and_merge_offers(all_raw_products)
        return deduped, results


_registry: Optional[ProductProviderRegistry] = None


def get_provider_registry() -> ProductProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProductProviderRegistry()
    return _registry

