"""Firecrawl Validators & Sanitizers.

Performs URL validation, URL classification, product candidate verification,
data integrity checks, and prompt-injection sanitization.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.providers.firecrawl.schemas import FirecrawlExtractedProduct, URLClassification

# Standard valid currencies
KNOWN_CURRENCIES = {
    "INR", "USD", "EUR", "GBP", "AED", "CAD", "AUD", "SGD", "JPY", "CNY", "KRW",
    "THB", "MYR", "IDR", "PHP", "VND", "BRL", "MXN", "ZAR", "SAR", "QAR", "KWD"
}

# Standard availability mappings
AVAILABILITY_MAP = {
    "in_stock": "in_stock",
    "instock": "in_stock",
    "in stock": "in_stock",
    "available": "in_stock",
    "limited": "limited",
    "low_stock": "limited",
    "low stock": "limited",
    "few left": "limited",
    "out_of_stock": "out_of_stock",
    "outofstock": "out_of_stock",
    "out of stock": "out_of_stock",
    "sold out": "out_of_stock",
    "unavailable": "out_of_stock",
    "preorder": "preorder",
    "pre-order": "preorder",
    "backorder": "preorder",
}

# Regex patterns for URL classification
_PRODUCT_PATH_PATTERNS = [
    r"/p(?:roduct)?s?/",
    r"/dp/[A-Z0-9]{8,12}",
    r"/item(?:s)?/",
    r"/ip/[a-zA-Z0-9-]+/\d+",
    r"/product-page/",
    r"/pd/",
    r"/buy-[a-zA-Z0-9-]+",
    r"/[a-zA-Z0-9-]+-p-\d+",
    r"/[a-zA-Z0-9-]+/p/\d+",
]

_CATEGORY_PATH_PATTERNS = [
    r"/c(?:ategory)?s?/",
    r"/collections?/",
    r"/departments?/",
    r"/browse/",
    r"/all-[a-zA-Z0-9-]+",
]

_SEARCH_PATH_PATTERNS = [
    r"/search(?:/|\?)",
    r"\?q=",
    r"\?s=",
    r"/find/",
]

_ARTICLE_REVIEW_PATTERNS = [
    r"/blog/",
    r"/article/",
    r"/news/",
    r"/review(?:s)?/",
    r"/best-",
    r"/top-",
    r"reddit\.com",
    r"quora\.com",
    r"medium\.com",
    r"forum\.",
]

_IRRELEVANT_PATH_PATTERNS = [
    r"/login",
    r"/signin",
    r"/signup",
    r"/account",
    r"/cart",
    r"/checkout",
    r"/contact",
    r"/privacy",
    r"/terms",
    r"/about-us",
    r"/help",
    r"/faq",
    r"/support",
    r"/sitemap",
    r"youtube\.com",
    r"youtu\.be",
    r"vimeo\.com",
    r"tiktok\.com",
    r"instagram\.com",
    r"facebook\.com",
    r"twitter\.com",
]

# Obvious non-product page titles
_REJECT_TITLES = [
    r"page not found",
    r"404 not found",
    r"access denied",
    r"just a moment\.\.\.",
    r"attention required",
    r"security check",
    r"robot check",
    r"log in",
    r"sign in",
    r"shopping cart",
    r"error \d+",
]

# Prompt injection signatures in untrusted webpage text
_INJECTION_SIGNATURES = [
    r"ignore (?:all )?previous instructions",
    r"ignore above",
    r"system prompt",
    r"reveal (?:your )?api key",
    r"print your secret",
    r"assistant instruction",
    r"call this url",
    r"<script",
    r"javascript:",
]


def is_valid_url(url: Optional[str]) -> bool:
    """Validates that a URL is a well-formed HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc) and "." in parsed.netloc
    except Exception:
        return False


