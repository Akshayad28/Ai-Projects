"""Database models.

The product database is the source of truth for every fact shown to users.
Prices, availability and reviews always carry provider + timestamp metadata.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import TypeDecorator

from app.db.session import Base

EMBEDDING_DIM = 1536


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class Embedding(TypeDecorator):
    """pgvector `vector` on PostgreSQL, JSON elsewhere (dev/test only)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBEDDING_DIM))
        return dialect.type_descriptor(JSON())


class TZDateTime(TypeDecorator):
    """Always returns timezone-aware UTC datetimes (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# ─────────────────────────── Users ───────────────────────────


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    use_personalization: Mapped[bool] = mapped_column(Boolean, default=True)
    save_history: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_brands: Mapped[List[str]] = mapped_column(JSON, default=list)
    excluded_brands: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


# ─────────────────────────── Categories ───────────────────────────


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # slug
    name: Mapped[str] = mapped_column(String(120))
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), index=True)
    department: Mapped[str] = mapped_column(String(64), index=True)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)

    attributes: Mapped[List["CategoryAttribute"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="CategoryAttribute.display_order"
    )
    weights: Mapped[List["CategoryWeight"]] = relationship(cascade="all, delete-orphan")
    rules: Mapped[List["CategoryRule"]] = relationship(cascade="all, delete-orphan")


class CategoryAttribute(Base):
    __tablename__ = "category_attributes"
    __table_args__ = (UniqueConstraint("category_id", "key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    value_type: Mapped[str] = mapped_column(String(16))  # number | enum | text | bool
    unit: Mapped[Optional[str]] = mapped_column(String(24))
    # Regex patterns (first capture group = value) applied to provider titles/specs.
    extract_patterns: Mapped[List[str]] = mapped_column(JSON, default=list)
    # Provider spec field names that map to this attribute.
    source_keys: Mapped[List[str]] = mapped_column(JSON, default=list)
    filterable: Mapped[bool] = mapped_column(Boolean, default=False)
    show_on_card: Mapped[bool] = mapped_column(Boolean, default=False)
    comparable: Mapped[bool] = mapped_column(Boolean, default=True)
    higher_is_better: Mapped[Optional[bool]] = mapped_column(Boolean)
    display_order: Mapped[int] = mapped_column(Integer, default=100)

    category: Mapped[Category] = relationship(back_populates="attributes")


class CategoryWeight(Base):
    __tablename__ = "category_weights"
    __table_args__ = (UniqueConstraint("category_id", "factor"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    factor: Mapped[str] = mapped_column(String(48))
    weight: Mapped[float] = mapped_column(Float)


class CategoryRule(Base):
    """Maps a use-case/requirement phrase to attribute conditions.

    payload example: {"match": ["programming", "coding"],
                      "conditions": [{"attribute": "ram_gb", "op": ">=", "value": 16}]}
    """

    __tablename__ = "category_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)


# ─────────────────────────── Products ───────────────────────────


class Product(Base):
    """Canonical product (one per distinct variant identity)."""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_brand_category", "brand", "category_id"),
        Index("ix_products_normalized_name", "normalized_name"),
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500))
    brand: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    model: Mapped[Optional[str]] = mapped_column(String(160))
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    gtin: Mapped[Optional[str]] = mapped_column(String(14), index=True)
    upc: Mapped[Optional[str]] = mapped_column(String(14), index=True)
    ean: Mapped[Optional[str]] = mapped_column(String(14), index=True)
    mpn: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    asin: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    condition: Mapped[str] = mapped_column(String(24), default="new")
    region: Mapped[Optional[str]] = mapped_column(String(8))
    variant: Mapped[dict] = mapped_column(JSON, default=dict)  # storage/color/size/capacity
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    attribute_sources: Mapped[dict] = mapped_column(JSON, default=dict)
    image_urls: Mapped[List[str]] = mapped_column(JSON, default=list)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    rating_source: Mapped[Optional[str]] = mapped_column(String(120))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow, index=True)

    sources: Mapped[List["ProductSource"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    offers: Mapped[List["Offer"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductSource(Base):
    __tablename__ = "product_sources"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(48), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(2))
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    product: Mapped[Product] = relationship(back_populates="sources")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("product_id", "provider", "retailer_name", "seller_name"),
        Index("ix_offers_price", "price_amount"),
        Index("ix_offers_availability", "availability"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(48))
    retailer_name: Mapped[str] = mapped_column(String(160), index=True)
    retailer_domain: Mapped[Optional[str]] = mapped_column(String(160))
    seller_name: Mapped[str] = mapped_column(String(160), default="")
    seller_rating: Mapped[Optional[float]] = mapped_column(Float)
    seller_rating_count: Mapped[Optional[int]] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String(2))
    price_amount: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    original_price: Mapped[Optional[float]] = mapped_column(Float)
    price_status: Mapped[str] = mapped_column(String(16), default="unverified")  # verified | unverified
    shipping_amount: Mapped[Optional[float]] = mapped_column(Float)
    shipping_text: Mapped[Optional[str]] = mapped_column(String(255))
    delivery_estimate: Mapped[Optional[str]] = mapped_column(String(255))
    tax_amount: Mapped[Optional[float]] = mapped_column(Float)
    coupon_text: Mapped[Optional[str]] = mapped_column(String(255))
    cashback_text: Mapped[Optional[str]] = mapped_column(String(255))
    availability: Mapped[str] = mapped_column(String(24), default="unknown")
    condition: Mapped[str] = mapped_column(String(24), default="new")
    url: Mapped[Optional[str]] = mapped_column(Text)
    affiliate_url: Mapped[Optional[str]] = mapped_column(Text)
    return_policy: Mapped[Optional[str]] = mapped_column(Text)
    warranty: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    last_checked_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)

    # Quick commerce & Unit Economics extensions
    is_quick_commerce: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    delivery_eta_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    delivery_window: Mapped[Optional[str]] = mapped_column(String(120))
    delivery_fee: Mapped[Optional[float]] = mapped_column(Float)
    platform_fee: Mapped[Optional[float]] = mapped_column(Float)
    handling_fee: Mapped[Optional[float]] = mapped_column(Float)
    surge_fee: Mapped[Optional[float]] = mapped_column(Float)
    pack_size: Mapped[Optional[str]] = mapped_column(String(80))
    unit_price: Mapped[Optional[float]] = mapped_column(Float)
    unit_measure: Mapped[Optional[str]] = mapped_column(String(40))
    store_name: Mapped[Optional[str]] = mapped_column(String(160))
    location_checked: Mapped[Optional[str]] = mapped_column(String(120))

    product: Mapped[Product] = relationship(back_populates="offers")


class PriceObservation(Base):
    """Every verified price we have ever actually observed. Never synthesized."""

    __tablename__ = "price_observations"
    __table_args__ = (
        Index("ix_price_obs_product_time", "product_id", "observed_at"),
        {"extend_existing": True},
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(48), default="retailer")
    retailer_name: Mapped[str] = mapped_column(String(160))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    observed_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    offer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __init__(self, **kwargs):
        if "retailer" in kwargs and "retailer_name" not in kwargs:
            kwargs["retailer_name"] = kwargs.pop("retailer")
        if "price" in kwargs and "amount" not in kwargs:
            kwargs["amount"] = kwargs.pop("price")
        if "provider" not in kwargs:
            kwargs["provider"] = kwargs.get("retailer_name", "retailer")
        if "captured_at" in kwargs and "observed_at" not in kwargs:
            kwargs["observed_at"] = kwargs.pop("captured_at")
        super().__init__(**kwargs)

    @hybrid_property
    def price(self) -> float:
        return self.amount

    @price.setter
    def price(self, val: float):
        self.amount = val

    @hybrid_property
    def retailer(self) -> str:
        return self.retailer_name

    @retailer.setter
    def retailer(self, val: str):
        self.retailer_name = val

    @hybrid_property
    def captured_at(self) -> datetime:
        return self.observed_at

    @captured_at.setter
    def captured_at(self, val: datetime):
        self.observed_at = val


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("product_id", "source", "external_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(120))
    external_id: Mapped[str] = mapped_column(String(255))
    rating: Mapped[Optional[float]] = mapped_column(Float)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    text: Mapped[Optional[str]] = mapped_column(Text)
    review_date: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    verified: Mapped[Optional[bool]] = mapped_column(Boolean)
    fetched_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class ReviewSummary(Base):
    __tablename__ = "review_summaries"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    reviews_analyzed: Mapped[int] = mapped_column(Integer)
    positive_themes: Mapped[List[Any]] = mapped_column(JSON, default=list)
    negative_themes: Mapped[List[Any]] = mapped_column(JSON, default=list)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(32))  # llm | keyword
    generated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[str] = mapped_column(String(80))
    embedding: Mapped[List[float]] = mapped_column(Embedding)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


# ─────────────────────────── User data ───────────────────────────


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    target_price: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    price_when_added: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    alert_type: Mapped[str] = mapped_column(String(32))  # target_price | percent_drop | back_in_stock | historical_low
    target_price: Mapped[Optional[float]] = mapped_column(Float)
    percent_drop: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    baseline_price: Mapped[Optional[float]] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    product_id: Mapped[Optional[str]] = mapped_column(String(80))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)


class SearchHistory(Base):
    __tablename__ = "search_history"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(2))
    category_id: Mapped[Optional[str]] = mapped_column(String(64))
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, index=True)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    search_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    useful: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[Optional[str]] = mapped_column(String(48))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


# ─────────────────────────── Operations ───────────────────────────


class ProviderCallLog(Base):
    __tablename__ = "provider_call_logs"
    __table_args__ = (Index("ix_provider_calls_provider_time", "provider", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(48))
    operation: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(16))  # ok | error | timeout | rate_limited | skipped
    latency_ms: Mapped[int] = mapped_column(Integer)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
