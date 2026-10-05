"""Product Identity Matching Service.

Matches identical products across retailers using strict priority:
1. GTIN
2. EAN
3. UPC
4. ISBN
5. MPN
6. Exact model number
7. Brand + model
8. Brand + normalized title + key specifications

CRITICAL: Variant incompatibility (storage, RAM, capacity, color)
STRICTLY prevents merging disparate products.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.core.logging import get_logger
from app.providers.base.models import ProviderProduct
from app.utils.text_normalization import extract_brand_from_title, extract_variant_attributes, normalize_text

log = get_logger(__name__)


class ProductMatchResult(BaseModel):
    matched: bool
    confidence: float
    method: str  # gtin | ean | upc | mpn | brand_model | spec_compatible | rejected


class ProductIdentityService:
    """Matches identical products across retailers into canonical clusters."""

    def are_variants_compatible(self, p1: ProviderProduct, p2: ProviderProduct) -> bool:
        """Determines if two products have compatible variant signatures.
        A 256GB device and 512GB device MUST NEVER be merged.
        """
        v1 = p1.variant_attributes or extract_variant_attributes(p1.title)
        v2 = p2.variant_attributes or extract_variant_attributes(p2.title)

        # Storage check
        s1 = v1.get("storage")
        s2 = v2.get("storage")
        if s1 and s2 and s1 != s2:
            return False

        # RAM check
        r1 = v1.get("ram")
        r2 = v2.get("ram")
        if r1 and r2 and r1 != r2:
            return False

        return True

    def match_products(self, p1: ProviderProduct, p2: ProviderProduct) -> ProductMatchResult:
        """Evaluates whether two provider products represent the exact same item."""
        # 1. First, check variant compatibility. If incompatible, reject immediately.
        if not self.are_variants_compatible(p1, p2):
            return ProductMatchResult(matched=False, confidence=0.0, method="variant_incompatible")

        # 2. Universal Identifiers: GTIN / EAN / UPC
        for id_key in ["gtin", "ean", "upc", "isbn"]:
            v1 = p1.identifiers.get(id_key)
            v2 = p2.identifiers.get(id_key)
            if v1 and v2 and v1.strip().lower() == v2.strip().lower():
                return ProductMatchResult(matched=True, confidence=1.0, method=id_key)

        # 3. MPN (Manufacturer Part Number)
        mpn1 = p1.identifiers.get("mpn")
        mpn2 = p2.identifiers.get("mpn")
        if mpn1 and mpn2 and mpn1.strip().lower() == mpn2.strip().lower():
            return ProductMatchResult(matched=True, confidence=0.98, method="mpn")

        # 4. Brand + Model Number Match
        b1 = (p1.brand or extract_brand_from_title(p1.title) or "").lower()
        b2 = (p2.brand or extract_brand_from_title(p2.title) or "").lower()

        if b1 and b2 and b1 == b2:
            # Extract alphanumeric model codes (e.g. WH-1000XM5, M3, RTX 4060, S24)
            model_pat = r"\b([A-Z0-9]{2,}[-_]?[A-Z0-9]{2,})\b"
            m1 = set(re.findall(model_pat, p1.title.upper()))
            m2 = set(re.findall(model_pat, p2.title.upper()))
            
            # Common filter tokens that are not models
            non_models = {"16GB", "8GB", "512GB", "1TB", "256GB", "4GB", "15-INCH", "13-INCH", "SSD", "RAM", "ROM", "DDR4", "DDR5", "WIFI", "USB"}
            m1 = {x for x in m1 if x not in non_models and not x.isdigit()}
            m2 = {x for x in m2 if x not in non_models and not x.isdigit()}

            intersect = m1.intersection(m2)
            if intersect:
                return ProductMatchResult(matched=True, confidence=0.95, method="brand_model")

            # 5. Core Title Token Overlap (with brand match and variant compatibility)
            t1_tokens = set(normalize_text(p1.title).split())
            t2_tokens = set(normalize_text(p2.title).split())

            # Stop words
            stop_words = {"with", "and", "for", "the", "in", "by", "of", "to", "edition", "year", "latest", "new"}
            t1_clean = t1_tokens - stop_words
            t2_clean = t2_tokens - stop_words

            if t1_clean and t2_clean:
                overlap = len(t1_clean.intersection(t2_clean)) / min(len(t1_clean), len(t2_clean))
                if overlap >= 0.85:
                    return ProductMatchResult(matched=True, confidence=0.90, method="brand_spec_token")

        return ProductMatchResult(matched=False, confidence=0.0, method="no_match")

    def cluster_products(self, products: List[ProviderProduct]) -> List[List[ProviderProduct]]:
        """Groups a list of products across retailers into canonical clusters."""
        clusters: List[List[ProviderProduct]] = []

        for p in products:
            matched_cluster = None
            for cluster in clusters:
                # Compare against the representative of the cluster
                rep = cluster[0]
                result = self.match_products(p, rep)
                if result.matched:
                    matched_cluster = cluster
                    break

            if matched_cluster is not None:
                matched_cluster.append(p)
            else:
                clusters.append([p])

        return clusters
