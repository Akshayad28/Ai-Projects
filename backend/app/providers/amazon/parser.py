"""Amazon Search Results Parser.

Extracts only strictly observed data from Amazon HTML cards.
Falls back through selector lists without inventing missing fields.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.providers.amazon.selectors import AMAZON_SELECTORS
from app.utils.currency import clean_price_string
from app.utils.url_utils import normalize_amazon_url

log = get_logger(__name__)


def parse_amazon_search_page(html_content: str, max_items: int = 20) -> List[Dict[str, Any]]:
    """Parses Amazon search results HTML into raw dictionaries."""
    soup = BeautifulSoup(html_content, "lxml")
    cards: List[Tag] = []

    # 1. Find all product cards using selector fallbacks
    for card_sel in AMAZON_SELECTORS["product_cards"]:
        found = soup.select(card_sel)
        if found:
            cards = found
            break

    results: List[Dict[str, Any]] = []

    for card in cards:
        if len(results) >= max_items:
            break

        # Check if sponsored / ad
        is_sponsored = False
        for sp_sel in AMAZON_SELECTORS["sponsored_badge"]:
            if card.select_one(sp_sel):
                is_sponsored = True
                break

        # ASIN
        asin = card.get("data-asin")
        if not asin or str(asin).strip() == "":
            continue
        asin = str(asin).strip()

        # Title
        title = None
        for t_sel in AMAZON_SELECTORS["title"]:
            t_elem = card.select_one(t_sel)
            if t_elem:
                raw_text = t_elem.get_text(strip=True)
                if raw_text and len(raw_text) > 3:
                    title = raw_text
                    break

        if not title:
            continue

        # URL
        url = None
        for u_sel in AMAZON_SELECTORS["url"]:
            u_elem = card.select_one(u_sel)
            if u_elem and u_elem.get("href"):
                url = normalize_amazon_url(str(u_elem["href"]))
                break

        # Price
        price = None
        for p_sel in AMAZON_SELECTORS["price_whole"]:
            p_elem = card.select_one(p_sel)
            if p_elem:
                parsed_amt = clean_price_string(p_elem.get_text(strip=True))
                if parsed_amt is not None:
                    price = parsed_amt
                    break

        # Original price
        orig_price = None
        for op_sel in AMAZON_SELECTORS["original_price"]:
            op_elem = card.select_one(op_sel)
            if op_elem:
                parsed_orig = clean_price_string(op_elem.get_text(strip=True))
                if parsed_orig is not None and (price is None or parsed_orig > price):
                    orig_price = parsed_orig
                    break

        # Rating
        rating = None
        for r_sel in AMAZON_SELECTORS["rating"]:
            r_elem = card.select_one(r_sel)
            if r_elem:
                r_text = r_elem.get("aria-label") or r_elem.get_text(strip=True)
                m = re.search(r"([\d\.]+)\s*(?:out of 5|stars)?", r_text, re.IGNORECASE)
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
        for rc_sel in AMAZON_SELECTORS["review_count"]:
            rc_elem = card.select_one(rc_sel)
            if rc_elem:
                rc_text = rc_elem.get("aria-label") or rc_elem.get_text(strip=True)
                m = re.search(r"([\d,]+)", rc_text.replace("(", "").replace(")", ""))
                if m:
                    try:
                        review_count = int(m.group(1).replace(",", ""))
                        break
                    except ValueError:
                        pass

        # Image
        image_url = None
        for img_sel in AMAZON_SELECTORS["image"]:
            img_elem = card.select_one(img_sel)
            if img_elem:
                src = img_elem.get("src") or img_elem.get("data-src") or img_elem.get("data-image-source")
                if not src and img_elem.get("srcset"):
                    src = img_elem["srcset"].split(",")[0].split()[0]
                if src:
                    src_str = str(src).strip()
                    if src_str.startswith("http") and not src_str.endswith("transparent-pixel.gif"):
                        image_url = src_str
                        break

        # Availability
        avail = "in_stock"
        for av_sel in AMAZON_SELECTORS["availability"]:
            av_elem = card.select_one(av_sel)
            if av_elem:
                text = av_elem.get_text(strip=True).lower()
                if "only" in text and "stock" in text:
                    avail = "limited"
                elif "currently unavailable" in text or "out of stock" in text:
                    avail = "out_of_stock"
                break

        results.append({
            "asin": asin,
            "title": title,
            "url": url,
            "price": price,
            "original_price": orig_price,
            "rating": rating,
            "review_count": review_count,
            "image_url": image_url,
            "availability": avail,
            "is_sponsored": is_sponsored,
        })

    return results
