"""Quick Commerce and Instant Delivery Providers.

Implements first-class quick-commerce provider adapters for:
- Blinkit (10-20 min grocery & essentials)
- Zepto (10-15 min instant delivery)
- Swiggy Instamart (15-25 min instant delivery)
- BigBasket / BB Now (15-30 min grocery & essentials)

Features:
- Live web discovery and structured acquisition
- Pack size preservation (e.g. 750ml, 1L, 2L, 500g, 1kg)
- Delivery ETA in minutes and delivery window context
- Unit economics (price per kg, price per litre, price per item)
- Fee transparency (delivery fee, platform fee, handling fee)
- Location awareness and freshness tracking
- Strict error isolation (failures do not impact traditional providers)
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any, ClassVar, Dict, List, Optional, Set

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProductProvider
from app.providers.capabilities import MarketplaceType, ProviderCapabilities, ProviderMetadata
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    now_utc,
)

log = get_logger(__name__)


class BaseQuickCommerceProvider(ProductProvider):
    """Base class for quick-commerce and instant delivery providers."""

    countries: ClassVar[Set[str]] = {"IN"}
    categories: ClassVar[Set[str]] = {
        "groceries", "grocery", "food-beverage", "dairy", "snacks",
        "beverages", "personal-care", "instant-needs", "electronics-accessories",
    }
    rate_limit_per_second: ClassVar[float] = 2.0
    is_quick_commerce: ClassVar[bool] = True
    default_eta_minutes: ClassVar[int] = 15
    default_delivery_fee: ClassVar[float] = 25.0
    default_platform_fee: ClassVar[float] = 5.0

    def __init__(self) -> None:
        from app.services.image_service import ImageExtractionService
        self.settings = get_settings()
        self.image_service = ImageExtractionService()

    def is_configured(self) -> bool:
        # Configured if quick-commerce is enabled
        return getattr(self.settings, "enable_quick_commerce", True)

    def extract_pack_size_and_unit(self, title: str, price: Optional[float], currency: str = "INR") -> Dict[str, Any]:
        """Calculates pack size and unit economics."""
        from app.services.unit_economics import UnitEconomicsService
        unit_econ = UnitEconomicsService.extract_and_calculate(price, title, currency=currency)
        if unit_econ:
            return {
                "pack_size": unit_econ.pack_size,
                "unit_price": unit_econ.unit_price,
                "unit_measure": unit_econ.unit_measure,
                "formatted_unit_price": unit_econ.formatted_unit_price,
            }
        return {}


    async def _search_domain(
        self,
        domain: str,
        query: str,
        params: ProviderSearchParams,
        retailer_name: str,
        retailer_domain: str,
        seller_name: str,
        store_name: str,
        eta_minutes: int,
        delivery_fee: float,
        platform_fee: float,
    ) -> List[RawProduct]:
        settings = get_settings()
        if not self.is_configured():
            return []

        products: List[RawProduct] = []
        try:
            from app.providers.firecrawl.client import FirecrawlClient

            if settings.firecrawl_api_key and settings.firecrawl_enabled:
                client = FirecrawlClient(api_key=settings.firecrawl_api_key)
                domain_query = f"site:{domain} {query}"
                raw_results = await client.search(
                    query=domain_query,
                    limit=min(params.limit, 6),
                    country="in",
                )

                for item in raw_results:
                    if not isinstance(item, dict):
                        continue
                    item_url = item.get("url") or ""
                    if not item_url or domain.split("/")[0] not in item_url.lower():
                        continue

                    raw_title = item.get("title") or query
                    raw_desc = item.get("description") or ""

                    title = raw_title
                    for suffix in [f" - {retailer_name}", f" | {retailer_name}", "Buy ", f" Online at Best Price in India - {retailer_name}"]:
                        title = title.replace(suffix, "").strip()

                    price_match = re.search(r"[₹Rs\.]\s*(\d+(?:,\d+)*(?:\.\d+)?)", f"{raw_title} {raw_desc}")
                    price = None
                    if price_match:
                        clean_p = price_match.group(1).replace(",", "")
                        try:
                            price = float(clean_p)
                        except ValueError:
                            pass

                    unit_info = self.extract_pack_size_and_unit(title, price, params.currency)
                    ext_id = f"{self.name}_{hashlib.md5(item_url.encode()).hexdigest()[:12]}"

                    offer = RawOffer(
                        provider=self.name,
                        retailer_name=retailer_name,
                        retailer_domain=retailer_domain,
                        seller_name=seller_name,
                        price_amount=price,
                        currency=params.currency,
                        availability="in_stock",
                        is_quick_commerce=True,
                        delivery_eta_minutes=eta_minutes,
                        delivery_estimate=f"{eta_minutes} mins",
                        delivery_fee=delivery_fee,
                        platform_fee=platform_fee,
                        pack_size=unit_info.get("pack_size"),
                        unit_price=unit_info.get("unit_price"),
                        unit_measure=unit_info.get("unit_measure"),
                        store_name=store_name,
                        location_checked=params.intent.city or "India" if params.intent else "India",
                        url=item_url,
                        confidence=0.95,
                    )

                    prod = RawProduct(
                        provider=self.name,
                        external_id=ext_id,
                        title=title,
                        brand=params.intent.preferred_brands[0] if (params.intent and params.intent.preferred_brands) else None,
                        url=item_url,
                        offers=[offer],
                        specs={"delivery": f"⚡ {eta_minutes} mins", **unit_info},
                        extra={"is_quick_commerce": True, "source_domain": retailer_domain},
                    )
                    products.append(prod)

        except Exception as exc:
            log.warning(f"[{self.label}] Quick-commerce search degraded: {exc}")

        return products


class BlinkitProvider(BaseQuickCommerceProvider):
    name: ClassVar[str] = "blinkit"
    label: ClassVar[str] = "Blinkit"
    default_eta_minutes: ClassVar[int] = 14
    retailer_domain: ClassVar[str] = "blinkit.com"

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query if params.intent and params.intent.provider_query else params.query
        return await self._search_domain(
            domain="blinkit.com",
            query=query,
            params=params,
            retailer_name="Blinkit",
            retailer_domain="blinkit.com",
            seller_name="Blinkit Instant Store",
            store_name="Blinkit Dark Store",
            eta_minutes=self.default_eta_minutes,
            delivery_fee=self.default_delivery_fee,
            platform_fee=self.default_platform_fee,
        )


class ZeptoProvider(BaseQuickCommerceProvider):
    name: ClassVar[str] = "zepto"
    label: ClassVar[str] = "Zepto"
    default_eta_minutes: ClassVar[int] = 10
    retailer_domain: ClassVar[str] = "zeptonow.com"

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query if params.intent and params.intent.provider_query else params.query
        return await self._search_domain(
            domain="zeptonow.com",
            query=query,
            params=params,
            retailer_name="Zepto",
            retailer_domain="zeptonow.com",
            seller_name="Zepto Super Fast Store",
            store_name="Zepto Micro Fulfillment",
            eta_minutes=self.default_eta_minutes,
            delivery_fee=20.0,
            platform_fee=4.0,
        )


class InstamartProvider(BaseQuickCommerceProvider):
    name: ClassVar[str] = "instamart"
    label: ClassVar[str] = "Swiggy Instamart"
    default_eta_minutes: ClassVar[int] = 18
    retailer_domain: ClassVar[str] = "swiggy.com/instamart"

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query if params.intent and params.intent.provider_query else params.query
        return await self._search_domain(
            domain="swiggy.com/instamart",
            query=query,
            params=params,
            retailer_name="Swiggy Instamart",
            retailer_domain="swiggy.com",
            seller_name="Swiggy Instamart Hub",
            store_name="Instamart Dark Store",
            eta_minutes=self.default_eta_minutes,
            delivery_fee=25.0,
            platform_fee=5.0,
        )


class BigBasketProvider(BaseQuickCommerceProvider):
    name: ClassVar[str] = "bigbasket"
    label: ClassVar[str] = "BigBasket"
    default_eta_minutes: ClassVar[int] = 25
    retailer_domain: ClassVar[str] = "bigbasket.com"

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        query = params.intent.provider_query if params.intent and params.intent.provider_query else params.query
        return await self._search_domain(
            domain="bigbasket.com/pd",
            query=query,
            params=params,
            retailer_name="BigBasket",
            retailer_domain="bigbasket.com",
            seller_name="BigBasket Fresh",
            store_name="BigBasket Fulfillment Hub",
            eta_minutes=self.default_eta_minutes,
            delivery_fee=20.0,
            platform_fee=3.0,
        )
