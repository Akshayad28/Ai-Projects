"""eBay Browse API adapter.

Uses eBay OAuth Client Credentials flow to query the official eBay Browse API
when EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are configured.
"""
from __future__ import annotations

import base64
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


class EbayProvider(ProductProvider):
    name: ClassVar[str] = "ebay"
    label: ClassVar[str] = "eBay"
    countries: ClassVar[Set[str]] = {"US", "GB", "DE", "AU", "CA"}
    rate_limit_per_second: ClassVar[float] = 5.0
    required_env: ClassVar[List[str]] = ["EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET"]

    _cached_token: Optional[str] = None
    _token_expiry: float = 0.0

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.ebay_client_id and settings.ebay_client_secret)

    async def _get_access_token(self) -> Optional[str]:
        settings = get_settings()
        if not settings.ebay_client_id or not settings.ebay_client_secret:
            return None

        if self._cached_token and time.time() < self._token_expiry - 60:
            return self._cached_token

        auth_header = base64.b64encode(
            f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()
        ).decode()

        url = "https://api.ebay.com/identity/v1/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, data=data)
                res.raise_for_status()
                token_data = res.json()
                self._cached_token = token_data.get("access_token")
                self._token_expiry = time.time() + token_data.get("expires_in", 7200)
                return self._cached_token
        except Exception as exc:
            log.warning("eBay token acquisition failed", extra={"error": str(exc)})
            return None

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        token = await self._get_access_token()
        if not token:
            return []

        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        query = params.intent.provider_query or params.query
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": f"EBAY_{params.country}" if params.country in {"US", "GB", "DE", "AU"} else "EBAY_US",
        }
        req_params = {
            "q": query,
            "limit": str(min(params.limit, 20)),
        }

        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.get(url, headers=headers, params=req_params)
                raise_for_status(res, self.name)
                return res.json()

        try:
            data = await with_retries(_call, attempts=2)
        except Exception as exc:
            log.warning("eBay search failed", extra={"query": query, "error": str(exc)})
            return []

        items = data.get("itemSummaries", [])
        products: List[RawProduct] = []

        for item in items:
            item_id = item.get("itemId")
            title = item.get("title")
            if not item_id or not title:
                continue

            price_info = item.get("price", {})
            amount = float(price_info.get("value")) if price_info.get("value") else None
            currency = price_info.get("currency") or "USD"

            image = item.get("image", {}).get("imageUrl")
            item_url = item.get("itemWebUrl")
            seller = item.get("seller", {})

            offer = RawOffer(
                provider=self.name,
                retailer_name="eBay",
                seller_name=seller.get("username") or "eBay Seller",
                seller_rating=float(seller.get("feedbackPercentage")) if seller.get("feedbackPercentage") else None,
                seller_rating_count=int(seller.get("feedbackScore")) if seller.get("feedbackScore") else None,
                country=params.country,
                price_amount=amount,
                currency=currency,
                availability="in_stock" if amount is not None else "unknown",
                url=item_url,
                checked_at=now_utc(),
            )

            raw = RawProduct(
                provider=self.name,
                external_id=str(item_id),
                title=title,
                url=item_url,
                image_urls=[image] if image else [],
                country=params.country,
                offers=[offer],
            )
            products.append(raw)

        return products
