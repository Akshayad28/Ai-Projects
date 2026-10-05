"""Flipkart Data Normalizer."""
from __future__ import annotations

from typing import Any, Dict
from app.providers.base.models import ProviderPrice, ProviderProduct
from app.utils.text_normalization import extract_brand_from_title, extract_variant_attributes


def normalize_flipkart_product(raw: Dict[str, Any]) -> ProviderProduct:
    """Standardizes raw scraped Flipkart dict into a canonical ProviderProduct."""
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

    pid = raw.get("pid") or ""
    identifiers = {"flipkart_pid": pid}

    image_urls = [raw["image_url"]] if raw.get("image_url") else []

    return ProviderProduct(
        provider="flipkart",
        provider_product_id=pid,
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
        raw_metadata={},
    )
