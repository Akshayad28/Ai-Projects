"""Seller database model."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.db.models import new_id


class Seller(Base):
    """Merchant / Seller on a marketplace (e.g. Appario Retail, RetailNet)."""

    __tablename__ = "sellers"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    retailer_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    rating_count: Mapped[Optional[int]] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    fulfilled_by_retailer: Mapped[bool] = mapped_column(Boolean, default=False)
