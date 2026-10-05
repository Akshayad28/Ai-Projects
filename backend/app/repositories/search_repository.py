"""Search Repository."""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.search import SearchRecord, SearchResultRecord


class SearchRepository:
    """Database persistence for user searches and ranking logs."""

    async def log_search(
        self,
        db: AsyncSession,
        search_id: str,
        raw_query: str,
        provider_query: str,
        country: str,
        currency: str,
        duration_ms: int,
        intent_data: dict,
    ) -> SearchRecord:
        rec = SearchRecord(
            id=search_id,
            raw_query=raw_query,
            provider_query=provider_query,
            country=country,
            currency=currency,
            duration_ms=duration_ms,
            intent_data=intent_data,
        )
        db.add(rec)
        await db.commit()
        return rec
