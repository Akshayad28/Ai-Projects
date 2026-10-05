"""Text Normalization and Entity Extraction Utilities."""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Tuple

_KNOWN_BRANDS = [
    "apple", "samsung", "sony", "bose", "sennheiser", "jbl", "asus", "dell", "hp",
    "lenovo", "acer", "lg", "oneplus", "google", "xiaomi", "philips", "boat",
    "noise", "realme", "motorola", "oppo", "vivo", "nike", "adidas", "puma",
]


def normalize_text(text: Optional[str]) -> str:
    """Lowercases, strips diacritics, normalizes whitespace and punctuation."""
    if not text:
        return ""

    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric punctuation with spaces (except hyphens and plus)
    text = re.sub(r"[^\w\s\-\+]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_brand_from_title(title: str, candidate_brand: Optional[str] = None) -> Optional[str]:
    """Identifies the canonical brand from title or retailer metadata."""
    if candidate_brand and candidate_brand.strip():
        b = candidate_brand.strip()
        if len(b) > 1 and b.lower() != "visit the store":
            return b.title()

    title_lower = title.lower()
    for b in _KNOWN_BRANDS:
        # Match whole word
        if re.search(rf"\b{re.escape(b)}\b", title_lower):
            return b.capitalize() if b != "jbl" and b != "hp" and b != "lg" else b.upper()

    # Fallback to first word if capitalized in original title
    words = title.split()
    if words and words[0].isalpha() and len(words[0]) > 2:
        return words[0].title()

    return None


def extract_variant_attributes(title: str) -> Dict[str, str]:
    """Extracts critical variant attributes (RAM, Storage, Color) to prevent incompatible product merging."""
    variants: Dict[str, str] = {}
    title_lower = title.lower()

    # Storage: e.g. 128GB, 256GB, 512GB, 1TB, 2TB
    m_storage = re.search(r"\b(\d+)\s*(gb|tb)\s*(?:ssd|storage|rom)?\b", title_lower)
    if m_storage:
        qty, unit = m_storage.group(1), m_storage.group(2).upper()
        variants["storage"] = f"{qty}{unit}"

    # RAM: e.g. 8GB RAM, 16GB RAM, 32GB RAM
    m_ram = re.search(r"\b(\d+)\s*(?:gb|mb)\s*ram\b", title_lower)
    if m_ram:
        variants["ram"] = f"{m_ram.group(1)}GB"

    # Color
    colors = ["black", "white", "silver", "space gray", "midnight", "starlight", "titanium", "blue", "red", "gold"]
    for c in colors:
        if re.search(rf"\b{re.escape(c)}\b", title_lower):
            variants["color"] = c.title()
            break

    return variants
