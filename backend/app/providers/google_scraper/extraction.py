"""Multi-Layer Field Extraction for Google Shopping Results.

Implements layered extraction strategies:
- Layer 1: Primary CSS selectors
- Layer 2: Alternative / fallback selectors
- Layer 3: Semantic DOM attributes, microdata, aria-labels, srcset
- Layer 4: Validated pattern-based text extraction
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from bs4 import Tag

from app.providers.google_scraper.selectors import (
    AVAILABILITY_SELECTORS,
    IMAGE_SELECTORS,
    MERCHANT_SELECTORS,
    ORIGINAL_PRICE_SELECTORS,
    PRICE_SELECTORS,
    RATING_SELECTORS,
    REVIEW_COUNT_SELECTORS,
    SHIPPING_SELECTORS,
    TITLE_SELECTORS,
    URL_SELECTORS,
)
from app.providers.google_scraper.validation import (
    validate_price,
    validate_rating,
    validate_review_count,
    validate_title,
    validate_url,
)

# Currency symbol mapping
CURRENCY_SYMBOLS: Dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "usd": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "€": "EUR",
    "eur": "EUR",
    "aed": "AED",
    "dh": "AED",
    "dhs": "AED",
    "s$": "SGD",
    "sgd": "SGD",
    "c$": "CAD",
    "cad": "CAD",
    "a$": "AUD",
    "aud": "AUD",
    "¥": "JPY",
    "jpy": "JPY",
    "chf": "CHF",
}

DEFAULT_COUNTRY_CURRENCIES: Dict[str, str] = {
    "IN": "INR",
    "US": "USD",
    "GB": "GBP",
    "DE": "EUR",
    "AE": "AED",
    "SG": "SGD",
    "CA": "CAD",
    "AU": "AUD",
    "JP": "JPY",
    "FR": "EUR",
    "IT": "EUR",
    "ES": "EUR",
}


def parse_price_and_currency(
    price_str: Optional[str],
    default_currency: str = "INR",
) -> Tuple[Optional[float], Optional[str]]:
    """Robustly parses localized price string into numeric float and ISO-4217 currency."""
    if not price_str or not price_str.strip():
        return None, None

    raw = price_str.strip()

    # 1. Detect Currency (longest symbol first to prioritize e.g. 's$' over '$')
    detected_currency = None
    lower_raw = raw.lower()
    for symbol, code in sorted(CURRENCY_SYMBOLS.items(), key=lambda x: len(x[0]), reverse=True):
        if symbol in lower_raw or symbol in raw:
            detected_currency = code
            break

    currency = detected_currency or default_currency

    # 2. Extract and Normalize Numerical Portion
    cleaned = re.sub(r"(?i)\b(?:inr|usd|gbp|eur|aed|sgd|cad|aud|jpy|chf|rs\.?|dhs?|dh)\b", "", raw)
    cleaned = re.sub(r"[$₹£€¥]", "", cleaned).strip()

    # Handle thousands with spaces (e.g. '29 999')
    cleaned = re.sub(r"(\d)\s+(\d)", r"\1\2", cleaned)

    # Distinguish decimal comma from thousands comma
    if "," in cleaned and "." in cleaned:
        first_sep = cleaned.find(",")
        second_sep = cleaned.find(".")
        if first_sep < second_sep:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        if re.search(r",\d{1,2}$", cleaned) and currency in ("EUR", "DE"):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    # Extract digits with optional decimal point
    num_match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not num_match:
        return None, None

    try:
        val = float(num_match.group(1))
        validated = validate_price(val)
        return validated, currency
    except (ValueError, TypeError):
        return None, None


def extract_destination_url(raw_href: Optional[str]) -> Optional[str]:
    """Extracts actual retailer destination URL from Google link or redirect."""
    if not raw_href or not raw_href.strip():
        return None

    cleaned_href = html.unescape(raw_href.strip())

    # Check for Google redirect wrapper: /url?q=... or /url?url=...
    if "/url?" in cleaned_href:
        parsed = urlparse(cleaned_href)
        qs = parse_qs(parsed.query)

        # Priority 1: 'url' parameter
        if "url" in qs and qs["url"]:
            target = unquote(qs["url"][0])
            if target.startswith("http://") or target.startswith("https://"):
                return target

        # Priority 2: 'q' parameter
        if "q" in qs and qs["q"]:
            target = unquote(qs["q"][0])
            if (target.startswith("http://") or target.startswith("https://")) and "google.com/search" not in target:
                return target

    # Direct absolute HTTP/HTTPS URL
    if cleaned_href.startswith("http://") or cleaned_href.startswith("https://"):
        return cleaned_href

    # Internal Google Shopping product relative path
    if cleaned_href.startswith("/"):
        return f"https://www.google.com{cleaned_href}"

    return cleaned_href


def clean_retailer_name(raw_name: Optional[str]) -> Optional[str]:
    """Cleans seller/retailer name displayed on Google."""
    if not raw_name or not raw_name.strip():
        return None

    name = raw_name.strip()
    name = re.sub(r"^(?:from|by|at)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(?\d+(?:\.\d+)?\s*(?:★|stars?|\/5)?\)?$", "", name, flags=re.IGNORECASE)
    name = name.strip()

    if len(name) < 2 or len(name) > 100:
        return None
    return name


def parse_rating_and_reviews(
    rating_str: Optional[str],
    review_str: Optional[str],
) -> Tuple[Optional[float], Optional[int]]:
    """Extracts rating (float out of 5) and review count (int)."""
    rating = None
    review_count = None

    if rating_str:
        r_match = re.search(r"(\d+(?:\.\d+)?)", rating_str)
        if r_match:
            try:
                r_val = float(r_match.group(1))
                rating = validate_rating(r_val)
            except (ValueError, TypeError):
                pass

    if review_str:
        k_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK]", review_str)
        if k_match:
            try:
                review_count = validate_review_count(int(float(k_match.group(1)) * 1000))
            except (ValueError, TypeError):
                pass
        else:
            c_match = re.search(r"(\d[\d,]*)", review_str)
            if c_match:
                try:
                    review_count = validate_review_count(int(c_match.group(1).replace(",", "")))
                except (ValueError, TypeError):
                    pass

    return rating, review_count


# ── Multi-Layer Extractors per Field ─────────────────────────────────

def extract_title(card: Tag) -> Optional[str]:
    """Extracts product title using layered selectors, headings, and aria attributes."""
    # Layer 1 & 2: CSS Selectors
    for sel in TITLE_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            text = elem.get_text(strip=True) or elem.get("aria-label") or elem.get("title")
            val = validate_title(text)
            if val:
                return val

    # Layer 3: Microdata / Semantic attributes
    name_tag = card.find(attrs={"itemprop": "name"})
    if name_tag:
        val = validate_title(name_tag.get_text(strip=True))
        if val:
            return val

    # Layer 4: Any anchor tag with substantive text
    for a_tag in card.find_all("a"):
        val = validate_title(a_tag.get_text(strip=True))
        if val and len(val) >= 10:
            return val

    return None


def extract_price(card: Tag, default_currency: str = "INR") -> Tuple[Optional[float], str]:
    """Extracts current product price using layered CSS selectors, microdata, and text fallback."""
    # Layer 1 & 2: CSS Selectors
    for sel in PRICE_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            text = elem.get_text(strip=True) or elem.get("data-price")
            val, curr = parse_price_and_currency(text, default_currency=default_currency)
            if val is not None:
                return val, curr or default_currency

    # Layer 3: Microdata [itemprop='price']
    price_tag = card.find(attrs={"itemprop": "price"})
    if price_tag:
        raw_val = price_tag.get("content") or price_tag.get_text(strip=True)
        val, curr = parse_price_and_currency(raw_val, default_currency=default_currency)
        if val is not None:
            return val, curr or default_currency

    # Layer 4: Regex on entire card text
    card_text = card.get_text(" ", strip=True)
    price_match = re.search(r"([$₹£€¥]|(?:inr|usd|gbp|eur|aed|sgd|rs\.?)\s*)(\d[\d, ]*(?:\.\d{1,2})?)", card_text, re.IGNORECASE)
    if price_match:
        val, curr = parse_price_and_currency(price_match.group(0), default_currency=default_currency)
        if val is not None:
            return val, curr or default_currency

    return None, default_currency


def extract_original_price(card: Tag, current_price: Optional[float], default_currency: str = "INR") -> Optional[float]:
    """Extracts original/strikethrough price."""
    for sel in ORIGINAL_PRICE_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            val, _ = parse_price_and_currency(elem.get_text(strip=True), default_currency=default_currency)
            if val is not None and (current_price is None or val > current_price):
                return val
    return None


def extract_merchant(card: Tag) -> Optional[str]:
    """Extracts seller or merchant name using layered selectors and attributes."""
    for sel in MERCHANT_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            cleaned = clean_retailer_name(elem.get_text(strip=True) or elem.get("aria-label"))
            if cleaned:
                return cleaned

    seller_tag = card.find(attrs={"itemprop": "seller"})
    if seller_tag:
        cleaned = clean_retailer_name(seller_tag.get_text(strip=True))
        if cleaned:
            return cleaned

    return None


def extract_url(card: Tag) -> Optional[str]:
    """Extracts product destination link using layered selectors and anchor hrefs."""
    for sel in URL_SELECTORS:
        elem = card.select_one(sel)
        if elem and elem.get("href"):
            dest = extract_destination_url(str(elem.get("href")))
            validated = validate_url(dest)
            if validated:
                return validated

    for a_tag in card.find_all("a", href=True):
        dest = extract_destination_url(str(a_tag["href"]))
        validated = validate_url(dest)
        if validated and "google.com/search" not in validated:
            return validated

    return None


def extract_image_url(card: Tag) -> Optional[str]:
    """Extracts product image with high-resolution and lazy-loading support."""
    # Look for all img tags
    img_tags = card.find_all("img")
    for img in img_tags:
        # Check srcset first for highest resolution image
        srcset = img.get("srcset")
        if srcset:
            parts = [s.strip().split() for s in srcset.split(",") if s.strip()]
            if parts:
                best_url = parts[-1][0]
                if best_url.startswith("http://") or best_url.startswith("https://"):
                    return best_url

        # Check data attributes (lazy loaded images)
        for attr in ("data-src", "data-original", "data-image-src", "data-deferred-src", "src"):
            val = img.get(attr)
            if val and isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                return val.strip()

    return None


def extract_rating_and_reviews(card: Tag) -> Tuple[Optional[float], Optional[int]]:
    """Extracts rating value and review count."""
    rating_text = None
    for sel in RATING_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            rating_text = elem.get_text(strip=True) or elem.get("aria-label") or elem.get("title")
            if rating_text:
                break

    review_text = None
    for sel in REVIEW_COUNT_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            review_text = elem.get_text(strip=True) or elem.get("aria-label")
            if review_text:
                break

    return parse_rating_and_reviews(rating_text, review_text)


def extract_shipping(card: Tag) -> Optional[str]:
    """Extracts shipping / delivery promise text."""
    for sel in SHIPPING_SELECTORS:
        elem = card.select_one(sel)
        if elem:
            text = elem.get_text(strip=True)
            if any(w in text.lower() for w in ("delivery", "shipping", "free")):
                return text
    return None


def extract_availability(card: Tag) -> str:
    """Extracts stock availability status."""
    text_lower = card.get_text().lower()
    if "out of stock" in text_lower:
        return "out_of_stock"
    if "pre-order" in text_lower or "preorder" in text_lower:
        return "preorder"
    return "in_stock"
