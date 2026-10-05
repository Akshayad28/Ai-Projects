"""Intent Service.

Interprets the user's natural language shopping query into structured constraints.
THE INTENT SERVICE ONLY INTERPRETS THE USER'S REQUEST.
IT NEVER INVENT OR PROVIDES PRODUCT FACTS.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.cache import get_cache
from app.nlp.intent import parse_intent
from app.schemas.search import ExtractedQueryIntent
from app.utils.hashing import hash_query


class IntentService:
    """Extracts shopping intent, constraints, and features from user queries."""

    async def extract_intent(
        self,
        query: str,
        country: str = "IN",
        currency: str = "INR",
    ) -> ExtractedQueryIntent:
        cache = get_cache()
        cache_key = f"extracted_intent:{hash_query(query, country, currency)}"
        try:
            cached_data = await cache.get(cache_key)
            if cached_data and isinstance(cached_data, dict):
                return ExtractedQueryIntent.model_validate(cached_data)
        except Exception:
            pass

        # Utilize the multi-engine parser (LLM with rule-based fallback)
        intent = await parse_intent(query, country=country, currency=currency)

        # Extract specific required / preferred features
        q_lower = query.lower()
        req_features: Dict[str, Any] = {}
        pref_features: Dict[str, Any] = {}

        if any(w in q_lower for w in ["anc", "noise cancelling", "noise cancellation"]):
            req_features["noise_cancellation"] = True
        if any(w in q_lower for w in ["wireless", "bluetooth"]):
            req_features["wireless"] = True
        if "lightweight" in q_lower:
            pref_features["lightweight"] = True
        if "battery" in q_lower:
            pref_features["long_battery_life"] = True

        # Extract brand if single preferred
        primary_brand = intent.preferred_brands[0] if intent.preferred_brands else None

        keywords = intent.keywords if intent.keywords else ([intent.provider_query] if intent.provider_query else [query])

        # Add requirements from parsed intent to required_features
        for req_item in getattr(intent, "requirements", []):
            req_features[req_item.lower().replace(" ", "_")] = True

        extracted = ExtractedQueryIntent(
            original=query,
            product_type=getattr(intent, "product_type", None) or intent.category,
            category=intent.category,
            keywords=keywords,
            min_price=intent.budget.min,
            max_price=intent.budget.max,
            currency=intent.budget.currency or currency,
            required_features=req_features,
            preferred_features=pref_features,
            brand=primary_brand,
            model=getattr(intent, "model", None),
            size=getattr(intent, "size", None),
            color=getattr(intent, "color", None),
            quantity=getattr(intent, "quantity", None),
            use_cases=intent.use_cases if intent.use_cases else [],
            condition=intent.condition or "new",
            clean_provider_query=intent.provider_query or query,
        )

        try:
            await cache.set(cache_key, extracted.model_dump(), ttl=3600)
        except Exception:
            pass

        return extracted
