"""Dispatcher for selecting and executing the appropriate Google Shopping parser."""
from __future__ import annotations

from typing import List, Tuple
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.google_scraper.extraction import (
    clean_retailer_name,
    extract_destination_url,
    parse_price_and_currency,
    parse_rating_and_reviews,
)
from app.providers.google_scraper.models import ExtractionHealth, GoogleLayout, GoogleScrapedItem
from app.providers.google_scraper.parser.base import GoogleLayoutParser
from app.providers.google_scraper.parser.carousel_parser import CarouselParser
from app.providers.google_scraper.parser.generic_parser import GenericParser
from app.providers.google_scraper.parser.grid_parser import GridParser
from app.providers.google_scraper.parser.list_parser import ListParser

log = get_logger(__name__)


class GoogleParserDispatcher:
    """Detects Google result layout and dispatches to the corresponding parser."""

    def __init__(self) -> None:
        self.grid_parser = GridParser()
        self.carousel_parser = CarouselParser()
        self.list_parser = ListParser()
        self.generic_parser = GenericParser()

    def detect_layout(self, soup: BeautifulSoup) -> GoogleLayout:
        """Inspects DOM structure to detect layout type using multiple structural signals."""
        if self.grid_parser.can_parse(soup):
            return GoogleLayout.SHOPPING_GRID
        if self.carousel_parser.can_parse(soup):
            return GoogleLayout.SHOPPING_CAROUSEL
        if self.list_parser.can_parse(soup):
            return GoogleLayout.SHOPPING_LIST
        return GoogleLayout.UNKNOWN

    def get_parser_for_layout(self, layout: GoogleLayout) -> GoogleLayoutParser:
        """Returns the parser instance for a given layout."""
        if layout == GoogleLayout.SHOPPING_GRID:
            return self.grid_parser
        if layout == GoogleLayout.SHOPPING_CAROUSEL:
            return self.carousel_parser
        if layout == GoogleLayout.SHOPPING_LIST:
            return self.list_parser
        return self.generic_parser

    def parse(
        self,
        html_content: str,
        country: str = "IN",
        currency: str = "INR",
        max_results: int = 20,
    ) -> Tuple[List[GoogleScrapedItem], ExtractionHealth]:
        """Parses HTML by detecting layout, executing dedicated parser, and evaluating degradation."""
        if not html_content or not html_content.strip():
            return [], ExtractionHealth(layout=GoogleLayout.UNKNOWN)

        soup = BeautifulSoup(html_content, "lxml")
        layout = self.detect_layout(soup)
        parser = self.get_parser_for_layout(layout)

        log.info(f"Google parser selected layout: {layout.value}")
        items, health = parser.parse(
            soup=soup,
            country=country,
            currency=currency,
            max_results=max_results,
        )

        # Fallback to generic semantic parser if dedicated parser found cards but 0 products
        if not items and layout != GoogleLayout.UNKNOWN:
            log.info("Dedicated parser yielded zero products. Attempting generic semantic fallback.")
            fallback_items, fallback_health = self.generic_parser.parse(
                soup=soup,
                country=country,
                currency=currency,
                max_results=max_results,
            )
            if fallback_items:
                items = fallback_items
                health = fallback_health

        # Check for parser degradation
        settings = get_settings()
        threshold = getattr(settings, "google_extraction_health_threshold", 0.2)
        if health.is_degraded(threshold=threshold):
            log.warning(
                "Google extraction health degraded; possible DOM/layout change.",
                extra={
                    "layout": layout.value,
                    "cards_found": health.cards_found,
                    "products_parsed": health.products_parsed,
                    "threshold": threshold,
                },
            )

        return items, health


# Singleton dispatcher instance
_dispatcher = GoogleParserDispatcher()


def parse_google_shopping_page(
    html_content: str,
    country: str = "IN",
    currency: str = "INR",
    max_results: int = 20,
) -> List[GoogleScrapedItem]:
    """Top-level functional entry point preserving backwards compatibility."""
    items, _ = _dispatcher.parse(
        html_content=html_content,
        country=country,
        currency=currency,
        max_results=max_results,
    )
    return items
