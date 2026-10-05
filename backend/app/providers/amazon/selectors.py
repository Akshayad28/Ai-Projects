"""Amazon India Selectors.

Isolated CSS and XPath selector definitions with fallback sequences.
Updated centrally if Amazon markup evolves.
"""
from __future__ import annotations

AMAZON_SELECTORS = {
    "product_cards": [
        "div[data-component-type='s-search-result']",
        "div.s-result-item[data-asin]:not([data-asin=''])",
        ".s-card-container",
    ],
    "title": [
        "h2",
        "h2 span",
        "a.a-link-normal:has(h2)",
        "h2 a span",
        "h2.a-size-mini span",
        "h2.a-size-base-plus",
        "h2.a-size-medium",
        "span.a-size-medium.a-color-base.a-text-normal",
        "span.a-size-base-plus",
    ],
    "url": [
        "a.a-link-normal:has(h2)",
        "h2 a.a-link-normal",
        "a.a-link-normal[href*='/dp/']",
        "a.a-link-normal.s-no-outline",
        "a.a-link-normal.s-underline-text",
    ],
    "price_whole": [
        "span.a-price-whole",
        ".a-price .a-offscreen",
    ],
    "price_fraction": [
        "span.a-price-fraction",
    ],
    "original_price": [
        "span.a-price.a-text-price span.a-offscreen",
        "span.a-text-strike",
    ],
    "rating": [
        "span[aria-label*='out of 5 stars']",
        "span[aria-label*='stars']",
        "i[class*='star'] span.a-icon-alt",
        "i.a-icon-star-small span.a-icon-alt",
        "i.a-icon-star span.a-icon-alt",
        "i.a-icon-star-mini span.a-icon-alt",
    ],
    "review_count": [
        "span[aria-label*='ratings']",
        "a[href*='#customerReviews'] span",
        "span.a-size-base.s-underline-text",
    ],
    "image": [
        "img.s-image",
        "img[data-image-latency='s-product-image']",
    ],
    "availability": [
        "span.a-color-price",  # e.g. "Only 2 left in stock"
        "span.a-size-base.a-color-success",
    ],
    "sponsored_badge": [
        "span.puis-sponsored-label-text",
        ".s-sponsored-label-info-icon",
    ],
}
