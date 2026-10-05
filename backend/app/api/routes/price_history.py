"""Price History API Route."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.price_history import PriceHistoryResponse
from app.services.price_service import PriceService

router = APIRouter(prefix="/price-history", tags=["Price History"])
price_service = PriceService()


@router.get("", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: str = Query(..., description="Canonical product ID"),
    db: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    return await price_service.get_price_history(db, product_id)
