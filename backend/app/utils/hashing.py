"""Hashing utilities for deterministic IDs and cache keys."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_query(query: str, country: str = "IN", currency: str = "INR") -> str:
    """Produces a deterministic MD5 hash for search caching."""
    normalized = f"{query.strip().lower()}:{country.upper()}:{currency.upper()}"
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def generate_identity_key(brand: str, model_or_title: str, variant_sig: str = "") -> str:
    """Generates canonical product identity key."""
    raw = f"{brand.strip().lower()}:{model_or_title.strip().lower()}:{variant_sig.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
