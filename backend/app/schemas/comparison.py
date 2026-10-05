"""Comparison Schemas.

Structures for multi-product side-by-side comparison, dynamic dimensional scorecards,
verified retailer offers, dynamic specification sections with winner detection,
and AI-synthesized buying insights and verdicts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.offer import OfferSchema


class ComparisonRequest(BaseModel):
    product_ids: List[str] = Field(..., min_length=1, max_length=4)


class ComparisonProductItem(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    best_price: Optional[float] = None
    currency: str = "INR"
    primary_retailer: Optional[str] = None
    offers_count: int = 0
    offers: List[OfferSchema] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    identifiers: Dict[str, str] = Field(default_factory=dict)
    condition: str = "new"


class ScorecardDimension(BaseModel):
    dimension: str
    scores: Dict[str, int] = Field(default_factory=dict)  # product_id -> score (0-100)
    winner_id: Optional[str] = None
    rationale: str = ""


class ComparisonAttributeRow(BaseModel):
    key: str
    label: str
    values: Dict[str, Any] = Field(default_factory=dict)  # product_id -> display string/number/"—"
    unit: Optional[str] = None
    winner_id: Optional[str] = None
    winner_reason: Optional[str] = None
    is_highlight: bool = False
    is_neutral: bool = False
    is_different: bool = True
    score_explanation: Optional[Dict[str, str]] = None
    raw_values: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, str]] = None
    verified: bool = True


class ComparisonCategoryScore(BaseModel):
    name: str
    weight: float
    scores: Dict[str, int] = Field(default_factory=dict)  # product_id -> 0-100
    winner_id: Optional[str] = None
    winner_reason: Optional[str] = None
    reasons: Dict[str, List[str]] = Field(default_factory=dict)  # product_id -> ["+ Faster CPU", "+ More RAM"]
    attributes: List[ComparisonAttributeRow] = Field(default_factory=list)


class PriceComparison(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_difference: Optional[float] = None
    percentage_difference: Optional[float] = None
    cheapest_product_id: Optional[str] = None
    currency: str = "INR"
    product_prices: Dict[str, Optional[float]] = Field(default_factory=dict)
    best_retailers: Dict[str, Optional[str]] = Field(default_factory=dict)
    best_offer_urls: Dict[str, Optional[str]] = Field(default_factory=dict)
    value_scores: Dict[str, int] = Field(default_factory=dict)
    value_rationale: str = ""


class RatingComparison(BaseModel):
    product_ratings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    highest_rated_id: Optional[str] = None
    rating_advantage: Optional[str] = None


class ReviewInsights(BaseModel):
    insights: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # product_id -> { likes: [...], complaints: [...], summary: "..." }
    available: bool = False
    status_message: str = "Review intelligence unavailable from current sources."


class ComparisonSection(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    is_default_expanded: bool = True
    attributes: List[ComparisonAttributeRow] = Field(default_factory=list)


class ProductBuyingInsights(BaseModel):
    product_id: str
    why_choose: List[str] = Field(default_factory=list)  # verified pros / key strengths
    considerations: List[str] = Field(default_factory=list)  # verified cons / trade-offs
    best_suited_for: str = ""


class ComparisonAIVerdict(BaseModel):
    best_overall_id: Optional[str] = None
    best_overall_title: Optional[str] = None
    best_value_id: Optional[str] = None
    best_value_title: Optional[str] = None
    verdict_summary: str
    confidence: int = 90  # Calculated from available evidence
    best_for: List[str] = Field(default_factory=list)  # e.g. ["Performance", "Portability", "Value"]
    why_it_wins: Optional[str] = None
    why_best_value: Optional[str] = None
    key_differences: List[str] = Field(default_factory=list)
    trade_offs: Dict[str, List[str]] = Field(default_factory=dict)  # product_id -> ["Choose Product A if..."]
    buying_recommendations: Dict[str, str] = Field(default_factory=dict)


class ComparisonResponse(BaseModel):
    products: List[ComparisonProductItem] = Field(default_factory=list)
    verdict: ComparisonAIVerdict
    scorecard: List[ScorecardDimension] = Field(default_factory=list)
    sections: List[ComparisonSection] = Field(default_factory=list)
    buying_insights: List[ProductBuyingInsights] = Field(default_factory=list)
    category_name: Optional[str] = None
    generated_at: str = "Just now"
    ai_powered: bool = True
    product_type: str = "general"
    categories: List[ComparisonCategoryScore] = Field(default_factory=list)
    overall_scores: Dict[str, int] = Field(default_factory=dict)
    overall_winner_id: Optional[str] = None
    overall_winner_reason: Optional[str] = None
    price_comparison: Optional[PriceComparison] = None
    rating_comparison: Optional[RatingComparison] = None
    review_insights: Optional[ReviewInsights] = None
    data_coverage: Dict[str, int] = Field(default_factory=dict)
    available_specs_count: Dict[str, int] = Field(default_factory=dict)


