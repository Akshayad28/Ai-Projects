"""Unit tests for Flipkart parser and normalizer."""
from __future__ import annotations

from pathlib import Path
from app.providers.flipkart.parser import parse_flipkart_search_page
from app.providers.flipkart.normalizer import normalize_flipkart_product

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "flipkart_search_fixture.html"


def test_parse_flipkart_search_fixture():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    items = parse_flipkart_search_page(html)

    assert len(items) == 2

    # Item 1: Sony WH-1000XM5
    sony = items[0]
    assert sony["pid"] == "ACCG6ZFFHGZHZHYG"
    assert "SONY WH-1000XM5" in sony["title"]
    assert sony["price"] == 29490.0
    assert sony["original_price"] == 34990.0
    assert sony["rating"] == 4.6
    assert sony["review_count"] == 3120

    # Normalize
    prod = normalize_flipkart_product(sony)
    assert prod.brand == "Sony"
    assert prod.price.amount == 29490.0
    assert prod.price.discount == 5500.0
    assert prod.identifiers["flipkart_pid"] == "ACCG6ZFFHGZHZHYG"
