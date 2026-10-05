"""URL Normalization and validation utilities."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_amazon_url(raw_url: str) -> str:
    """Extracts canonical Amazon product URL (dp/ASIN) removing tracking/session tokens."""
    if not raw_url:
        return ""

    if raw_url.startswith("/"):
        raw_url = f"https://www.amazon.in{raw_url}"

    # Extract ASIN via regex
    asin_match = re.search(r"/(?:dp|gp/product|d)/([A-Z0-9]{10})", raw_url)
    if asin_match:
        asin = asin_match.group(1)
        return f"https://www.amazon.in/dp/{asin}"

    # Fallback to cleaning query parameters
    parsed = urlparse(raw_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def normalize_flipkart_url(raw_url: str) -> str:
    """Normalizes Flipkart URL to clean canonical product path with pid."""
    if not raw_url:
        return ""

    if raw_url.startswith("/"):
        raw_url = f"https://www.flipkart.com{raw_url}"

    parsed = urlparse(raw_url)
    qs = parse_qs(parsed.query)

    clean_qs = {}
    if "pid" in qs:
        clean_qs["pid"] = qs["pid"][0]

    query_str = urlencode(clean_qs) if clean_qs else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query_str, ""))
