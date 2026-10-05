"""Amazon Data Normalizer."""
from __future__ import annotations

from typing import Any, Dict
from app.providers.base.models import ProviderPrice, ProviderProduct
from app.utils.text_normalization import extract_brand_from_title, extract_variant_attributes


def normalize_amazon_product(raw: Dict[str, Any]) -> ProviderProduct:
    """Converts raw scraped Amazon dict into a standardized ProviderProduct."""
    title = raw["title"]
    brand = extract_brand_from_title(title)
    variant_attrs = extract_variant_attributes(title)

    price_amt = raw.get("price")
    orig_amt = raw.get("original_price")
    discount = (orig_amt - price_amt) if (orig_amt and price_amt and orig_amt > price_amt) else None

    price = ProviderPrice(
        amount=price_amt,
        currency="INR",
        original_price=orig_amt,
        discount=discount,
    )

    asin = raw.get("asin") or ""
    identifiers = {"asin": asin}

    image_urls = [raw["image_url"]] if raw.get("image_url") else []

    return ProviderProduct(
        provider="amazon",
        provider_product_id=asin,
        title=title,
        url=raw.get("url"),
        image_url=raw.get("image_url"),
        image_urls=image_urls,
        brand=brand,
        price=price,
        rating=raw.get("rating"),
        review_count=raw.get("review_count"),
        availability=raw.get("availability", "unknown"),
        identifiers=identifiers,
        variant_attributes=variant_attrs,
        raw_metadata={"is_sponsored": raw.get("is_sponsored", False)},
    )
