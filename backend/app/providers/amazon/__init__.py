"""Amazon Provider Package."""
from __future__ import annotations

from app.providers.amazon.normalizer import normalize_amazon_product
from app.providers.amazon.parser import parse_amazon_search_page
from app.providers.amazon.provider import AmazonProvider
from app.providers.amazon.scraper import AmazonScraper
from app.providers.amazon.selectors import AMAZON_SELECTORS

__all__ = [
    "AmazonProvider",
    "AmazonScraper",
    "parse_amazon_search_page",
    "normalize_amazon_product",
    "AMAZON_SELECTORS",
]
