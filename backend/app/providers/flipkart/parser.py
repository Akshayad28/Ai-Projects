"""Flipkart Search Results Parser.

Extracts only observed data from Flipkart HTML cards without inventing missing attributes.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.providers.flipkart.selectors import FLIPKART_SELECTORS
from app.utils.currency import clean_price_string
from app.utils.url_utils import normalize_flipkart_url

log = get_logger(__name__)


def parse_flipkart_search_page(html_content: str, max_items: int = 20) -> List[Dict[str, Any]]:
    """Parses Flipkart search results HTML into raw dictionaries."""
    soup = BeautifulSoup(html_content, "lxml")
    cards: List[Tag] = []

    for card_sel in FLIPKART_SELECTORS["product_cards"]:
        found = soup.select(card_sel)
        if found:
            cards = found
            break

    results: List[Dict[str, Any]] = []

    for card in cards:
        if len(results) >= max_items:
            break

        # Title & Brand
        brand_elem = card.select_one("div._2WkVRV, span._2WkVRV")
        extracted_brand = brand_elem.get_text(strip=True) if brand_elem else None

        title = None
        for t_sel in FLIPKART_SELECTORS["title"]:
            t_elem = card.select_one(t_sel)
            if t_elem:
                raw_text = t_elem.get("title") or t_elem.get("alt") or t_elem.get_text(strip=True)
                if raw_text and len(raw_text) > 3:
                    title = raw_text
                    break

        # If title is just the brand or very short, look for subtitle or combine with brand
        if extracted_brand:
            if not title or title.strip().lower() == extracted_brand.strip().lower():
                # Check for secondary title link (e.g., a.WKTcLC or a[title])
                sub_elem = card.select_one("a.WKTcLC, a.wjcEIp, a.s1Q9rs, a[title]")
                if sub_elem:
                    sub_text = sub_elem.get("title") or sub_elem.get_text(strip=True)
                    if sub_text and sub_text.strip().lower() != extracted_brand.strip().lower():
                        title = f"{extracted_brand} {sub_text}"
            elif extracted_brand.lower() not in title.lower() and len(title) < 40:
                title = f"{extracted_brand} {title}"

        if not title:
            continue

        # URL
        url = None
        for u_sel in FLIPKART_SELECTORS["url"]:
            u_elem = card.select_one(u_sel)
            if u_elem and u_elem.get("href"):
                url = normalize_flipkart_url(str(u_elem["href"]))
                break

        # ID / PID
        pid = card.get("data-id")
        if not pid and url:
            m = re.search(r"pid=([A-Z0-9]+)", url)
            if m:
                pid = m.group(1)
        if not pid:
            # Deterministic fallback from url path
            pid = re.sub(r"[^\w]", "", url.split("?")[0])[-16:] if url else f"fk_{len(results)}"

        # Price
        price = None
        for p_sel in FLIPKART_SELECTORS["price"]:
            p_elem = card.select_one(p_sel)
            if p_elem:
                parsed_amt = clean_price_string(p_elem.get_text(strip=True))
                if parsed_amt is not None:
                    price = parsed_amt
                    break

        # Original price
        orig_price = None
        for op_sel in FLIPKART_SELECTORS["original_price"]:
            op_elem = card.select_one(op_sel)
            if op_elem:
                parsed_orig = clean_price_string(op_elem.get_text(strip=True))
                if parsed_orig is not None and (price is None or parsed_orig > price):
                    orig_price = parsed_orig
                    break

        # Rating
        rating = None
        for r_sel in FLIPKART_SELECTORS["rating"]:
            r_elem = card.select_one(r_sel)
            if r_elem:
                m = re.search(r"(\d+(?:\.\d+)?)", r_elem.get_text(strip=True))
                if m:
                    try:
                        parsed_r = float(m.group(1))
                        if 1.0 <= parsed_r <= 5.0:
                            rating = parsed_r
                            break
                    except ValueError:
                        pass

        # Review count
        review_count = None
        for rc_sel in FLIPKART_SELECTORS["review_count"]:
            rc_elem = card.select_one(rc_sel)
            if rc_elem:
                clean_rc = rc_elem.get_text(strip=True).replace("(", "").replace(")", "")
                m = re.search(r"([\d,]+)", clean_rc)
                if m:
                    try:
                        review_count = int(m.group(1).replace(",", ""))
                        break
                    except ValueError:
                        pass

        # Image
        image_url = None
        for img_sel in FLIPKART_SELECTORS["image"]:
            img_elem = card.select_one(img_sel)
            if img_elem:
                src = img_elem.get("src") or img_elem.get("data-src") or img_elem.get("data-url")
                if not src and img_elem.get("srcset"):
                    src = img_elem["srcset"].split(",")[0].split()[0]
                if src and str(src).strip().startswith("http"):
                    image_url = str(src).strip()
                    break

        # Availability
        avail = "in_stock"
        for av_sel in FLIPKART_SELECTORS["availability"]:
            if card.select_one(av_sel):
                avail = "out_of_stock"
                break

        results.append({
            "pid": str(pid),
            "title": title,
            "url": url,
            "price": price,
            "original_price": orig_price,
            "rating": rating,
            "review_count": review_count,
            "image_url": image_url,
            "availability": avail,
        })

    return results
