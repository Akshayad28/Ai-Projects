"""Specialized Retailer and Brand Marketplace Providers.

Implements dedicated retail provider adapters for:
- Croma (Electronics, Laptops, Phones, Appliances)
- Reliance Digital (Electronics & Tech)
- Myntra (Fashion, Footwear, Apparel, Accessories)
- IKEA India (Furniture, Study Tables, Office Chairs, Home Decor)

Enables deep specialist discovery beyond general marketplaces.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any, ClassVar, Dict, List, Optional, Set

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProductProvider
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
)

log = get_logger(__name__)


class BaseSpecialistProvider(ProductProvider):
    """Base class for specialist category retailer adapters."""
    countries: ClassVar[Set[str]] = {"IN"}
    rate_limit_per_second: ClassVar[float] = 2.0
    retailer_name: ClassVar[str] = "Specialist"
    retailer_domain: ClassVar[str] = ""

    def is_configured(self) -> bool:
        settings = get_settings()
        # Active when Firecrawl is available or when domain scraping is enabled
        return bool(settings.firecrawl_api_key and settings.firecrawl_enabled)

    async def _search_retailer_domain(self, domain: str, query: str, limit: int, currency: str) -> List[RawProduct]:
        settings = get_settings()
        if not self.is_configured():
            return []

        products: List[RawProduct] = []
        try:
            from app.providers.firecrawl.client import FirecrawlClient

            client = FirecrawlClient(api_key=settings.firecrawl_api_key)
            domain_query = f"site:{domain} {query}"
            raw_results = await client.search(
                query=domain_query,
                limit=min(limit, 8),
                country="in",
            )

            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                item_url = item.get("url") or ""
                if not item_url or domain not in item_url.lower():
                    continue

                item_title = item.get("title") or query
                item_desc = item.get("description") or ""
                clean_title = item_title
                for suffix in [f" - {self.label}", f" | {self.label}", f": Buy Online at {self.label}"]:
                    clean_title = clean_title.replace(suffix, "").strip()

                price_match = re.search(r"[₹Rs\.]\s*(\d+(?:,\d+)*(?:\.\d+)?)", f"{item_title} {item_desc}")
                price = None
                if price_match:
                    clean_p = price_match.group(1).replace(",", "")
                    try:
                        price = float(clean_p)
                    except ValueError:
                        pass

                ext_id = f"{self.name}_{hashlib.md5(item_url.encode()).hexdigest()[:12]}"

                offer = RawOffer(
                    provider=self.name,
                    retailer_name=self.retailer_name,
                    retailer_domain=self.retailer_domain,
                    seller_name=f"{self.retailer_name} Official",
                    price_amount=price,
                    currency=currency,
                    availability="in_stock",
                    delivery_estimate="2-4 business days",
                    url=item_url,
                    confidence=0.95,
                )

                prod = RawProduct(
                    provider=self.name,
                    external_id=ext_id,
                    title=clean_title,
                    url=item_url,
                    offers=[offer],
                    specs={"merchant": self.retailer_name},
                    extra={"specialist_category": self.retailer_name, "source_domain": self.retailer_domain},
                )
                products.append(prod)

        except Exception as exc:
            log.warning(f"[{self.label}] Domain search degraded: {exc}")

        return products


class CromaProvider(BaseSpecialistProvider):
    name: ClassVar[str] = "croma"
    label: ClassVar[str] = "Croma"
    retailer_name: ClassVar[str] = "Croma"
    retailer_domain: ClassVar[str] = "croma.com"
    categories: ClassVar[Set[str]] = {"electronics", "laptops", "phones", "monitors", "appliances", "audio"}

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query or params.query
        return await self._search_retailer_domain(self.retailer_domain, query, params.limit, params.currency)


class RelianceDigitalProvider(BaseSpecialistProvider):
    name: ClassVar[str] = "reliance_digital"
    label: ClassVar[str] = "Reliance Digital"
    retailer_name: ClassVar[str] = "Reliance Digital"
    retailer_domain: ClassVar[str] = "reliancedigital.in"
    categories: ClassVar[Set[str]] = {"electronics", "laptops", "phones", "monitors", "appliances"}

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query or params.query
        return await self._search_retailer_domain(self.retailer_domain, query, params.limit, params.currency)


class MyntraProvider(BaseSpecialistProvider):
    name: ClassVar[str] = "myntra"
    label: ClassVar[str] = "Myntra"
    retailer_name: ClassVar[str] = "Myntra"
    retailer_domain: ClassVar[str] = "myntra.com"
    categories: ClassVar[Set[str]] = {"fashion", "shoes", "apparel", "clothing", "accessories"}

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query or params.query
        return await self._search_retailer_domain(self.retailer_domain, query, params.limit, params.currency)


class IkeaProvider(BaseSpecialistProvider):
    name: ClassVar[str] = "ikea"
    label: ClassVar[str] = "IKEA"
    retailer_name: ClassVar[str] = "IKEA"
    retailer_domain: ClassVar[str] = "ikea.com"
    categories: ClassVar[Set[str]] = {"furniture", "home", "study-tables", "office-chairs"}

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query or params.query
        return await self._search_retailer_domain("ikea.com/in", query, params.limit, params.currency)
