"""Provider Capabilities and Metadata Definitions."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field


class MarketplaceType(str, Enum):
    GENERAL_MARKETPLACE = "general_marketplace"
    ELECTRONICS = "electronics"
    FASHION = "fashion"
    GROCERY = "grocery"
    QUICK_COMMERCE = "quick_commerce"
    HOME_FURNITURE = "home_furniture"
    BEAUTY = "beauty"
    SPORTS = "sports"
    HARDWARE_DIY = "hardware_diy"
    WEB_DISCOVERY = "web_discovery"
    MERCHANT_FEED = "merchant_feed"


class ProviderCapabilities(BaseModel):
    product_search: bool = True
    product_detail: bool = True
    offers: bool = True
    reviews: bool = False
    availability: bool = True
    delivery: bool = True
    images: bool = True
    price_history: bool = False
    quick_commerce: bool = False
    unit_economics: bool = False
    location_aware: bool = False
    marketplace_type: Optional[MarketplaceType] = None


class ProviderMetadata(BaseModel):
    name: str
    label: str
    marketplace_type: MarketplaceType = MarketplaceType.GENERAL_MARKETPLACE
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    countries: Set[str] = Field(default_factory=set)
    currencies: Set[str] = Field(default_factory=lambda: {"INR", "USD"})
    categories: Set[str] = Field(default_factory=set)
    rate_limit_per_second: float = 2.0
    timeout_seconds: int = 30
    priority: int = 100
    enabled: bool = True
    required_env: List[str] = Field(default_factory=list)
    is_demo: bool = False
