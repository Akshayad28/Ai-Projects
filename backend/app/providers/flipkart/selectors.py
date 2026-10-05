"""Flipkart India Selectors.

Isolated CSS selectors with fallback chains for product cards and details.
"""
from __future__ import annotations

FLIPKART_SELECTORS = {
    "product_cards": [
        "div[data-id]",
        "div._1AtVbE div._13oc-S",
        "div._75nlfW",
        "._4ddWXP",
        "._1xHGKq",
    ],
    "title": [
        "div.KzDlHZ",
        "div._4rR01T",
        "a.wjcEIp",
        "a.WKTcLC",
        "a.s1Q9rs",
        "a[title]",
        "a.pIpigb",
        "a.IRpwTa",
        "div._2WkVRV",
        "img.UCc1lI[alt]",
    ],
    "url": [
        "a.GnxRXv",
        "a.pIpigb",
        "a[href*='/p/']",
        "a.CGtC5Q",
        "a._1fQZEK",
        "a.s1Q9rs",
        "a.IRpwTa",
    ],
    "price": [
        "div.hZ3P6w",
        "div.Nx9bqj",
        "div._30jeq3",
        "div._30jeq3._1_WHN1",
    ],
    "original_price": [
        "div.kRYCnD",
        "div.yRaY8j",
        "div._3I9_wc",
        "div._3I9_wc._27UcVY",
    ],
    "rating": [
        "div.MKiFS6",
        "div.XQDdHH",
        "div._3LWZlK",
        "span[id^='productRating']",
    ],
    "review_count": [
        "span.PvbNMB",
        "span.Wphh3L",
        "span._2_R_DZ span",
    ],
    "image": [
        "img.UCc1lI",
        "img.DByuf4",
        "img._396cs4",
        "img._2r_T1I",
        "img[src*='flixcart.com']",
    ],
    "availability": [
        "div._16FRp0",  # "Out of stock"
    ],
}
