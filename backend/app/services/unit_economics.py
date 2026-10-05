"""Unit Economics and Price Intelligence Service.

Calculates normalized unit prices (e.g., price per kg, price per litre,
price per 100g/100ml, price per item) for groceries, consumables, and quick commerce.
Enables true value comparisons across different package sizes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

log = get_logger(__name__)

# Patterns for extracting package sizes and quantities
VOLUME_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(l|litre|litres|liter|liters|ml|millilitres?|milliliters?)\b",
    re.IGNORECASE,
)
WEIGHT_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|g|gm|gms|grams?)\b",
    re.IGNORECASE,
)
COUNT_REGEX = re.compile(
    r"\b(?:pack\s*of|pack\s*-\s*|set\s*of|combo\s*of)\s*(\d{1,3})\b|\b(\d{1,3})\s*(?:pack|packs|pk|pcs|pieces|cans?|bottles?|units?)\b",
    re.IGNORECASE,
)


@dataclass
class UnitEconomics:
    pack_size: str
    unit_price: float
    unit_measure: str  # "kg", "litre", "100g", "100ml", "item"
    formatted_unit_price: str
    base_quantity: float
    item_count: int = 1


class UnitEconomicsService:
    """Calculates standardized unit economics for physical products and offers."""

    def calculate_unit_price(
        self,
        price: Optional[float],
        title: str,
        specs: Optional[Dict[str, Any]] = None,
        currency: str = "INR",
    ) -> Optional[Tuple[float, str, str]]:
        """Convenience method returning (unit_price, unit_measure, formatted_str)."""
        econ = self.extract_and_calculate(price, title, specs, currency)
        if not econ:
            return None
        return econ.unit_price, econ.unit_measure, econ.formatted_unit_price

    @staticmethod
    def extract_and_calculate(
        price: Optional[float],
        title: str,
        specs: Optional[Dict[str, Any]] = None,
        currency: str = "INR",
    ) -> Optional[UnitEconomics]:
        if not price or price <= 0:
            return None

        combined_text = title
        if specs:
            combined_text += " " + " ".join(f"{k} {v}" for k, v in specs.items())
        text_lower = combined_text.lower()

        # 1. Check Volume (Liquid)
        vol_match = VOLUME_REGEX.search(text_lower)
        if vol_match:
            val = float(vol_match.group(1))
            unit = vol_match.group(2).lower()
            if unit in ("l", "litre", "litres", "liter", "liters"):
                ml = val * 1000.0
                pack_str = f"{val:g}L"
            else:
                ml = val
                pack_str = f"{int(val)}ml"

            if ml > 0:
                litres = ml / 1000.0
                price_per_litre = round(price / litres, 2)
                symbol = "₹" if currency.upper() in ("INR", "₹") else f"{currency} "
                return UnitEconomics(
                    pack_size=pack_str,
                    unit_price=price_per_litre,
                    unit_measure="litre",
                    formatted_unit_price=f"{symbol}{price_per_litre:,.2f} / L",
                    base_quantity=litres,
                )

        # 2. Check Weight (Solid / Mass)
        wt_match = WEIGHT_REGEX.search(text_lower)
        if wt_match:
            num_str = wt_match.group(1)
            unit_str = wt_match.group(2).lower()
            # Guard against storage "gb" false positives
            if not re.search(rf"\b{num_str}\s*gb\b", text_lower):
                val = float(num_str)
                if unit_str in ("kg", "kgs", "kilograms"):
                    grams = val * 1000.0
                    pack_str = f"{val:g}kg"
                else:
                    grams = val
                    pack_str = f"{int(val)}g"

                if grams > 0:
                    kgs = grams / 1000.0
                    price_per_kg = round(price / kgs, 2)
                    symbol = "₹" if currency.upper() in ("INR", "₹") else f"{currency} "
                    return UnitEconomics(
                        pack_size=pack_str,
                        unit_price=price_per_kg,
                        unit_measure="kg",
                        formatted_unit_price=f"{symbol}{price_per_kg:,.2f} / kg",
                        base_quantity=kgs,
                    )

        # 3. Check Pack Count (Multipack items)
        count_match = COUNT_REGEX.search(text_lower)
        if count_match:
            c_str = count_match.group(1) or count_match.group(2)
            try:
                count = int(c_str)
                if count > 1:
                    price_per_item = round(price / count, 2)
                    symbol = "₹" if currency.upper() in ("INR", "₹") else f"{currency} "
                    return UnitEconomics(
                        pack_size=f"Pack of {count}",
                        unit_price=price_per_item,
                        unit_measure="item",
                        formatted_unit_price=f"{symbol}{price_per_item:,.2f} / item",
                        base_quantity=float(count),
                        item_count=count,
                    )
            except ValueError:
                pass

        return None
