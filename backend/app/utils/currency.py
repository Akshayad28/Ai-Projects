"""Currency and price parsing utilities."""
from __future__ import annotations

import re
from typing import Optional


def clean_price_string(price_str: Optional[str]) -> Optional[float]:
    """Extracts a numeric float price from arbitrary retailer strings (e.g. '₹34,999.00', 'Rs. 1,499')."""
    if not price_str:
        return None

    cleaned = price_str.strip().replace(",", "")
    # Match numbers with optional decimal
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None

    try:
        val = float(match.group(1))
        return val if val > 0 else None
    except ValueError:
        return None
