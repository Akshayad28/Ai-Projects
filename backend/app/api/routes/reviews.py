"""Reviews API Route."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.review import ReviewAnalysisResponse
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])
review_service = ReviewService()


@router.get("", response_model=ReviewAnalysisResponse)
async def get_reviews(
    product_id: str = Query(..., description="Canonical product ID"),
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalysisResponse:
    return await review_service.get_reviews_for_product(db, product_id)
