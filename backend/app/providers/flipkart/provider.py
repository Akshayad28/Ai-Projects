"""Flipkart Shopping Provider Implementation."""
from __future__ import annotations

from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base.exceptions import (
    ProviderBlocked,
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
from app.providers.flipkart.normalizer import normalize_flipkart_product
from app.providers.flipkart.scraper import FlipkartScraper

log = get_logger(__name__)


class FlipkartProvider(ShoppingProvider):
    """ShoppingProvider implementation for Flipkart India."""

    def __init__(self) -> None:
        self._scraper = FlipkartScraper()
        self._settings = get_settings()
        self._last_success: Optional[str] = None
        self._last_error: Optional[str] = None
        self._status = "healthy"

    name: str = "flipkart"
    label: str = "Flipkart India"
    required_env: List[str] = ["FLIPKART_AFFILIATE_ID", "FLIPKART_AFFILIATE_TOKEN"]
    countries: set = {"IN"}
    rate_limit_per_second: float = 2.0
    is_demo: bool = False

    def is_configured(self) -> bool:
        return bool(self._settings.flipkart_affiliate_id) or bool(self._settings.scraper_flipkart_enabled)

    def supports(self, country: str, category: Optional[str] = None) -> bool:
        return country.upper() == "IN" or not country

    async def search_products(self, query: SearchQuery) -> List[ProviderProduct]:
        """Searches live Flipkart India for products."""
        if not self._settings.scraper_flipkart_enabled:
            return []

        try:
            raw_items = await self._scraper.scrape_search(
                query.query,
                max_items=min(query.limit, self._settings.scraper_flipkart_max_results),
            )
            products: List[ProviderProduct] = []
            for item in raw_items:
                prod = normalize_flipkart_product(item)
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
            log.warning(f"FlipkartProvider is marked BLOCKED: {exc}")
            raise
        except ProviderTimeout as exc:
            self._last_error = str(exc)
            self._status = "degraded"
            log.warning(f"FlipkartProvider timed out: {exc}")
            raise
        except Exception as exc:
            self._last_error = str(exc)
            self._status = "degraded"
            log.warning(f"FlipkartProvider search failed: {exc}")
            raise ProviderUnavailable(f"Flipkart error: {exc}") from exc

    async def get_product(self, product_url: str) -> Optional[ProviderProduct]:
        return None

    async def get_offers(self, product_url: str) -> List[ProviderOffer]:
        return []

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name,
            enabled=self._settings.scraper_flipkart_enabled,
            status=self._status,
            last_success=self._last_success,
            last_error=self._last_error,
        )
