"""Best Buy Products API adapter.

Fetches product data, prices, offers, and specifications from the official
developer.bestbuy.com API when BESTBUY_API_KEY is configured.
"""
from __future__ import annotations

from typing import ClassVar, List, Optional, Set
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


class BestBuyProvider(ProductProvider):
    name: ClassVar[str] = "bestbuy"
    label: ClassVar[str] = "Best Buy"
    countries: ClassVar[Set[str]] = {"US", "CA"}
    rate_limit_per_second: ClassVar[float] = 5.0
    required_env: ClassVar[List[str]] = ["BESTBUY_API_KEY"]

    def is_configured(self) -> bool:
        return bool(get_settings().bestbuy_api_key)

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        api_key = get_settings().bestbuy_api_key
        if not api_key:
            return []

        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        # Best Buy search query syntax: search=term1&search=term2
        query_words = (params.intent.provider_query or params.query).split()
        search_filter = "&".join(f"search={w}" for w in query_words[:4] if w)

        url = f"https://api.bestbuy.com/v1/products({search_filter})?apiKey={api_key}&format=json&show=sku,name,salePrice,regularPrice,upc,manufacturer,modelNumber,shortDescription,image,customerReviewAverage,customerReviewCount,url,inStoreAvailability,onlineAvailability"

        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.get(url)
                raise_for_status(res, self.name)
                return res.json()

        try:
            data = await with_retries(_call, attempts=2)
        except Exception as exc:
            log.warning("BestBuy search failed", extra={"query": params.query, "error": str(exc)})
            return []

        items = data.get("products", [])
        products: List[RawProduct] = []

        for item in items:
            sku = str(item.get("sku") or "")
            title = item.get("name") or ""
            if not sku or not title:
                continue

            sale_price = item.get("salePrice")
            regular_price = item.get("regularPrice")
            in_stock = bool(item.get("onlineAvailability") or item.get("inStoreAvailability"))

            offer = RawOffer(
                provider=self.name,
                retailer_name="Best Buy",
                country="US",
                price_amount=float(sale_price) if sale_price is not None else None,
                currency="USD",
                original_price=float(regular_price) if regular_price is not None else None,
                availability="in_stock" if in_stock else "out_of_stock",
                url=item.get("url"),
                checked_at=now_utc(),
            )

            raw = RawProduct(
                provider=self.name,
                external_id=sku,
                title=title,
                brand=item.get("manufacturer"),
                model=item.get("modelNumber"),
                upc=str(item.get("upc")) if item.get("upc") else None,
                sku=sku,
                description=item.get("shortDescription"),
                url=item.get("url"),
                image_urls=[item.get("image")] if item.get("image") else [],
                rating=float(item.get("customerReviewAverage")) if item.get("customerReviewAverage") is not None else None,
                review_count=int(item.get("customerReviewCount")) if item.get("customerReviewCount") is not None else None,
                country="US",
                offers=[offer],
            )
            products.append(raw)

        return products
