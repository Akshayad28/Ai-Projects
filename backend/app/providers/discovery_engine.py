"""Marketplace Discovery Engine.

Dynamically maps user shopping intent to relevant retail marketplaces,
specialist stores, quick-commerce platforms, and web discovery engines.
Ensures multi-provider parallel execution without privileging or defaulting
to any single retailer (e.g., Amazon is never privileged as the sole provider).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from app.core.logging import get_logger
from app.providers.capabilities import MarketplaceType, ProviderCapabilities, ProviderMetadata
from app.schemas.domain import SearchIntent

log = get_logger(__name__)

# Keywords triggering specific marketplace capabilities
QUICK_COMMERCE_KEYWORDS: Set[str] = {
    "milk", "coke", "coca-cola", "pepsi", "chips", "bread", "butter", "eggs",
    "curd", "yogurt", "ice cream", "snacks", "groceries", "grocery", "toothpaste",
    "soap", "shampoo", "biscuit", "biscuits", "tea", "coffee", "vegetables",
    "fruits", "instant", "10 min", "15 min", "quick delivery", "same day delivery",
    "cold drink", "soda", "water", "juice", "chocolates", "chocolate", "chips",
    "maggi", "noodles", "atta", "rice", "dal", "oil", "sugar", "salt", "spices"
}

ELECTRONICS_KEYWORDS: Set[str] = {
    "laptop", "laptops", "phone", "phones", "smartphone", "iphone", "samsung",
    "macbook", "monitor", "monitors", "tv", "television", "gpu", "rtx", "ram",
    "processor", "headphones", "earbuds", "tablet", "ipad", "camera", "console",
    "ps5", "xbox", "audio", "speaker", "charger", "cable", "smartwatch", "desktop"
}

FASHION_KEYWORDS: Set[str] = {
    "shoes", "sneakers", "running shoes", "formal shoes", "shirt", "t-shirt",
    "jeans", "trousers", "jacket", "hoodie", "dress", "saree", "kurta", "watch",
    "clothing", "apparel", "boots", "sandals", "handbag", "wallet"
}

FURNITURE_KEYWORDS: Set[str] = {
    "chair", "office chair", "gaming chair", "table", "study table", "desk",
    "sofa", "bed", "mattress", "wardrobe", "bookshelf", "cabinet", "dining table",
    "furniture"
}


class MarketplaceDiscoveryEngine:
    """Discovers and routes queries to relevant marketplaces and providers."""

    def __init__(self) -> None:
        self._provider_metadata: Dict[str, ProviderMetadata] = {}

    def register_metadata(self, name: str, meta: ProviderMetadata) -> None:
        self._provider_metadata[name] = meta

    def get_metadata(self, name: str) -> Optional[ProviderMetadata]:
        return self._provider_metadata.get(name)

    def classify_intent_types(self, intent: SearchIntent) -> Set[MarketplaceType]:
        """Classifies the user query into one or more relevant marketplace types."""
        types: Set[MarketplaceType] = {
            MarketplaceType.GENERAL_MARKETPLACE,
            MarketplaceType.WEB_DISCOVERY,
        }

        text = f"{intent.raw_query} {intent.category or ''} {' '.join(intent.keywords)}".lower()

        # Quick Commerce / Grocery detection
        if intent.quick_commerce_priority or any(kw in text for kw in QUICK_COMMERCE_KEYWORDS):
            types.add(MarketplaceType.QUICK_COMMERCE)
            types.add(MarketplaceType.GROCERY)

        # Electronics detection
        if any(kw in text for kw in ELECTRONICS_KEYWORDS):
            types.add(MarketplaceType.ELECTRONICS)

        # Fashion detection
        if any(kw in text for kw in FASHION_KEYWORDS):
            types.add(MarketplaceType.FASHION)

        # Home & Furniture detection
        if any(kw in text for kw in FURNITURE_KEYWORDS):
            types.add(MarketplaceType.HOME_FURNITURE)

        return types

    def select_relevant_providers(
        self,
        available_providers: Dict[str, Any],
        intent: SearchIntent,
        country: str = "IN",
    ) -> List[str]:
        """Selects provider keys that match query intent and geographic support.

        Guarantees:
        - NEVER privileges Amazon as a sole provider.
        - Multiple complementary providers always selected for parallel execution.
        """
        relevant_types = self.classify_intent_types(intent)
        selected: List[str] = []

        for name, prov in available_providers.items():
            meta = self._provider_metadata.get(name)

            # If no metadata registered, default to general inclusion
            if not meta:
                selected.append(name)
                continue

            if not meta.enabled:
                continue

            # Country check
            if meta.countries and country.upper() not in meta.countries and "ALL" not in meta.countries:
                continue

            # Check type alignment
            if meta.marketplace_type in relevant_types:
                selected.append(name)
            elif meta.marketplace_type in (MarketplaceType.GENERAL_MARKETPLACE, MarketplaceType.WEB_DISCOVERY, MarketplaceType.MERCHANT_FEED):
                selected.append(name)

        # Safety Fallback: ensure at least web discovery and general marketplaces are present
        if not selected:
            selected = list(available_providers.keys())

        log.info(
            f"Marketplace Discovery: query='{intent.raw_query}', "
            f"types={[t.value for t in relevant_types]}, selected_providers={selected}"
        )
        return selected

    def discover_relevant_providers(self, intent: SearchIntent, country: str = "IN") -> List[str]:
        """Convenience method discovering relevant providers using known metadata or defaults."""
        if not self._provider_metadata:
            default_map = {
                "google_scraper": MarketplaceType.WEB_DISCOVERY,
                "firecrawl": MarketplaceType.WEB_DISCOVERY,
                "amazon": MarketplaceType.GENERAL_MARKETPLACE,
                "flipkart": MarketplaceType.GENERAL_MARKETPLACE,
                "ebay": MarketplaceType.GENERAL_MARKETPLACE,
                "blinkit": MarketplaceType.QUICK_COMMERCE,
                "zepto": MarketplaceType.QUICK_COMMERCE,
                "instamart": MarketplaceType.QUICK_COMMERCE,
                "bigbasket": MarketplaceType.QUICK_COMMERCE,
                "croma": MarketplaceType.ELECTRONICS,
                "reliance_digital": MarketplaceType.ELECTRONICS,
                "myntra": MarketplaceType.FASHION,
                "ikea": MarketplaceType.HOME_FURNITURE,
            }
            for name, mtype in default_map.items():
                self.register_metadata(name, ProviderMetadata(name=name, label=name.replace("_", " ").title(), marketplace_type=mtype))

        dummy_providers = {name: None for name in self._provider_metadata.keys()}
        return self.select_relevant_providers(dummy_providers, intent, country)

