"""Google Shopping / Search DOM Selectors.

Isolates all CSS selectors and patterns for Google Shopping result layouts.
Organized by field with multi-layer fallback support for Grid, Carousel, and List formats.
"""
from __future__ import annotations

from typing import Dict, List

# ── 1. Card Container Selectors ──────────────────────────────────────
GRID_CARD_SELECTORS: List[str] = [
    "div.sh-dgr__grid-result",
    "div.sh-dgr__content",
    "div[data-docid]",
    "div.xcR77",
    "div.LqBPfc",
    "div.sh-np__click-target",
]

CAROUSEL_CARD_SELECTORS: List[str] = [
    "div.pla-unit",
    "div.pla-unit-container",
    "div.mnr-c",
    "div.KZmu8e",
    "div.u30jdd",
    "g-scrolling-carousel div.mnr-c",
    "div[data-pla-slot]",
]

LIST_CARD_SELECTORS: List[str] = [
    "div.sh-dlr__list-result",
    "div.sh-pr__product-results > div",
    "div.sh-sr__shop-result-group > div",
    "div.sr__card",
]

# All Card Selectors (Grid > Carousel > List > Generic)
CARD_SELECTORS: List[str] = (
    GRID_CARD_SELECTORS + CAROUSEL_CARD_SELECTORS + LIST_CARD_SELECTORS + [
        "div[data-item-id]",
        "div.product-card",
        "article[data-docid]",
    ]
)

# ── 2. Title Selectors ───────────────────────────────────────────────
TITLE_SELECTORS: List[str] = [
    # Layer 1: Primary classes
    ".tAxDx",
    "h3.tAxDx",
    "div.tAxDx",
    "h3.sh-np__product-title",
    "h3.sh-dlr__thumbnail-title",
    "a.pla-unit-title-link",
    "div.mUQCLc",
    "div.EI11Pd",
    "div.Xjkr3b",
    # Layer 2: Secondary / Fallback classes
    "a.sh-o__action",
    "div.rgRx7c",
    "span[role='heading']",
    "div[role='heading']",
    "h3",
    "h4",
    "a[aria-label]",
]

# ── 3. Price Selectors ───────────────────────────────────────────────
PRICE_SELECTORS: List[str] = [
    # Layer 1: Primary price elements
    "span.a8Pemb",
    "span.e10twf",
    "div.T149du",
    "span.kHxwFf",
    "div.kHxwFf",
    # Layer 2: Fallback price elements
    "span[data-price]",
    "span.OFFNJ",
    "span.HRLxBb",
    "span.dD8Ag",
    "div.qTkE6",
    "div.g9WBQb",
    "span[aria-label*='price']",
    "span.price",
    "div.price",
    "[itemprop='price']",
]

# ── 4. Original / Strikethrough Price Selectors ──────────────────────
ORIGINAL_PRICE_SELECTORS: List[str] = [
    "span.qXLe6d s",
    "span.W4P4ne s",
    "span.st",
    "span.s8tx4e",
    "span.line-through",
    "s",
    "del",
    "span[aria-label*='original price']",
]

# ── 5. Merchant / Retailer Selectors ─────────────────────────────────
MERCHANT_SELECTORS: List[str] = [
    # Layer 1: Primary retailer classes
    "div.aULzUe",
    "span.E5ocAb",
    "span.LbUacb",
    "div.IuHnof",
    # Layer 2: Secondary / Fallback classes
    "div.dD8Ag",
    "div.b5yKc",
    "div.hBUZL",
    "span.h1U9Ae",
    "div.z1asCe",
    "span[aria-label*='seller']",
    "span[aria-label*='merchant']",
    "div.merchant-name",
    "[itemprop='seller']",
]

# ── 6. Redirect / Destination URL Selectors ──────────────────────────
URL_SELECTORS: List[str] = [
    "a.shntl",
    "a.LqBPfc",
    "a.pla-unit-title-link",
    "a.plantl",
    "a.CQReSt",
    "a[href*='/url?']",
    "a[href*='/shopping/product/']",
    "a[data-what='1']",
    "a",
]

# ── 7. Image Selectors ───────────────────────────────────────────────
IMAGE_SELECTORS: List[str] = [
    "div.ArOc1c img",
    "div.oR27Gd img",
    "div.pla-unit-img-container img",
    "img.m5zEkf",
    "img[data-src]",
    "img[data-original]",
    "img[data-image-src]",
    "img[data-deferred-src]",
    "img[srcset]",
    "img[src]",
]

# ── 8. Rating Selectors ──────────────────────────────────────────────
RATING_SELECTORS: List[str] = [
    ".Rsc7Yb",
    "span.Rsc7Yb",
    "div.Rsc7Yb",
    "div.mB199c",
    "span.Fam1ne",
    "span[aria-label*='stars']",
    "span[aria-label*='out of 5']",
    "span[aria-label*='star rating']",
    "div.d15J0c",
    "[itemprop='ratingValue']",
]

# ── 9. Review Count Selectors ────────────────────────────────────────
REVIEW_COUNT_SELECTORS: List[str] = [
    ".fl",
    "span.fl",
    "div.fl",
    "span.Rsc7Yb + span",
    "div.Rsc7Yb + div",
    "span[aria-label*='reviews']",
    "span.mB199c",
    "[itemprop='reviewCount']",
]

# ── 10. Availability Selectors ───────────────────────────────────────
AVAILABILITY_SELECTORS: List[str] = [
    "span.W4P4ne",
    "span.dD8Ag",
    "div.vEjMR",
    "span[aria-label*='stock']",
    "[itemprop='availability']",
]

# ── 11. Shipping Selectors ───────────────────────────────────────────
SHIPPING_SELECTORS: List[str] = [
    "div.vEjMR",
    "span.dD8Ag",
    "div.qTkE6",
    "span.W4P4ne",
    "div.hBUZL",
    "span[aria-label*='delivery']",
    "span[aria-label*='shipping']",
]

# ── 12. Specification Selectors ──────────────────────────────────────
SPECIFICATION_SELECTORS: List[str] = [
    "div.dD8Ag",
    "div.vEjMR",
    "ul.sh-dgr__spec-list li",
    "div.sh-ds__specs",
]

# ── Backwards-Compatible Dictionary ──────────────────────────────────
GOOGLE_SELECTORS: Dict[str, List[str]] = {
    "product_cards": CARD_SELECTORS,
    "title": TITLE_SELECTORS,
    "price": PRICE_SELECTORS,
    "original_price": ORIGINAL_PRICE_SELECTORS,
    "retailer": MERCHANT_SELECTORS,
    "rating": RATING_SELECTORS,
    "reviews": REVIEW_COUNT_SELECTORS,
    "link": URL_SELECTORS,
    "image": IMAGE_SELECTORS,
    "shipping": SHIPPING_SELECTORS,
}
