"""Availability History database model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.db.models import TZDateTime, utcnow


class AvailabilityHistory(Base):
    """Historical stock and availability records captured per retailer offer."""

    __tablename__ = "availability_history"
    __table_args__ = (
        Index("ix_avail_history_offer_time", "offer_id", "captured_at"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24))  # IN_STOCK | LOW_STOCK | OUT_OF_STOCK | PREORDER | UNKNOWN
    captured_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)

    offer = relationship("Offer")
