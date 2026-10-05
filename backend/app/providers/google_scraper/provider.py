"""Google Shopping Scraper Provider.

Implements ProductProvider and ShoppingProvider interfaces for browser-based
Google Shopping product discovery with circuit breaker, rate limiting, and layout resilience.
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Set, Union

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resilience import provider_bucket
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
from app.providers.google_scraper.models import CircuitState
from app.providers.google_scraper.scraper import GoogleScraper
from app.schemas.domain import ProviderSearchParams, RawOffer, RawProduct

log = get_logger(__name__)


class GoogleScraperProvider(ProductProvider, ShoppingProvider):
    """Retrieves real product data from Google Shopping using Playwright browser automation."""

    name: ClassVar[str] = "google_scraper"
    label: ClassVar[str] = "Google Shopping"
    countries: ClassVar[Set[str]] = {"IN", "US", "GB", "DE", "AE", "SG", "CA", "AU", "ALL"}
    rate_limit_per_second: ClassVar[float] = 1.0
    required_env: ClassVar[List[str]] = ["GOOGLE_SCRAPER_ENABLED"]
    is_demo: ClassVar[bool] = False

    def __init__(self) -> None:
        self._scraper = GoogleScraper()
        self._settings = get_settings()
        self._last_success: Optional[str] = None
        self._last_error: Optional[str] = None
        self._status = "healthy"

    def is_configured(self) -> bool:
        """Provider is active when GOOGLE_SCRAPER_ENABLED=true (default: true). No API key required."""
        return bool(self._settings.google_scraper_enabled)

    def supports(self, country: str, category: Optional[str] = None) -> bool:
        if not country:
            return True
        return country.upper() in self.countries or "ALL" in self.countries

    async def search_products(
        self,
        query: Union[ProviderSearchParams, SearchQuery],
    ) -> Union[List[RawProduct], List[ProviderProduct]]:
        """Searches Google Shopping and returns normalized product records.

        Seamlessly supports both ProviderSearchParams (for ProductProviderRegistry)
        and SearchQuery (for SearchOrchestrator).
        """
        if not self.is_configured():
            log.debug("GoogleScraperProvider is disabled via configuration.")
            return []

        # Check circuit breaker before acquiring rate limiter
        if self._scraper.circuit_breaker.state == CircuitState.OPEN:
            if not await self._scraper.circuit_breaker.can_request():
                self._status = "blocked"
                reason = self._scraper.circuit_breaker.last_block_reason or "CIRCUIT_OPEN"
                log.warning(f"GoogleScraperProvider skipped: circuit breaker OPEN ({reason})")
                raise ProviderBlocked(f"Google circuit breaker is OPEN ({reason})")

        # Throttling via token bucket
        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        # Unpack query parameters
        if isinstance(query, ProviderSearchParams):
            search_str = query.intent.provider_query or query.query
            country = query.country
            currency = query.currency
            limit = query.limit
            is_domain_schema = True
        else:
            search_str = query.query
            country = query.country
            currency = query.currency
            limit = query.limit
            is_domain_schema = False

        try:
            items = await self._scraper.scrape_search(
                query=search_str,
                country=country,
                currency=currency,
                max_results=min(limit, self._settings.google_scraper_max_results),
            )

            self._last_success = utcnow_str()

            # Check if extraction health reported degradation
            if self._scraper.last_health and self._scraper.last_health.is_degraded():
                self._status = "degraded"
            else:
                self._status = "healthy"

            if is_domain_schema:
                # Return pipeline's RawProduct records
                return [item.to_raw_product() for item in items]
            else:
                # Return ShoppingProvider's ProviderProduct records
                return [item.to_provider_product() for item in items]

        except ProviderBlocked as exc:
            self._last_error = str(exc)
            self._status = "blocked"
            log.warning(f"GoogleScraperProvider is marked BLOCKED: {exc}")
            raise
        except ProviderTimeout as exc:
            self._last_error = str(exc)
            self._status = "timeout"
            log.warning(f"GoogleScraperProvider TIMED OUT: {exc}")
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self._status = "degraded"
            log.warning(f"GoogleScraperProvider search failed: {exc}")
            raise ProviderUnavailable(f"Google error: {exc}") from exc

    async def get_product(self, product_url: str, country: str = "IN") -> Optional[Any]:
        """Gracefully unsupported for arbitrary Google Search redirect URLs."""
        return None

    async def get_offers(self, product_url: str, country: str = "IN") -> List[Any]:
        """Google Shopping search returns multi-retailer offers directly in search cards."""
        return []

    async def health_check(self) -> ProviderHealth:
        """Returns runtime provider status and last execution telemetry."""
        return ProviderHealth(
            name=self.name,
            enabled=self._settings.google_scraper_enabled,
            status=self._status,
            last_success=self._last_success,
            last_error=self._last_error,
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic telemetry for health / admin endpoints."""
        return {
            "name": self.name,
            "status": self._status,
            "enabled": self.is_configured(),
            "last_success": self._last_success,
            "last_error": self._last_error,
            **self._scraper.get_health_telemetry(),
        }
