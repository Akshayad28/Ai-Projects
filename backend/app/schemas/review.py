"""Review Schemas."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    id: int
    source: str
    rating: Optional[float] = None
    title: Optional[str] = None
    text: Optional[str] = None
    review_date: Optional[str] = None
    verified: Optional[bool] = None


class ReviewAnalysisResponse(BaseModel):
    product_id: str
    reviews_analyzed: int = 0
    sentiment_score: Optional[float] = None
    positive_themes: List[str] = Field(default_factory=list)
    common_complaints: List[str] = Field(default_factory=list)
    common_praise: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    confidence: float = 1.0
    reviews: List[ReviewItem] = Field(default_factory=list)
