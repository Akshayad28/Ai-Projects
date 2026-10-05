"""Internal data models for Google Shopping scraper.

Represents strictly observed fields extracted from Google's rendered DOM.
Converts seamlessly to project's canonical RawProduct and ProviderProduct models.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.providers.base.models import ProviderPrice, ProviderProduct
from app.schemas.domain import RawOffer, RawProduct, now_utc


class GoogleLayout(str, Enum):
    """Google Shopping result layout classification."""
    SHOPPING_GRID = "shopping_grid"
    SHOPPING_CAROUSEL = "shopping_carousel"
    SHOPPING_LIST = "shopping_list"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ExtractionHealth(BaseModel):
    """Extraction-health telemetry for every Google Shopping scrape."""

    layout: GoogleLayout = GoogleLayout.UNKNOWN
    cards_found: int = 0
    products_detected: int = 0
    products_parsed: int = 0
    products_with_title: int = 0
    products_with_price: int = 0
    products_with_image: int = 0
    products_with_url: int = 0
    products_with_merchant: int = 0
    products_with_rating: int = 0
    products_with_review_count: int = 0
    blocked: bool = False
    block_reason: Optional[str] = None
    extraction_errors: List[str] = Field(default_factory=list)

    @property
    def price_success_rate(self) -> float:
        return round(self.products_with_price / self.products_parsed, 2) if self.products_parsed > 0 else 0.0

    @property
    def image_success_rate(self) -> float:
        return round(self.products_with_image / self.products_parsed, 2) if self.products_parsed > 0 else 0.0

    @property
    def merchant_success_rate(self) -> float:
        return round(self.products_with_merchant / self.products_parsed, 2) if self.products_parsed > 0 else 0.0

    @property
    def url_success_rate(self) -> float:
        return round(self.products_with_url / self.products_parsed, 2) if self.products_parsed > 0 else 0.0

    def is_degraded(self, threshold: float = 0.2) -> bool:
        """Detects if many cards were found but parsing rate was abnormally low."""
        if self.cards_found >= 5 and (self.products_parsed / self.cards_found) < threshold:
            return True
        return False

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "layout": self.layout.value if isinstance(self.layout, GoogleLayout) else str(self.layout),
            "cards_found": self.cards_found,
            "products_parsed": self.products_parsed,
            "price_success_rate": self.price_success_rate,
            "image_success_rate": self.image_success_rate,
            "merchant_success_rate": self.merchant_success_rate,
            "url_success_rate": self.url_success_rate,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "degraded": self.is_degraded(),
        }


class GoogleScrapedItem(BaseModel):
    """Raw product observation extracted from a Google Shopping result card."""

    title: str
    price_amount: Optional[float] = None
    currency: str = "INR"
    original_price: Optional[float] = None
    retailer_name: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    availability: Optional[str] = None
    shipping_text: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    country: str = "IN"
    layout: Optional[str] = None

    @property
    def external_id(self) -> str:
        """Deterministic ID based on product URL or title + retailer."""
        key = self.url or f"{self.retailer_name}:{self.title}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def to_raw_product(self) -> RawProduct:
        """Converts to the pipeline's RawProduct domain model."""
        offer = RawOffer(
            provider="google_scraper",
            retailer_name=self.retailer_name or "Retailer",
            retailer_domain=None,
            price_amount=self.price_amount,
            currency=self.currency,
            original_price=self.original_price,
            shipping_text=self.shipping_text,
            availability="in_stock" if self.availability != "out_of_stock" else "out_of_stock",
            condition="new",
            url=self.url,
            confidence=1.0,
            checked_at=now_utc(),
        )

        return RawProduct(
            provider="google_scraper",
            external_id=self.external_id,
            title=self.title,
            brand=self.brand,
            model=self.model,
            url=self.url,
            image_urls=[self.image_url] if self.image_url else [],
            rating=self.rating,
            review_count=self.review_count,
            rating_source="Google Shopping" if self.rating else None,
            specs={},
            country=self.country,
            offers=[offer],
            is_demo=False,
        )

    def to_provider_product(self) -> ProviderProduct:
        """Converts to the ShoppingProvider's ProviderProduct model."""
        discount = None
        if self.original_price and self.price_amount and self.original_price > self.price_amount:
            discount = round(self.original_price - self.price_amount, 2)

        return ProviderProduct(
            provider="google_scraper",
            provider_product_id=self.external_id,
            title=self.title,
            url=self.url,
            image_url=self.image_url,
            image_urls=[self.image_url] if self.image_url else [],
            brand=self.brand,
            model=self.model,
            price=ProviderPrice(
                amount=self.price_amount,
                currency=self.currency,
                original_price=self.original_price,
                discount=discount,
            ),
            rating=self.rating,
            review_count=self.review_count,
            availability=self.availability or "IN_STOCK",
            seller=self.retailer_name,
            identifiers={},
            raw_metadata={
                "shipping": self.shipping_text,
                "country": self.country,
                "layout": self.layout,
            },
        )
