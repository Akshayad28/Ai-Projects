"""SerpApi / Google Shopping provider adapter.

Fetches live search results from Google Shopping across countries/currencies
using official SerpApi API keys if configured.
"""
from __future__ import annotations

import time
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


class SerpShoppingProvider(ProductProvider):
    name: ClassVar[str] = "serp_google_shopping"
    label: ClassVar[str] = "Google Shopping (SerpApi)"
    countries: ClassVar[Set[str]] = {"IN", "US", "GB", "DE", "CA", "AU", "AE", "SG"}
    rate_limit_per_second: ClassVar[float] = 3.0
    required_env: ClassVar[List[str]] = ["SEARCH_PROVIDER_API_KEY"]

    def is_configured(self) -> bool:
        settings = get_settings()
        if not getattr(settings, "serpapi_enabled", True):
            return False
        return bool(settings.search_provider_api_key or settings.provider_api_key)

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        settings = get_settings()
        api_key = settings.search_provider_api_key or settings.provider_api_key
        if not api_key:
            return []

        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        gl = params.country.lower()
        hl = "en"
        query = params.intent.provider_query or params.query

        url = "https://serpapi.com/search.json"
        req_params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": api_key,
            "gl": gl,
            "hl": hl,
            "num": params.limit,
        }

        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                res = await client.get(url, params=req_params)
                raise_for_status(res, self.name)
                return res.json()

        try:
            data = await with_retries(_call, attempts=2)
        except Exception as exc:
            log.warning("SerpApi search failed", extra={"query": query, "error": str(exc)})
            return []

        shopping_results = data.get("shopping_results", [])
        products: List[RawProduct] = []

        for item in shopping_results:
            title = item.get("title") or ""
            if not title:
                continue

            product_id = str(item.get("product_id") or item.get("docid") or item.get("position") or title)
            extracted_price = item.get("extracted_price")
            price_val = float(extracted_price) if extracted_price is not None else None
            
            source_retailer = item.get("source") or "Google Shopping Merchant"
            rating = item.get("rating")
            reviews = item.get("reviews")
            thumbnail = item.get("thumbnail")
            link = item.get("link")

            offer = RawOffer(
                provider=self.name,
                retailer_name=source_retailer,
                country=params.country,
                price_amount=price_val,
                currency=params.currency,
                original_price=None,
                availability="in_stock" if price_val is not None else "unknown",
                url=link,
                checked_at=now_utc(),
            )

            raw = RawProduct(
                provider=self.name,
                external_id=product_id,
                title=title,
                description=item.get("snippet"),
                url=link,
                image_urls=[thumbnail] if thumbnail else [],
                rating=float(rating) if rating is not None else None,
                review_count=int(reviews) if reviews is not None else None,
                country=params.country,
                offers=[offer],
            )
            products.append(raw)

        return products
