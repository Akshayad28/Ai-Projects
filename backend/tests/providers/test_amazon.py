"""Unit tests for Amazon parser and normalizer."""
from __future__ import annotations

from pathlib import Path
from app.providers.amazon.parser import parse_amazon_search_page
from app.providers.amazon.normalizer import normalize_amazon_product

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "amazon_search_fixture.html"


def test_parse_amazon_search_fixture():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    items = parse_amazon_search_page(html)

    assert len(items) == 3

    # Item 1: Sony WH-1000XM5
    sony = items[0]
    assert sony["asin"] == "B09XS7JWHH"
    assert "Sony WH-1000XM5" in sony["title"]
    assert sony["price"] == 29990.0
    assert sony["original_price"] == 34990.0
    assert sony["rating"] == 4.5
    assert sony["review_count"] == 1240
    assert "https://m.media-amazon.com" in sony["image_url"]
    assert sony["availability"] == "in_stock"

    # Normalize
    prod = normalize_amazon_product(sony)
    assert prod.brand == "Sony"
    assert prod.price.amount == 29990.0
    assert prod.price.discount == 5000.0
    assert prod.identifiers["asin"] == "B09XS7JWHH"

    # Item 3: Out of stock item
    bose = items[2]
    assert bose["asin"] == "B07G4MNFS1"
    assert bose["availability"] == "out_of_stock"
    assert bose["price"] is None
