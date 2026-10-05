"""Product Schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DynamicCardAttribute(BaseModel):
    key: str
    label: str
    value: Any
    unit: Optional[str] = None


class RecommendationBreakdown(BaseModel):
    match_score: int
    confidence: float = 0.9
    breakdown: Dict[str, int] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    drawbacks: List[str] = Field(default_factory=list)
    why_not_higher: List[str] = Field(default_factory=list)


class ProductVariantSchema(BaseModel):
    id: str
    sku: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    capacity: Optional[str] = None
    configuration: Optional[str] = None
    condition: str = "new"


from app.schemas.offer import OfferSchema
from app.schemas.price_history import PriceSummary


class CanonicalProductDetail(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    identifiers: Dict[str, str] = Field(default_factory=dict)
    variants: List[ProductVariantSchema] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    sources: List[str] = Field(default_factory=list)
    recommendation: Optional[RecommendationBreakdown] = None
    offers: List[OfferSchema] = Field(default_factory=list)
    price_summary: Optional[PriceSummary] = None
    best_price: Optional[float] = None
    primary_retailer: Optional[str] = None
    offers_count: int = 0
    data_quality_score: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        # Sync images and image_urls
        if not self.images and self.image_urls:
            self.images = list(self.image_urls)
        elif not self.image_urls and self.images:
            self.image_urls = list(self.images)

        if not self.image_url and self.image_urls:
            self.image_url = self.image_urls[0]

        if not self.offers_count and self.offers:
            self.offers_count = len(self.offers)

        if self.best_price is None:
            if self.price_summary and self.price_summary.lowest_price:
                self.best_price = self.price_summary.lowest_price
            elif self.offers:
                prices = [o.price for o in self.offers if o.price is not None and o.price > 0]
                if prices:
                    self.best_price = min(prices)

        if not self.primary_retailer and self.offers:
            self.primary_retailer = self.offers[0].retailer
