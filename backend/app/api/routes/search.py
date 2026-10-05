"""Search API Route.

Executes end-to-end shopping search across real retailers, isolating failures,
normalizing canonical products, aggregating offers, and computing match scores.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.resilience import enforce_rate_limit
from app.database.connection import get_db
from app.schemas.search import SearchQueryPayload, UnifiedSearchResponse
from app.services.search_orchestrator import SearchOrchestrator

router = APIRouter(tags=["Search"])
orchestrator = SearchOrchestrator()


@router.post("/search", response_model=UnifiedSearchResponse)
async def search_products(
    payload: SearchQueryPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UnifiedSearchResponse:
    settings = get_settings()
    await enforce_rate_limit(request, "search", settings.user_rate_limit_per_minute)

    return await orchestrator.execute_search(
        raw_query=payload.query,
        country=payload.country,
        currency=payload.currency,
        sort_by=payload.sort_by,
        page=payload.page,
        page_size=payload.page_size,
        db=db,
    )
