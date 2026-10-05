"""Amazon Shopping Provider Implementation."""
from __future__ import annotations

from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.amazon.normalizer import normalize_amazon_product
from app.providers.amazon.scraper import AmazonScraper
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
from app.providers.base.provider import ShoppingProvider

log = get_logger(__name__)


class AmazonProvider(ShoppingProvider):
    """ShoppingProvider implementation for Amazon India."""

    def __init__(self) -> None:
        self._scraper = AmazonScraper()
        self._settings = get_settings()
        self._last_success: Optional[str] = None
        self._last_error: Optional[str] = None
        self._status = "healthy"

    name: str = "amazon"
    label: str = "Amazon India"
    required_env: List[str] = ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "AMAZON_PARTNER_TAG"]
    countries: set = {"IN", "US", "GB", "DE", "JP"}
    rate_limit_per_second: float = 1.0
    is_demo: bool = False

    def is_configured(self) -> bool:
        return bool(self._settings.amazon_paapi_access_key) or bool(self._settings.scraper_amazon_enabled)

    def supports(self, country: str, category: Optional[str] = None) -> bool:
        return True

    async def search_products(self, query: SearchQuery) -> List[ProviderProduct]:
        """Searches live Amazon India for products."""
        if not self._settings.scraper_amazon_enabled:
            return []

        try:
            raw_items = await self._scraper.scrape_search(
                query.query,
                max_items=min(query.limit, self._settings.scraper_amazon_max_results),
            )
            products: List[ProviderProduct] = []
            for item in raw_items:
                prod = normalize_amazon_product(item)
                # Respect price filter if provided
                if query.max_price and prod.price.amount and prod.price.amount > query.max_price:
                    continue
                if query.min_price and prod.price.amount and prod.price.amount < query.min_price:
                    continue
                products.append(prod)

            self._last_success = utcnow_str()
            self._status = "healthy"
            return products

        except ProviderBlocked as exc:
            self._last_error = str(exc)
            self._status = "blocked"
            log.warning(f"AmazonProvider is marked BLOCKED: {exc}")
            raise
        except ProviderTimeout as exc:
            self._last_error = str(exc)
            self._status = "degraded"
            log.warning(f"AmazonProvider timed out: {exc}")
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self._status = "degraded"
            log.warning(f"AmazonProvider search failed: {exc}")
            raise ProviderUnavailable(f"Amazon error: {exc}") from exc

    async def get_product(self, product_url: str) -> Optional[ProviderProduct]:
        """Fetches product details from Amazon URL."""
        # Query product by ASIN or URL
        return None

    async def get_offers(self, product_url: str) -> List[ProviderOffer]:
        """Fetches real-time offer pricing for an Amazon product."""
        return []

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name,
            enabled=self._settings.scraper_amazon_enabled,
            status=self._status,
            last_success=self._last_success,
            last_error=self._last_error,
        )
