"""Retailer database model."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.db.models import new_id


class Retailer(Base):
    """Shopping website or marketplace (Amazon, Flipkart, eBay, etc.)."""

    __tablename__ = "retailers"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # slug: amazon-in, flipkart
    name: Mapped[str] = mapped_column(String(120), unique=True)
    domain: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    affiliate_program_active: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