def classify_url(url: str, title: str = "", description: str = "") -> URLClassification:
    """Classifies a URL into product page, category, search, review, or irrelevant."""
    if not is_valid_url(url):
        return URLClassification.IRRELEVANT_PAGE

    url_lower = url.strip().lower()
    text_lower = f"{title} {description}".lower()

    # 1. Check irrelevant domains and paths
    for pattern in _IRRELEVANT_PATH_PATTERNS:
        if re.search(pattern, url_lower):
            return URLClassification.IRRELEVANT_PAGE

    parsed = urlparse(url_lower)
    path = parsed.path.strip("/")

    # Empty path is a homepage / root domain, not a product page
    if not path:
        return URLClassification.RETAILER_CATEGORY

    # 2. Check search pages and filtered query listings
    if "/s?" in url_lower or "&rh=" in url_lower:
        return URLClassification.SEARCH_PAGE
    for pattern in _SEARCH_PATH_PATTERNS:
        if re.search(pattern, url_lower):
            return URLClassification.SEARCH_PAGE

    # 3. Check review / article / discussion
    for pattern in _ARTICLE_REVIEW_PATTERNS:
        if re.search(pattern, url_lower):
            return URLClassification.ARTICLE_REVIEW

    # 4. Check category / collection paths
    for pattern in _CATEGORY_PATH_PATTERNS:
        if re.search(pattern, url_lower):
            return URLClassification.RETAILER_CATEGORY

    # 5. Check product page indicators
    for pattern in _PRODUCT_PATH_PATTERNS:
        if re.search(pattern, url_lower):
            return URLClassification.PRODUCT_PAGE

    # Fallback heuristics based on URL depth
    path_parts = [p for p in path.split("/") if p]
    if len(path_parts) >= 2:
        return URLClassification.PRODUCT_PAGE

    return URLClassification.RETAILER_CATEGORY


def sanitize_untrusted_text(text: Optional[str], max_len: int = 2000) -> Optional[str]:
    """Sanitizes scraped webpage text to neutralize potential prompt injections."""
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip()
    for sig in _INJECTION_SIGNATURES:
        cleaned = re.sub(sig, "[FILTERED]", cleaned, flags=re.IGNORECASE)

    # Neutralize control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned[:max_len]


def clean_availability(val: Optional[str]) -> str:
    """Normalizes arbitrary availability strings into canonical values."""
    if not val:
        return "unknown"
    normalized = val.strip().lower()
    return AVAILABILITY_MAP.get(normalized, "unknown")


def validate_extracted_product(prod: FirecrawlExtractedProduct) -> Tuple[bool, Optional[str]]:
    """Validates extracted product data against ShopBuddy data integrity requirements.

    Never invents facts. A product with name + valid URL is considered valid, but
    obvious non-product pages and garbage extractions are rejected.
    """
    # 1. Product title check
    if not prod.product_name or not prod.product_name.strip():
        return False, "Missing product name"

    title_clean = prod.product_name.strip()
    if len(title_clean) < 3:
        return False, "Product name too short"

    # 2. Reject obvious non-product titles (404, Access Denied, Login, etc.)
    for pattern in _REJECT_TITLES:
        if re.search(pattern, title_clean, flags=re.IGNORECASE):
            return False, f"Non-product page detected from title: '{title_clean}'"

    # 3. URL validity check
    effective_url = prod.canonical_url or prod.product_url
    if effective_url and not is_valid_url(effective_url):
        return False, f"Invalid product URL: {effective_url}"

    # 4. Price check (if price is present, it must be positive)
    if prod.price is not None:
        if not isinstance(prod.price, (int, float)) or prod.price < 0:
            return False, f"Invalid non-numeric or negative price: {prod.price}"

    # 5. Rating check (must be within 0.0 to 5.0)
    if prod.rating is not None:
        if not isinstance(prod.rating, (int, float)) or prod.rating < 0.0 or prod.rating > 5.0:
            prod.rating = None  # Do not reject the entire product; reset invalid rating to None

    # 6. Review count check (must be >= 0)
    if prod.review_count is not None:
        if not isinstance(prod.review_count, (int, float)) or prod.review_count < 0:
            prod.review_count = None

    # 7. Image URL check
    if prod.image_url and not is_valid_url(prod.image_url):
        prod.image_url = None

    return True, None
