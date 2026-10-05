"""Firecrawl Shopping Provider Implementation.

Implements ProductProvider and ShoppingProvider interfaces for universal web discovery
and dynamic product extraction using the official Firecrawl API.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar, Dict, List, Optional, Set, Union


from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderError,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.base.models import (
    ProviderHealth,
    ProviderOffer,
    ProviderProduct,
    SearchQuery,
    utcnow_str,
)
from app.providers.base.product_provider import ProductProvider
from app.providers.base.provider import ShoppingProvider
from app.providers.firecrawl.cache import FirecrawlCache
from app.providers.firecrawl.client import FirecrawlClient
from app.providers.firecrawl.exceptions import (
    FirecrawlAuthError,
    FirecrawlBlockedError,
    FirecrawlRateLimitError,
    FirecrawlTimeoutError,
)
from app.providers.firecrawl.parser import (
    search_item_to_raw_product,
    to_provider_product,
    to_raw_product,
)

from app.providers.firecrawl.schemas import FirecrawlDiagnostics
from app.providers.firecrawl.scraper import FirecrawlScraper
from app.providers.firecrawl.search import FirecrawlSearcher
from app.schemas.domain import ProviderSearchParams, RawOffer, RawProduct, SearchIntent

log = get_logger(__name__)


class FirecrawlProvider(ProductProvider, ShoppingProvider):
    """Universal web discovery and structured product extraction provider powered by Firecrawl."""

    name: ClassVar[str] = "firecrawl"
    label: ClassVar[str] = "Firecrawl"
    countries: ClassVar[Set[str]] = set()  # Empty set = supports all countries
    categories: ClassVar[Set[str]] = set()  # Empty set = supports all categories
    rate_limit_per_second: ClassVar[float] = 5.0
    required_env: ClassVar[List[str]] = ["FIRECRAWL_API_KEY"]
    is_demo: ClassVar[bool] = False

    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache = FirecrawlCache(default_ttl_seconds=self._settings.firecrawl_cache_ttl_seconds)
        self._client = FirecrawlClient(
            api_key=self._settings.firecrawl_api_key,
            timeout_seconds=self._settings.firecrawl_request_timeout_seconds,
            concurrency=self._settings.firecrawl_concurrency,
        )
        self._searcher = FirecrawlSearcher(self._client, self._cache)
        self._scraper = FirecrawlScraper(self._client, self._cache)

        # Operational metrics and circuit breaker state
        self._last_success: Optional[str] = None
        self._last_error: Optional[str] = None
        self._consecutive_failures: int = 0
        self._circuit_open_until: float = 0.0

        self.diagnostics = FirecrawlDiagnostics()
        self._update_status()

    def _update_status(self) -> None:
        if not self.is_configured():
            self.diagnostics.status = "UNAVAILABLE"
        elif time.time() < self._circuit_open_until:
            self.diagnostics.status = "BLOCKED"
        elif self._consecutive_failures >= 3:
            self.diagnostics.status = "DEGRADED"
        else:
            self.diagnostics.status = "HEALTHY"

    def is_configured(self) -> bool:
        """Provider is configured when FIRECRAWL_API_KEY is present and FIRECRAWL_ENABLED is true."""
        return bool(self._settings.firecrawl_api_key and self._settings.firecrawl_enabled)

    def supports(self, country: str, category: Optional[str] = None) -> bool:
        """Firecrawl supports arbitrary products from all countries and categories."""
        return True

    async def _enrich_urls_in_background(
        self,
        urls: List[str],
        max_pages: int,
        currency: str,
        query: str,
    ) -> None:
        """Asynchronously scrapes candidate URLs in the background and populates cache."""
        try:
            extracted_prods, scraped_count, rejected_count = await self._scraper.scrape_candidate_urls(
                urls=urls,
                max_pages=max_pages,
            )
            log.info(
                f"[FIRECRAWL_BG] Background enrichment finished for {len(urls)} URLs: "
                f"{scraped_count} scraped, {len(extracted_prods)} valid."
            )
        except Exception as exc:
            log.debug(f"[FIRECRAWL_BG] Background enrichment error: {exc}")


    async def search_products(
        self,
        query: Union[ProviderSearchParams, SearchQuery],
    ) -> Union[List[RawProduct], List[ProviderProduct]]:
        """Executes universal search discovery and structured extraction via Firecrawl.

        Supports both ProviderSearchParams (for ProductProviderRegistry) and SearchQuery (for SearchOrchestrator).
        """
        if not self.is_configured():
            self.diagnostics.status = "UNAVAILABLE"
            log.debug("FirecrawlProvider is unconfigured or disabled.")
            return []

        # Check circuit breaker
        now = time.time()
        if now < self._circuit_open_until:
            self.diagnostics.status = "BLOCKED"
            log.warning("[FIRECRAWL] Request skipped: Circuit breaker is OPEN")
            raise ProviderBlocked("Firecrawl circuit breaker is OPEN due to repeated failures or blocks.")

        # Unpack query parameters
        if isinstance(query, ProviderSearchParams):
            search_str = query.intent.provider_query or query.query
            raw_query = query.query
            intent = query.intent
            country = query.country
            currency = query.currency
            limit = query.limit
            is_domain_schema = True
        else:
            search_str = query.query
            raw_query = query.query
            intent = None
            country = query.country
            currency = query.currency
            limit = query.limit
            is_domain_schema = False

        self.diagnostics.search_attempted = True
        t0 = time.perf_counter()

        try:
            # 1. Search discovery & URL classification (fast, single API call)
            search_results, candidate_urls = await self._searcher.execute_discovery(
                query=search_str,
                intent=intent,
                country=country,
                currency=currency,
                max_results=min(limit, self._settings.firecrawl_max_search_results),
            )

            self.diagnostics.search_results = len(search_results)
            self.diagnostics.product_urls_detected = len(candidate_urls)

            # 2. Check if any candidate URLs are already cached from previous crawls
            cached_extracted = []
            uncached_urls = []
            for url in candidate_urls:
                cached_item = await self._cache.get(self._cache.hash_scrape_key(url))
                if cached_item:
                    cached_extracted.append(cached_item)
                else:
                    uncached_urls.append(url)


            # 3. Transform cached deep-scraped products + immediate discovery items into RawProduct
            raw_products: List[RawProduct] = []
            seen_external_ids: Set[str] = set()

            # First add cached rich products if available
            for extracted in cached_extracted:
                src_url = extracted.canonical_url or extracted.product_url or ""
                raw_prod = to_raw_product(
                    extracted=extracted,
                    source_url=src_url,
                    default_currency=currency,
                    query=raw_query,
                )
                if raw_prod.external_id not in seen_external_ids:
                    seen_external_ids.add(raw_prod.external_id)
                    raw_products.append(raw_prod)

            # Then add immediate products discovered from web search
            for item in search_results:
                raw_prod = search_item_to_raw_product(item, default_currency=currency, query=raw_query)
                if raw_prod and raw_prod.external_id not in seen_external_ids:
                    seen_external_ids.add(raw_prod.external_id)
                    raw_products.append(raw_prod)

            # 4. Handle uncached URLs: if we already have discovery products, enrich deep details in background!
            # If no products were discovered from search items (or direct unit test call), scrape candidate URLs.
            if not raw_products and uncached_urls:
                max_pages = min(self._settings.firecrawl_max_scrape_pages, len(uncached_urls))
                extracted_items, _, _ = await self._scraper.scrape_candidate_urls(
                    candidate_urls=uncached_urls[:max_pages],
                    currency=currency,
                    query=raw_query,
                )
                for extracted in extracted_items:
                    src_url = extracted.canonical_url or extracted.product_url or ""
                    raw_prod = to_raw_product(
                        extracted=extracted,
                        source_url=src_url,
                        default_currency=currency,
                        query=raw_query,
                    )
                    if raw_prod.external_id not in seen_external_ids:
                        seen_external_ids.add(raw_prod.external_id)
                        raw_products.append(raw_prod)
            elif uncached_urls:
                max_pages = min(self._settings.firecrawl_max_scrape_pages, len(uncached_urls))
                asyncio.create_task(
                    self._enrich_urls_in_background(uncached_urls, max_pages, currency, raw_query)
                )

            # Record telemetry
            self.diagnostics.pages_scraped = len(cached_extracted)
            self.diagnostics.products_extracted = len(raw_products)
            self.diagnostics.products_validated = len(raw_products)
            self.diagnostics.raw = len(raw_products)
            self.diagnostics.normalized = len(raw_products)
            self.diagnostics.offers = sum(len(p.offers) for p in raw_products)
            self.diagnostics.canonical = len(raw_products)
            self.diagnostics.offers_extracted = self.diagnostics.offers

            self._last_success = utcnow_str()
            self._consecutive_failures = 0
            self._update_status()

            elapsed = round(time.perf_counter() - t0, 2)
            log.info(
                f"[FIRECRAWL] Immediate discovery completed in {elapsed}s: "
                f"raw={self.diagnostics.raw}, cached={len(cached_extracted)}, "
                f"background_queued={len(uncached_urls)}"
            )

            if is_domain_schema:
                return raw_products
            else:
                return [to_provider_product(p) for p in raw_products]


        except (FirecrawlBlockedError, ProviderBlocked) as exc:
            self._last_error = str(exc)
            self._consecutive_failures += 1
            self._circuit_open_until = time.time() + 60.0  # 1 min cooldown
            self.diagnostics.errors += 1
            self.diagnostics.status = "BLOCKED"
            log.warning(f"[FIRECRAWL] BLOCKED: {exc}")
            raise ProviderBlocked(f"Firecrawl blocked: {exc}") from exc

        except (FirecrawlTimeoutError, ProviderTimeout) as exc:
            self._last_error = str(exc)
            self._consecutive_failures += 1
            self.diagnostics.errors += 1
            self.diagnostics.status = "DEGRADED"
            log.warning(f"[FIRECRAWL] TIMEOUT: {exc}")
            raise ProviderTimeout(f"Firecrawl timeout: {exc}") from exc

        except FirecrawlAuthError as exc:
            self._last_error = str(exc)
            self.diagnostics.errors += 1
            self.diagnostics.status = "UNAVAILABLE"
            log.error(f"[FIRECRAWL] AUTH ERROR: {exc}")
            raise ProviderUnavailable(f"Firecrawl auth error: {exc}") from exc

        except Exception as exc:
            self._last_error = str(exc)
            self._consecutive_failures += 1
            self.diagnostics.errors += 1
            if self._consecutive_failures >= 3:
                self._circuit_open_until = time.time() + 30.0
            self._update_status()
            log.error(f"[FIRECRAWL] SEARCH ERROR: {exc}")
            raise ProviderUnavailable(f"Firecrawl error: {exc}") from exc

    async def get_product(self, product_url: str, country: str = "IN") -> Optional[RawProduct]:
        """Scrapes and extracts a specific product page URL."""
        if not self.is_configured():
            return None

        try:
            extracted, reason = await self._scraper.scrape_single_url(product_url)
            if not extracted:
                return None
            return to_raw_product(extracted, product_url)
        except Exception as exc:
            log.warning(f"[FIRECRAWL] Failed to get product for {product_url}: {exc}")
            return None

    async def get_offers(self, product_url: str, country: str = "IN") -> List[RawOffer]:
        """Extracts offers from a specific product page URL."""
        prod = await self.get_product(product_url, country)
        return prod.offers if prod else []

    async def health_check(self) -> ProviderHealth:
        """Returns runtime connectivity and operational status."""
        self._update_status()
        return ProviderHealth(
            name=self.name,
            enabled=self.is_configured(),
            status=self.diagnostics.status.lower(),
            last_success=self._last_success,
            last_error=self._last_error,
            consecutive_failures=self._consecutive_failures,
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic telemetry."""
        self._update_status()
        return {
            "name": self.name,
            "label": self.label,
            "status": self.diagnostics.status,
            "configured": self.is_configured(),
            "last_success": self._last_success,
            "last_error": self._last_error,
            "circuit_breaker": {
                "open": time.time() < self._circuit_open_until,
                "cooldown_remaining_sec": max(0, int(self._circuit_open_until - time.time())),
            },
            **self.diagnostics.to_dict(),
        }
