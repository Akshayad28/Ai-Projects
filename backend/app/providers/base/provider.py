"""Shopping Provider Interface.

All current (Amazon, Flipkart) and future (Myntra, Croma, eBay, etc.)
providers must implement this exact interface. Business logic never
depends directly on any single retailer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.providers.base.models import (
    ProviderHealth,
    ProviderOffer,
    ProviderProduct,
    SearchQuery,
)


class ShoppingProvider(ABC):
    """Abstract base class for all shopping data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'amazon', 'flipkart', 'ebay')."""
        pass

    @property
    def label(self) -> str:
        """Human-readable display name."""
        return self.name.capitalize()

    @abstractmethod
    async def search_products(
        self,
        query: SearchQuery,
    ) -> List[ProviderProduct]:
        """Search products using permitted access method.

        Never invents missing fields. Isolates errors and respects retailer constraints.
        """
        pass

    @abstractmethod
    async def get_product(
        self,
        product_url: str,
    ) -> Optional[ProviderProduct]:
        """Fetch full product details from retailer URL."""
        pass

    @abstractmethod
    async def get_offers(
        self,
        product_url: str,
    ) -> List[ProviderOffer]:
        """Fetch current active offers for product."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Return connectivity and operational status."""
        pass
