"""Firecrawl Pydantic Schemas.

Defines schemas for URL discovery, dynamic product extraction,
validation, and operational diagnostics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class URLClassification(str, Enum):
    """Classification for web pages discovered via Firecrawl search."""
    PRODUCT_PAGE = "product_page"
    RETAILER_CATEGORY = "retailer_category"
    SEARCH_PAGE = "search_page"
    ARTICLE_REVIEW = "article_review"
    COMPARISON_PAGE = "comparison_page"
    IRRELEVANT_PAGE = "irrelevant_page"


class AttributeItem(BaseModel):
    """Dynamic key-value attribute supporting arbitrary product categories."""
    key: str
    value: str


class FirecrawlSearchResultItem(BaseModel):
    """Discovered search result with origin provenance."""
    title: str
    url: str
    description: Optional[str] = None
    domain: Optional[str] = None
    position: Optional[int] = None
    query: str
    classification: URLClassification = URLClassification.PRODUCT_PAGE
    confidence: float = 1.0
    fetched_at: str = Field(default_factory=utcnow_str)


class FirecrawlExtractedProduct(BaseModel):
    """Target schema for dynamic structured extraction from product pages.

    Supports arbitrary product categories with no fixed electronic-only fields.
    """
    # Identity
    product_name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    model_number: Optional[str] = None
    mpn: Optional[str] = None
    gtin: Optional[str] = None
    ean: Optional[str] = None
    upc: Optional[str] = None
    asin: Optional[str] = None
    sku: Optional[str] = None

    # Pricing
    price: Optional[float] = None
    currency: Optional[str] = None
    original_price: Optional[float] = None
    discount: Optional[float] = None
    sale_price: Optional[float] = None
    price_text: Optional[str] = None

    # Product details
    description: Optional[str] = None
    category: Optional[str] = None
    attributes: List[AttributeItem] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    specifications: Dict[str, str] = Field(default_factory=dict)
    variant: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    capacity: Optional[str] = None
    configuration: Optional[str] = None

    # Media
    image_url: Optional[str] = None
    additional_images: List[str] = Field(default_factory=list)

    # Retail / Seller
    retailer: Optional[str] = None
    seller: Optional[str] = None
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None

    # Availability
    availability: Optional[str] = None
    stock_status: Optional[str] = None

    # Shipping / Policy
    shipping_cost: Optional[float] = None
    delivery_information: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None

    # Reviews
    rating: Optional[float] = None
    review_count: Optional[int] = None
    review_summary: Optional[str] = None

    # Links & Metadata
    canonical_url: Optional[str] = None
    product_url: Optional[str] = None
    source: str = "firecrawl"
    fetched_at: str = Field(default_factory=utcnow_str)
    extraction_method: str = "structured_json"
    confidence: float = 1.0


class FirecrawlDiagnostics(BaseModel):
    """Detailed operational metrics for Firecrawl provider."""
    search_attempted: bool = False
    search_results: int = 0
    product_urls_detected: int = 0
    pages_scraped: int = 0
    extraction_attempted: int = 0
    products_extracted: int = 0
    products_validated: int = 0
    products_rejected: int = 0
    offers_extracted: int = 0
    raw: int = 0
    normalized: int = 0
    canonical: int = 0
    offers: int = 0
    errors: int = 0
    status: str = "CONFIGURED"  # CONFIGURED | HEALTHY | DEGRADED | BLOCKED | UNAVAILABLE
    last_success: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
