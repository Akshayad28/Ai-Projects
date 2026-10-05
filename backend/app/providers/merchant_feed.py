"""Merchant feed provider.

Parses standard Google Merchant Center formatted product feeds (CSV / TSV / XML)
configured via MERCHANT_FEED_URLS.
"""
from __future__ import annotations

import csv
import io
from typing import ClassVar, List, Optional, Set
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProductProvider
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    now_utc,
)

log = get_logger(__name__)


class MerchantFeedProvider(ProductProvider):
    name: ClassVar[str] = "merchant_feed"
    label: ClassVar[str] = "Merchant Product Feed"
    rate_limit_per_second: ClassVar[float] = 1.0

    def is_configured(self) -> bool:
        return bool(get_settings().merchant_feed_urls)

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        urls = get_settings().merchant_feed_urls
        if not urls:
            return []

        products: List[RawProduct] = []
        q_terms = [t.lower() for t in (params.intent.provider_query or params.query).split() if t]

        for feed_url in urls:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.get(feed_url)
                    if res.status_code != 200:
                        continue
                    content = res.text

                # Parse CSV/TSV
                delimiter = "\t" if "\t" in content[:1000] else ","
                reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
                for row in reader:
                    title = row.get("title") or row.get("name") or ""
                    if not title:
                        continue

                    # Keyword match filter
                    title_lower = title.lower()
                    if not all(term in title_lower for term in q_terms[:2]):
                        continue

                    item_id = row.get("id") or row.get("sku") or row.get("mpn") or title
                    price_str = row.get("price") or ""
                    price_num = None
                    try:
                        clean_price = "".join(c for c in price_str if c.isdigit() or c == ".")
                        if clean_price:
                            price_num = float(clean_price)
                    except ValueError:
                        pass

                    offer = RawOffer(
                        provider=self.name,
                        retailer_name=row.get("brand") or "Merchant Feed",
                        price_amount=price_num,
                        currency=params.currency,
                        availability="in_stock" if (row.get("availability") or "").lower() in {"in stock", "in_stock", "available"} else "unknown",
                        url=row.get("link"),
                        checked_at=now_utc(),
                    )

                    raw = RawProduct(
                        provider=self.name,
                        external_id=str(item_id),
                        title=title,
                        brand=row.get("brand"),
                        description=row.get("description"),
                        url=row.get("link"),
                        image_urls=[row.get("image_link")] if row.get("image_link") else [],
                        gtin=row.get("gtin"),
                        mpn=row.get("mpn"),
                        country=params.country,
                        offers=[offer],
                    )
                    products.append(raw)
                    if len(products) >= params.limit:
                        break
            except Exception as exc:
                log.warning("Merchant feed parse error", extra={"url": feed_url, "error": str(exc)})

        return products
