"""ProductProvider interface.

Every external data source (official API, affiliate API, merchant feed,
licensed data provider) implements this same normalized contract. The rest
of the system never knows which provider a fact came from except via the
`provider` field that is preserved for attribution and freshness.
"""
from __future__ import annotations

import abc
from typing import ClassVar, List, Optional, Set

import httpx

from app.core.resilience import RetryableError
from app.schemas.domain import (
    ProviderAvailability,
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    RawReview,
)


class ProviderError(Exception):
    pass


class ProviderNotConfigured(ProviderError):
    pass


class ProductProvider(abc.ABC):
    #: Stable identifier stored alongside every record this provider produces.
    name: ClassVar[str]
    #: Human-readable label (shown as "Source").
    label: ClassVar[str]
    #: ISO-3166 alpha-2 countries this provider can serve. Empty = all.
    countries: ClassVar[Set[str]] = set()
    #: Category ids this provider is good at. Empty = all categories.
    categories: ClassVar[Set[str]] = set()
    #: Outbound requests per second allowed by the provider's terms.
    rate_limit_per_second: ClassVar[float] = 2.0
    #: Environment variables required to enable this provider (for diagnostics).
    required_env: ClassVar[List[str]] = []
    supports_image_search: ClassVar[bool] = False
    is_demo: ClassVar[bool] = False

    @abc.abstractmethod
    def is_configured(self) -> bool:
        ...

    def supports(self, country: str, category: Optional[str]) -> bool:
        if self.countries and country.upper() not in self.countries:
            return False
        if self.categories and category and category not in self.categories:
            return False
        return True

    @abc.abstractmethod
    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        ...

    async def get_product(self, external_id: str, country: str) -> Optional[RawProduct]:
        return None

    async def get_offers(self, external_id: str, country: str) -> List[RawOffer]:
        product = await self.get_product(external_id, country)
        return product.offers if product else []

    async def get_reviews(self, external_id: str, country: str) -> List[RawReview]:
        return []

    async def check_availability(self, external_id: str, country: str) -> Optional[ProviderAvailability]:
        offers = await self.get_offers(external_id, country)
        if not offers:
            return None
        best = "in_stock" if any(o.availability == "in_stock" for o in offers) else offers[0].availability
        return ProviderAvailability(provider=self.name, status=best)

    async def search_similar(self, external_id: str, country: str) -> List[RawProduct]:
        return []

    async def search_by_image(self, image_bytes: bytes, country: str) -> List[RawProduct]:
        return []

    async def get_delivery(self, external_id: str, country: str) -> Optional[dict]:
        return None

    async def get_images(self, external_id: str, country: str) -> List[str]:
        product = await self.get_product(external_id, country)
        return product.image_urls if product else []

    def get_capabilities(self) -> Any:
        from app.providers.capabilities import ProviderCapabilities, MarketplaceType
        is_qc = getattr(self, "is_quick_commerce", False)
        return ProviderCapabilities(
            product_search=True,
            offers=True,
            availability=True,
            delivery=is_qc,
            images=True,
            quick_commerce=is_qc,
            marketplace_type=MarketplaceType.QUICK_COMMERCE if is_qc else MarketplaceType.GENERAL_MARKETPLACE,
        )


def raise_for_status(response: httpx.Response, provider: str) -> None:
    """Map HTTP errors to retryable vs. permanent provider errors."""
    if response.status_code == 429 or response.status_code >= 500:
        raise RetryableError(f"{provider}: HTTP {response.status_code}")
    if response.status_code >= 400:
        raise ProviderError(f"{provider}: HTTP {response.status_code} – {response.text[:200]}")
