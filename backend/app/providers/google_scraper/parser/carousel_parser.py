"""Shopping Carousel Layout Parser for Google Shopping."""
from __future__ import annotations

from typing import List, Tuple
from bs4 import BeautifulSoup

from app.providers.google_scraper.extraction import (
    DEFAULT_COUNTRY_CURRENCIES,
    extract_availability,
    extract_image_url,
    extract_merchant,
    extract_original_price,
    extract_price,
    extract_rating_and_reviews,
    extract_shipping,
    extract_title,
    extract_url,
)
from app.providers.google_scraper.models import ExtractionHealth, GoogleLayout, GoogleScrapedItem
from app.providers.google_scraper.parser.base import GoogleLayoutParser
from app.providers.google_scraper.selectors import CAROUSEL_CARD_SELECTORS
from app.providers.google_scraper.validation import is_product_candidate


class CarouselParser(GoogleLayoutParser):
    """Parses Google Shopping horizontal carousel and PLA product units."""

    layout_type = GoogleLayout.SHOPPING_CAROUSEL

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Returns True if carousel elements or PLA units are detected."""
        for sel in CAROUSEL_CARD_SELECTORS:
            if len(soup.select(sel)) >= 2:
                return True
        return False

    def parse(
        self,
        soup: BeautifulSoup,
        country: str = "IN",
        currency: str = "INR",
        max_results: int = 20,
    ) -> Tuple[List[GoogleScrapedItem], ExtractionHealth]:
        health = ExtractionHealth(layout=self.layout_type)
        default_curr = currency or DEFAULT_COUNTRY_CURRENCIES.get(country.upper(), "INR")

        cards = []
        for sel in CAROUSEL_CARD_SELECTORS:
            found = soup.select(sel)
            if found:
                cards = found
                break

        health.cards_found = len(cards)
        items: List[GoogleScrapedItem] = []

        for card in cards:
            if len(items) >= max_results:
                break

            if not is_product_candidate(card):
                continue

            health.products_detected += 1

            title = extract_title(card)
            if title:
                health.products_with_title += 1
            else:
                continue

            price_val, item_curr = extract_price(card, default_currency=default_curr)
            if price_val is not None:
                health.products_with_price += 1
            else:
                continue

            orig_price = extract_original_price(card, price_val, default_currency=item_curr)

            retailer = extract_merchant(card)
            if retailer:
                health.products_with_merchant += 1

            url = extract_url(card)
            if url:
                health.products_with_url += 1

            image_url = extract_image_url(card)
            if image_url:
                health.products_with_image += 1

            rating, review_count = extract_rating_and_reviews(card)
            if rating:
                health.products_with_rating += 1
            if review_count:
                health.products_with_review_count += 1

            shipping = extract_shipping(card)
            availability = extract_availability(card)

            item = GoogleScrapedItem(
                title=title,
                price_amount=price_val,
                currency=item_curr,
                original_price=orig_price,
                retailer_name=retailer,
                url=url,
                image_url=image_url,
                rating=rating,
                review_count=review_count,
                availability=availability,
                shipping_text=shipping,
                country=country,
                layout=self.layout_type.value,
            )
            items.append(item)
            health.products_parsed += 1

        return items, health
