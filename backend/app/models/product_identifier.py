"""Product Identifier database model."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.db.models import new_id


class ProductIdentifier(Base):
    """Normalized product identifiers (GTIN, EAN, UPC, ISBN, MPN, Model)."""

    __tablename__ = "product_identifiers"
    __table_args__ = (
        UniqueConstraint("id_type", "id_value"),
        Index("ix_identifier_lookup", "id_type", "id_value"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    id_type: Mapped[str] = mapped_column(String(32))  # gtin | ean | upc | isbn | mpn | model | asin | sku
    id_value: Mapped[str] = mapped_column(String(80), index=True)
    issuer: Mapped[Optional[str]] = mapped_column(String(64))

    product = relationship("Product")
