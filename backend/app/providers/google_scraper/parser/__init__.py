"""Google Scraper Modular Parser Package.

Exposes layout-specific parsers, layout detector, dispatcher, and field extraction helpers.
"""
from __future__ import annotations

from app.providers.google_scraper.extraction import (
    clean_retailer_name,
    extract_availability,
    extract_destination_url,
    extract_image_url,
    extract_merchant,
    extract_original_price,
    extract_price,
    extract_rating_and_reviews,
    extract_shipping,
    extract_title,
    extract_url,
    parse_price_and_currency,
    parse_rating_and_reviews,
)
from app.providers.google_scraper.parser.base import GoogleLayoutParser
from app.providers.google_scraper.parser.carousel_parser import CarouselParser
from app.providers.google_scraper.parser.dispatcher import (
    GoogleParserDispatcher,
    parse_google_shopping_page,
)
from app.providers.google_scraper.parser.generic_parser import GenericParser
from app.providers.google_scraper.parser.grid_parser import GridParser
from app.providers.google_scraper.parser.list_parser import ListParser

__all__ = [
    "GoogleLayoutParser",
    "GoogleParserDispatcher",
    "GridParser",
    "CarouselParser",
    "ListParser",
    "GenericParser",
    "parse_google_shopping_page",
    "parse_price_and_currency",
    "extract_destination_url",
    "clean_retailer_name",
    "parse_rating_and_reviews",
    "extract_title",
    "extract_price",
    "extract_original_price",
    "extract_merchant",
    "extract_url",
    "extract_image_url",
    "extract_shipping",
    "extract_availability",
]
