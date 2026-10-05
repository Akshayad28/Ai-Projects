"""Product Candidate and Field Validation Layer for Google Scraper.

Ensures only genuine shopping items are extracted and non-product DOM elements
(ads disclaimers, navigation, filter chips, empty wrappers) are safely discarded.
"""
from __future__ import annotations

import re
from typing import Optional
from bs4 import Tag

# Non-product keywords in title or container
_NON_PRODUCT_EXACT_TITLES = {
    "sponsored",
    "advertisement",
    "why this ad",
    "ad choices",
    "filters",
    "sort by",
    "next",
    "previous",
    "more results",
    "feedback",
    "privacy",
    "terms",
    "settings",
    "google apps",
    "sign in",
    "view offer",
    "view offers",
    "view product",
    "view details",
    "buy now",
    "shop now",
    "visit site",
    "see options",
    "check price",
}


def validate_title(title: Optional[str]) -> Optional[str]:
    """Validates that extracted title is a genuine product name."""
    if not title or not isinstance(title, str):
        return None
    cleaned = title.strip()
    if len(cleaned) < 3 or len(cleaned) > 400:
        return None
    if cleaned.lower() in _NON_PRODUCT_EXACT_TITLES:
        return None
    # Reject strings composed entirely of non-alphanumeric chars
    if not any(c.isalnum() for c in cleaned):
        return None
    return cleaned


def validate_price(price: Optional[float]) -> Optional[float]:
    """Validates that price is a positive, realistic monetary float."""
    if price is None:
        return None
    try:
        val = float(price)
        if 0.0 < val < 100_000_000.0:
            return round(val, 2)
        return None
    except (ValueError, TypeError):
        return None


def validate_rating(rating: Optional[float]) -> Optional[float]:
    """Validates that rating is within 0.0 to 5.0 scale."""
    if rating is None:
        return None
    try:
        r = float(rating)
        if 0.0 < r <= 5.0:
            return round(r, 2)
        return None
    except (ValueError, TypeError):
        return None


def validate_review_count(count: Optional[int]) -> Optional[int]:
    """Validates that review count is a non-negative integer."""
    if count is None:
        return None
    try:
        c = int(count)
        return c if c >= 0 else None
    except (ValueError, TypeError):
        return None


def validate_url(url: Optional[str]) -> Optional[str]:
    """Validates that destination URL is well-formed HTTP/HTTPS."""
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    return None


def is_product_candidate(element: Tag) -> bool:
    """Evaluates whether a DOM Tag has sufficient product signals to warrant parsing.

    A valid product candidate should display multiple product signals (e.g. price,
    shopping link, image, or merchant) and not match blacklisted container types.
    """
    if not isinstance(element, Tag):
        return False

    # 1. Reject elements that are explicitly navigation or UI utility
    tag_name = element.name.lower()
    if tag_name in ("nav", "header", "footer", "button", "script", "style"):
        return False

    classes = " ".join(element.get("class", [])).lower()
    role = (element.get("role") or "").lower()
    if role in ("navigation", "menubar", "search", "dialog"):
        return False

    # 2. Check inner text content
    text = element.get_text(strip=True)
    if len(text) < 4:
        return False

    if text.lower() in _NON_PRODUCT_EXACT_TITLES:
        return False

    # 3. Collect product signals
    signals = 0

    # Signal A: Contains currency or price pattern (₹, $, £, €, etc.)
    if re.search(r"[$₹£€¥]|(?:inr|usd|gbp|eur|aed|sgd|rs\.?)\s*\d", text, re.IGNORECASE):
        signals += 1

    # Signal B: Contains an anchor link
    if element.find("a", href=True):
        signals += 1

    # Signal C: Contains an image
    if element.find("img"):
        signals += 1

    # Signal D: Contains known shopping attribute or spec indicator
    if any(k in classes for k in ("sh-dgr", "pla-unit", "sh-dlr", "product", "item")):
        signals += 1

    # Candidate must have at least 2 distinct signals (e.g. link + price, or image + price)
    return signals >= 2
