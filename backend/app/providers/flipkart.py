"""Flipkart Affiliate API adapter.

Integrates with the official Flipkart Affiliate platform for product search,
lookup, delta ingestion, and offer aggregation using Fk-Affiliate-Id and
Fk-Affiliate-Token authentication.
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Set

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resilience import provider_bucket, with_retries
from app.providers.base import ProductProvider, raise_for_status
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    now_utc,
)

log = get_logger(__name__)


class FlipkartProvider(ProductProvider):
    name: ClassVar[str] = "flipkart"
    label: ClassVar[str] = "Flipkart"
    countries: ClassVar[Set[str]] = {"IN"}
    rate_limit_per_second: ClassVar[float] = 2.0
    required_env: ClassVar[List[str]] = [
        "FLIPKART_AFFILIATE_ID",
        "FLIPKART_AFFILIATE_TOKEN",
    ]

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.flipkart_affiliate_id and settings.flipkart_affiliate_token)

    def _get_headers(self) -> Dict[str, str]:
        settings = get_settings()
        return {
            "Fk-Affiliate-Id": settings.flipkart_affiliate_id or "",
            "Fk-Affiliate-Token": settings.flipkart_affiliate_token or "",
            "Accept": "application/json",
        }

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        if not self.is_configured():
            return []

        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        query = params.intent.provider_query or params.query
        url = "https://affiliate-api.flipkart.net/affiliate/1.0/search.json"
        req_params = {
            "query": query,
            "resultCount": str(min(params.limit, 20)),
        }
        headers = self._get_headers()

        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.get(url, headers=headers, params=req_params)
                raise_for_status(res, self.name)
                return res.json()

        try:
            data = await with_retries(_call, attempts=2)
        except Exception as exc:
            log.warning("Flipkart affiliate search failed", extra={"query": query, "error": str(exc)})
            return []

        product_list = data.get("products", [])
        products: List[RawProduct] = []

        for item in product_list:
            base_info = item.get("productBaseInfoV1", {})
            fsn = base_info.get("productId")
            title = base_info.get("title")
            if not fsn or not title:
                continue

            brand = base_info.get("productBrand")
            url = base_info.get("productUrl")
            desc = base_info.get("productDescription")

            # Extract image
            image_urls_dict = base_info.get("imageUrls", {})
            image_url = (
                image_urls_dict.get("800x800")
                or image_urls_dict.get("400x400")
                or image_urls_dict.get("200x200")
            )

            # Price calculations
            selling_price_obj = base_info.get("flipkartSellingPrice", {})
            selling_price = selling_price_obj.get("amount")
            currency = selling_price_obj.get("currency") or "INR"

            mrp_obj = base_info.get("maximumRetailPrice", {})
            mrp = mrp_obj.get("amount")

            in_stock = base_info.get("inStock", True)
            availability = "in_stock" if in_stock else "out_of_stock"

            # Specs
            specs_dict = base_info.get("attributes", {})

            offer = RawOffer(
                provider=self.name,
                retailer_name="Flipkart",
                retailer_domain="www.flipkart.com",
                seller_name="Flipkart Assured Seller",
                country="IN",
                price_amount=float(selling_price) if selling_price else None,
                currency=currency,
                original_price=float(mrp) if mrp else None,
                availability=availability,
                url=url,
                affiliate_url=url,
                checked_at=now_utc(),
            )

            raw = RawProduct(
                provider=self.name,
                external_id=fsn,
                sku=fsn,
                title=title,
                brand=brand,
                description=desc,
                url=url,
                image_urls=[image_url] if image_url else [],
                specs=specs_dict if isinstance(specs_dict, dict) else {},
                country="IN",
                offers=[offer],
                is_demo=False,
            )
            products.append(raw)

        return products

    async def get_product(self, external_id: str, country: str) -> Optional[RawProduct]:
        if not self.is_configured():
            return None

        url = "https://affiliate-api.flipkart.net/affiliate/1.0/product.json"
        req_params = {"id": external_id}
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.get(url, headers=headers, params=req_params)
                raise_for_status(res, self.name)
                data = res.json()
        except Exception as exc:
            log.warning("Flipkart get_product failed", extra={"id": external_id, "error": str(exc)})
            return None

        base_info = data.get("productBaseInfoV1", {})
        fsn = base_info.get("productId")
        title = base_info.get("title")
        if not fsn or not title:
            return None

        brand = base_info.get("productBrand")
        url = base_info.get("productUrl")
        desc = base_info.get("productDescription")

        image_urls_dict = base_info.get("imageUrls", {})
        image_url = (
            image_urls_dict.get("800x800")
            or image_urls_dict.get("400x400")
            or image_urls_dict.get("200x200")
        )

        selling_price_obj = base_info.get("flipkartSellingPrice", {})
        selling_price = selling_price_obj.get("amount")
        currency = selling_price_obj.get("currency") or "INR"

        mrp_obj = base_info.get("maximumRetailPrice", {})
        mrp = mrp_obj.get("amount")

        in_stock = base_info.get("inStock", True)
        availability = "in_stock" if in_stock else "out_of_stock"

        offer = RawOffer(
            provider=self.name,
            retailer_name="Flipkart",
            retailer_domain="www.flipkart.com",
            seller_name="Flipkart Assured Seller",
            country="IN",
            price_amount=float(selling_price) if selling_price else None,
            currency=currency,
            original_price=float(mrp) if mrp else None,
            availability=availability,
            url=url,
            affiliate_url=url,
            checked_at=now_utc(),
        )

        return RawProduct(
            provider=self.name,
            external_id=fsn,
            sku=fsn,
            title=title,
            brand=brand,
            description=desc,
            url=url,
            image_urls=[image_url] if image_url else [],
            country="IN",
            offers=[offer],
            is_demo=False,
        )
