"""Firecrawl Product and Offer Parser.

Converts extracted product details into domain RawProduct, RawOffer, and ProviderProduct
records with full provenance, currency normalization, and retailer identification.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.providers.base.models import ProviderPrice, ProviderProduct
from app.providers.firecrawl.schemas import FirecrawlExtractedProduct
from app.providers.firecrawl.validators import clean_availability
from app.schemas.domain import RawOffer, RawProduct, RawReview, now_utc

# Known retailer domain mappings
KNOWN_RETAILERS: Dict[str, str] = {
    "amazon.in": "Amazon India",
    "amazon.com": "Amazon",
    "amazon.co.uk": "Amazon UK",
    "amazon.de": "Amazon Germany",
    "flipkart.com": "Flipkart",
    "ebay.com": "eBay",
    "ebay.in": "eBay India",
    "bestbuy.com": "Best Buy",
    "walmart.com": "Walmart",
    "target.com": "Target",
    "croma.com": "Croma",
    "reliancedigital.in": "Reliance Digital",
    "tatacliq.com": "Tata CLiQ",
    "myntra.com": "Myntra",
    "nykaa.com": "Nykaa",
    "ikea.com": "IKEA",
    "featherlitefurniture.com": "Featherlite",
    "greensoul.online": "Green Soul",
    "pepperfry.com": "Pepperfry",
    "urbanladder.com": "Urban Ladder",
    "sleepycat.in": "SleepyCat",
    "wakefit.co": "Wakefit",
    "apple.com": "Apple Store",
    "samsung.com": "Samsung Store",
    "dell.com": "Dell",
    "hp.com": "HP Store",
    "lenovo.com": "Lenovo",
    "mi.com": "Xiaomi Store",
    "oneplus.in": "OnePlus",
}

# Currency symbol mapping
CURRENCY_SYMBOLS: Dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "inr": "INR",
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "aed": "AED",
    "c$": "CAD",
    "cad": "CAD",
    "a$": "AUD",
    "aud": "AUD",
    "s$": "SGD",
    "sgd": "SGD",
    "¥": "JPY",
    "jpy": "JPY",
}


def extract_retailer_info(url: str) -> Tuple[str, str]:
    """Extracts the domain and a human-readable retailer name from a URL."""
    try:
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Check known retailers
        for dom, name in KNOWN_RETAILERS.items():
            if netloc == dom or netloc.endswith(f".{dom}"):
                return netloc, name

        # Format unknown domain into a clean retailer name
        domain_parts = netloc.split(".")
        if len(domain_parts) >= 2:
            base_name = domain_parts[0].capitalize()
            return netloc, base_name

        return netloc, netloc.capitalize()
    except Exception:
        return "web", "Independent Retailer"


def parse_price_string(price_text: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """Parses a price string containing arbitrary currency symbols and separators.

    Examples:
    '₹34,999' -> (34999.0, 'INR')
    'Rs. 34,990.00' -> (34990.0, 'INR')
    '$699' -> (699.0, 'USD')
    '€799' -> (799.0, 'EUR')
    'AED 2,999' -> (2999.0, 'AED')
    """
    if not price_text or not isinstance(price_text, str):
        return None, None

    cleaned = price_text.strip()
    detected_currency: Optional[str] = None

    # Detect currency prefix or token
    for symbol, curr in CURRENCY_SYMBOLS.items():
        if re.search(rf"(?:^|\s){re.escape(symbol)}(?:\s|\.|\d)", cleaned, re.IGNORECASE):
            detected_currency = curr
            break

    # Strip symbols and non-numeric chars except digits and decimals
    digits_only = re.sub(r"[^\d.]", "", cleaned)
    if not digits_only:
        return None, detected_currency

    # Handle multiple decimal points if present
    parts = digits_only.split(".")
    if len(parts) > 2:
        digits_only = "".join(parts[:-1]) + "." + parts[-1]

    try:
        amount = float(digits_only)
        return amount, detected_currency
    except Exception:
        return None, detected_currency


def to_raw_product(
    extracted: FirecrawlExtractedProduct,
    source_url: str,
    default_currency: str = "INR",
    query: str = "",
) -> RawProduct:
    """Converts a FirecrawlExtractedProduct into a canonical ShopBuddy RawProduct and RawOffer."""
    retailer_domain, retailer_name = extract_retailer_info(source_url)
    if extracted.retailer and extracted.retailer.strip().lower() not in ("not available", "none", "n/a", "null", "unknown"):
        retailer_name = extracted.retailer

    effective_url = extracted.canonical_url or extracted.product_url or source_url

    # Generate a deterministic external ID based on canonical URL
    id_source = effective_url or extracted.product_name or "unknown"
    external_id = f"fc_{hashlib.sha256(id_source.encode('utf-8')).hexdigest()[:16]}"

    # Currency normalization
    final_currency = extracted.currency or default_currency
    final_price = extracted.price
    if final_price is None and extracted.price_text:
        parsed_p, parsed_c = parse_price_string(extracted.price_text)
        final_price = parsed_p
        if parsed_c:
            final_currency = parsed_c

    # Map currency symbols to standard ISO 4217
    curr_upper = final_currency.strip().upper()
    if curr_upper in ("₹", "RS", "RS.", "INR"):
        final_currency = "INR"
    elif curr_upper in ("$", "USD"):
        final_currency = "USD"
    elif curr_upper in ("€", "EUR"):
        final_currency = "EUR"
    elif curr_upper in ("£", "GBP"):
        final_currency = "GBP"

    # Build specifications dictionary
    specs: Dict[str, Any] = dict(extracted.specifications) if extracted.specifications else {}
    for attr in extracted.attributes:
        if attr.key and attr.value:
            specs[attr.key] = attr.value

    # Include physical variant attributes if present
    if extracted.color:
        specs["color"] = extracted.color
    if extracted.size:
        specs["size"] = extracted.size
    if extracted.capacity:
        specs["capacity"] = extracted.capacity
    if extracted.configuration:
        specs["configuration"] = extracted.configuration
    if extracted.variant:
        specs["variant"] = extracted.variant

    # Collect images
    images: List[str] = []
    if extracted.image_url:
        images.append(extracted.image_url)
    for extra_img in extracted.additional_images:
        if extra_img and extra_img not in images:
            images.append(extra_img)

    # Reviews
    raw_reviews: List[RawReview] = []
    if extracted.review_summary:
        raw_reviews.append(
            RawReview(
                source="firecrawl",
                external_id=external_id,
                rating=extracted.rating,
                title="Verified Web Review",
                text=extracted.review_summary,
                verified=False,
            )
        )

    clean_seller = extracted.seller_name or extracted.seller or retailer_name
    if not clean_seller or clean_seller.strip().lower() in ("not available", "none", "n/a", "null", "unknown", ""):
        clean_seller = retailer_name or "Independent Retailer"

    # Build RawOffer
    offer = RawOffer(
        provider="firecrawl",
        retailer_name=retailer_name or "Independent Retailer",
        retailer_domain=retailer_domain,
        seller_name=clean_seller,
        seller_rating=extracted.seller_rating,
        price_amount=final_price,
        currency=final_currency,
        original_price=extracted.original_price,
        shipping_amount=extracted.shipping_cost,
        delivery_estimate=extracted.delivery_information,
        availability=clean_availability(extracted.availability or extracted.stock_status),
        url=effective_url,
        return_policy=extracted.return_policy,
        warranty=extracted.warranty,
        confidence=extracted.confidence,
    )

    # Build RawProduct
    raw_prod = RawProduct(
        provider="firecrawl",
        external_id=external_id,
        title=extracted.product_name or "Unknown Product",
        brand=extracted.brand,
        model=extracted.model,
        description=extracted.description,
        gtin=extracted.gtin,
        upc=extracted.upc,
        ean=extracted.ean,
        mpn=extracted.mpn or extracted.model_number,
        asin=extracted.asin,
        sku=extracted.sku,
        url=effective_url,
        image_urls=images,
        rating=extracted.rating,
        review_count=extracted.review_count,
        rating_source="firecrawl",
        specs=specs,
        offers=[offer],
        reviews=raw_reviews,
        extra={
            "features": extracted.features,
            "source_type": "search_discovery",
            "search_query": query,
            "extraction_method": extracted.extraction_method,
            "source_domain": retailer_domain,
        },
        is_demo=False,
    )

    return raw_prod


def to_provider_product(raw: RawProduct) -> ProviderProduct:
    """Converts a RawProduct to a ProviderProduct for ShoppingProvider compatibility."""
    price_amount = None
    currency = "INR"
    original_price = None
    discount = None
    availability = "unknown"
    seller = None

    if raw.offers:
        o = raw.offers[0]
        price_amount = o.price_amount
        currency = o.currency or "INR"
        original_price = o.original_price
        if original_price and price_amount and original_price > price_amount:
            discount = original_price - price_amount
        availability = o.availability
        seller = o.seller_name or o.retailer_name or "Independent Retailer"

    identifiers = {}
    for key, val in [
        ("gtin", raw.gtin),
        ("upc", raw.upc),
        ("ean", raw.ean),
        ("mpn", raw.mpn),
        ("asin", raw.asin),
        ("sku", raw.sku),
    ]:
        if val:
            identifiers[key] = val

    return ProviderProduct(
        provider="firecrawl",
        provider_product_id=raw.external_id,
        title=raw.title,
        url=raw.url,
        image_url=raw.image_urls[0] if raw.image_urls else None,
        image_urls=raw.image_urls,
        brand=raw.brand,
        model=raw.model,
        price=ProviderPrice(
            amount=price_amount,
            currency=currency,
            original_price=original_price,
            discount=discount,
        ),
        rating=raw.rating,
        review_count=raw.review_count,
        availability=availability,
        seller=seller,
        identifiers=identifiers,
        specifications=raw.specs,
        variant_attributes={
            k: str(v) for k, v in raw.specs.items() if k in ("ram", "storage", "color", "size", "capacity", "variant")
        },
        raw_metadata=raw.extra,
        is_demo=False,
    )


def search_item_to_raw_product(
    item: Any,
    default_currency: str = "INR",
    query: str = "",
) -> Optional[RawProduct]:
    """Converts a FirecrawlSearchResultItem into a preliminary RawProduct immediately for zero-wait display."""
    item_url = getattr(item, "url", None)
    if not item_url or not isinstance(item_url, str):
        return None

    title = getattr(item, "title", None)
    if not title or not isinstance(title, str) or not title.strip():
        return None

    retailer_name, retailer_domain = extract_retailer_info(item_url)
    domain = retailer_domain or getattr(item, "domain", None) or urlparse(item_url).netloc.lower().replace("www.", "")

    desc = getattr(item, "description", "") or ""
    if not isinstance(desc, str):
        desc = ""
    combined_text = f"{title} {desc}"
    detected_price = None
    price_match = re.search(r"(?:₹|Rs\.?|INR|\$|£|€)\s*([\d,]+(?:\.\d{2})?)", combined_text, re.IGNORECASE)
    if price_match:
        try:
            detected_price = float(price_match.group(1).replace(",", ""))
        except ValueError:
            pass

    external_id = f"fc_{hashlib.md5(item_url.encode()).hexdigest()[:12]}"
    offer = RawOffer(
        provider="firecrawl",
        retailer_name=retailer_name,
        retailer_domain=domain,
        price_amount=detected_price,
        currency=default_currency,
        availability="in_stock",
        url=item_url,
        confidence=0.85,
        condition="new",
        source="search_discovery",
    )

    return RawProduct(
        provider="firecrawl",
        external_id=external_id,
        title=title,
        url=item_url,
        image_urls=[],
        specs={"snippet": desc} if desc else {},
        offers=[offer],
        extra={
            "source_type": "search_discovery_serp",
            "search_query": query,
            "source_domain": domain,
        },
        is_demo=False,
    )

