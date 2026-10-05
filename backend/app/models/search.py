"""Search and Search Result database models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.db.models import TZDateTime, utcnow, new_id


class SearchRecord(Base):
    """Tracks search queries and intent parsing."""

    __tablename__ = "searches"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    raw_query: Mapped[str] = mapped_column(String(500))
    provider_query: Mapped[str] = mapped_column(String(500))
    category: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    country: Mapped[str] = mapped_column(String(2), default="IN")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    intent_data: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)


class SearchResultRecord(Base):
    """Tracks rank position and recommendation scores for a search."""

    __tablename__ = "search_results"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    match_score: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
