"""Normalization Service.

Normalizes provider-specific products into canonical ShopBuddy representation.
Preserves original display titles while generating normalized search tokens.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.providers.base.models import ProviderProduct
from app.schemas.product import CanonicalProductDetail, ProductVariantSchema
from app.schemas.offer import OfferSchema
from app.utils.text_normalization import extract_brand_from_title, extract_variant_attributes, normalize_text
from app.utils.hashing import generate_identity_key


class NormalizationService:
    """Standardizes disparate provider products into canonical models."""

    def normalize_provider_product(self, prod: ProviderProduct, category_id: Optional[str] = None) -> CanonicalProductDetail:
        brand = prod.brand or extract_brand_from_title(prod.title)
        variant_attrs = prod.variant_attributes or extract_variant_attributes(prod.title)

        # Generate deterministic identity key based on brand, extracted model/core title, and variants
        norm_title = normalize_text(prod.title)
        var_sig = "-".join(f"{k}:{v}" for k, v in sorted(variant_attrs.items()))
        ident_key = generate_identity_key(brand or "unknown", norm_title, var_sig)

        variant = ProductVariantSchema(
            id=f"var-{ident_key[:12]}",
            storage=variant_attrs.get("storage"),
            ram=variant_attrs.get("ram"),
            color=variant_attrs.get("color"),
            condition="new",
        )

        return CanonicalProductDetail(
            id=ident_key,
            title=prod.title,
            brand=brand,
            model=prod.model,
            category_id=category_id,
            description=None,
            images=prod.image_urls or ([prod.image_url] if prod.image_url else []),
            specifications=prod.specifications,
            identifiers=prod.identifiers,
            variants=[variant],
            rating=prod.rating,
            review_count=prod.review_count,
            sources=[prod.provider],
            data_quality_score=self.calculate_data_completeness(prod),
        )

    def calculate_data_completeness(self, prod: ProviderProduct) -> float:
        """Calculates completeness score (0.0 to 1.0) for the extracted data."""
        score = 0.0
        if prod.title and len(prod.title) > 10:
            score += 0.25
        if prod.price.amount and prod.price.amount > 0:
            score += 0.25
        if prod.image_url:
            score += 0.15
        if prod.brand:
            score += 0.15
        if prod.rating is not None:
            score += 0.10
        if prod.review_count is not None:
            score += 0.10
        return round(score, 2)
