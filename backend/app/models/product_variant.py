"""Product Variant database model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.db.models import TZDateTime, utcnow, new_id


class ProductVariant(Base):
    """Specific product SKU / variant (e.g. 256GB Natural Titanium)."""

    __tablename__ = "product_variants"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    color: Mapped[Optional[str]] = mapped_column(String(64))
    size: Mapped[Optional[str]] = mapped_column(String(64))
    storage: Mapped[Optional[str]] = mapped_column(String(64))
    ram: Mapped[Optional[str]] = mapped_column(String(64))
    capacity: Mapped[Optional[str]] = mapped_column(String(64))
    configuration: Mapped[Optional[str]] = mapped_column(String(120))
    condition: Mapped[str] = mapped_column(String(24), default="new")
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    product = relationship("Product")
