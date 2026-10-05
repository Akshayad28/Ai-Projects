"""Generic / Semantic Fallback Parser for Unknown Google Layouts."""
from __future__ import annotations

import re
from typing import List, Tuple
from bs4 import BeautifulSoup, Tag

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
from app.providers.google_scraper.validation import is_product_candidate


class GenericParser(GoogleLayoutParser):
    """Fallback parser that applies semantic DOM heuristics when layout is UNKNOWN."""

    layout_type = GoogleLayout.UNKNOWN

    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Always returns True as the universal fallback parser."""
        return True

    def parse(
        self,
        soup: BeautifulSoup,
        country: str = "IN",
        currency: str = "INR",
        max_results: int = 20,
    ) -> Tuple[List[GoogleScrapedItem], ExtractionHealth]:
        health = ExtractionHealth(layout=self.layout_type)
        default_curr = currency or DEFAULT_COUNTRY_CURRENCIES.get(country.upper(), "INR")

        # Find candidate containers via semantic heuristics:
        # 1. Tags with schema.org Product microdata
        candidate_tags: List[Tag] = soup.find_all(attrs={"itemtype": re.compile(r"schema\.org/Product", re.I)})

        # 2. If no microdata, search for containers that hold price text and an anchor
        if not candidate_tags:
            seen_containers = set()
            # Find all elements that look like price indicators
            price_nodes = soup.find_all(string=re.compile(r"[$₹£€¥]|(?:inr|usd|gbp|eur|aed|sgd|rs\.?)\s*\d", re.I))
            for p_node in price_nodes:
                parent = p_node.find_parent(["div", "article", "li"])
                if parent and id(parent) not in seen_containers:
                    # Climb up if container is too small to contain title + link
                    ancestor = parent
                    for _ in range(3):
                        if ancestor and ancestor.find("a") and (ancestor.find("h3") or ancestor.find("h4") or len(ancestor.get_text()) > 20):
                            break
                        if ancestor.parent and ancestor.parent.name in ("div", "article", "li"):
                            ancestor = ancestor.parent
                    if ancestor and id(ancestor) not in seen_containers:
                        seen_containers.add(id(ancestor))
                        candidate_tags.append(ancestor)

        health.cards_found = len(candidate_tags)
        items: List[GoogleScrapedItem] = []

        for card in candidate_tags:
            if len(items) >= max_results:
                break

            if not is_product_candidate(card):
                continue

            health.products_detected += 1

            title = extract_title(card)
            if not title:
                continue
            health.products_with_title += 1

            price_val, item_curr = extract_price(card, default_currency=default_curr)
            if price_val is None:
                continue
            health.products_with_price += 1

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
