"""Flipkart Provider Package."""
from __future__ import annotations

from app.providers.flipkart.normalizer import normalize_flipkart_product
from app.providers.flipkart.parser import parse_flipkart_search_page
from app.providers.flipkart.provider import FlipkartProvider
from app.providers.flipkart.scraper import FlipkartScraper
from app.providers.flipkart.selectors import FLIPKART_SELECTORS

__all__ = [
    "FlipkartProvider",
    "FlipkartScraper",
    "parse_flipkart_search_page",
    "normalize_flipkart_product",
    "FLIPKART_SELECTORS",
]
