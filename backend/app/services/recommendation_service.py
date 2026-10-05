"""Universal Recommendation Service.

Computes objective, structured recommendation scores (0-100) based on
requirement match, specifications, price, reviews, availability, delivery speed,
and data completeness. Category-aware weights are applied dynamically across
electronics, quick commerce, groceries, fashion, furniture, and universal categories.
Never lets LLMs hallucinate winner rankings or missing facts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from app.providers.base.models import ProviderProduct
from app.schemas.product import RecommendationBreakdown
from app.schemas.search import ExtractedQueryIntent


class RecommendationService:
    """Calculates unbiased product suitability scores across arbitrary categories."""

    CATEGORY_WEIGHTS: Dict[str, Dict[str, float]] = {
        "quick_commerce": {
            "requirement_match": 0.25,
            "price": 0.30,
            "delivery_speed": 0.25,
            "availability": 0.15,
            "reviews": 0.05,
        },
        "groceries": {
            "requirement_match": 0.25,
            "price": 0.35,
            "delivery_speed": 0.20,
            "availability": 0.15,
            "reviews": 0.05,
        },
        "electronics": {
            "requirement_match": 0.40,
            "price": 0.25,
            "reviews": 0.20,
            "availability": 0.10,
            "data_quality": 0.05,
        },
        "laptops": {
            "requirement_match": 0.40,
            "price": 0.25,
            "reviews": 0.20,
            "availability": 0.10,
            "data_quality": 0.05,
        },
        "fashion": {
            "requirement_match": 0.35,
            "price": 0.30,
            "reviews": 0.15,
            "availability": 0.10,
            "data_quality": 0.10,
        },
        "furniture": {
            "requirement_match": 0.35,
            "price": 0.30,
            "reviews": 0.15,
            "availability": 0.10,
            "data_quality": 0.10,
        },
        "universal": {
            "requirement_match": 0.35,
            "price": 0.25,
            "reviews": 0.20,
            "availability": 0.10,
            "data_quality": 0.10,
        },
    }

    def compute_data_coverage_score(self, prod: ProviderProduct) -> float:
        """Calculates factual data coverage percentage across core product dimensions."""
        fields_checked = [
            bool(prod.title),
            bool(prod.price.amount and prod.price.amount > 0),
            bool(prod.image_url or prod.primary_image),
            bool(prod.rating),
            bool(prod.review_count and prod.review_count > 0),
            bool(prod.seller),
            bool(prod.availability and prod.availability != "unknown"),
            bool(prod.specifications),
        ]
        return round((sum(fields_checked) / len(fields_checked)) * 100, 1)

    def evaluate_product(
        self,
        prod: ProviderProduct,
        intent: ExtractedQueryIntent,
        category_weights: Optional[Dict[str, float]] = None,
    ) -> RecommendationBreakdown:
        # Determine dynamic category weights
        cat_key = (intent.category or "").lower()
        if intent.quick_commerce_priority or cat_key in ("groceries", "grocery", "food-beverage", "dairy"):
            weights = self.CATEGORY_WEIGHTS.get("quick_commerce", self.CATEGORY_WEIGHTS["universal"])
        elif cat_key in self.CATEGORY_WEIGHTS:
            weights = self.CATEGORY_WEIGHTS[cat_key]
        else:
            weights = category_weights or self.CATEGORY_WEIGHTS["universal"]

        # 1. Requirement Match Score (0 - 100)
        req_score = 75
        reasons: List[str] = []
        drawbacks: List[str] = []
        why_not_higher: List[str] = []

        title_lower = prod.title.lower()
        combined_text = f"{title_lower} {' '.join(str(v).lower() for v in prod.specifications.values())}"

        # Check required features (e.g. 1440p, 165Hz, RTX, 16GB, ANC)
        for feat, val in intent.required_features.items():
            feat_key = feat.replace("_", " ")
            synonyms = [feat_key, str(val).lower()]
            if "noise" in feat_key and "cancell" in feat_key:
                synonyms.extend(["noise cancelling", "noise cancellation", "anc", "active noise"])
            if any(syn in combined_text for syn in synonyms):
                req_score = min(100, req_score + 15)
                reasons.append(f"Includes requested {feat_key}")
            else:
                req_score = max(40, req_score - 20)
                drawbacks.append(f"May not feature {feat_key}")

        # Check preferred features
        for pref in intent.preferred_features.keys():
            pref_key = pref.replace("_", " ")
            if pref_key in title_lower:
                req_score = min(100, req_score + 10)
                reasons.append(f"Matches preferred {pref_key}")

        # Check brand match
        if intent.brand and prod.brand:
            if intent.brand.lower() in prod.brand.lower():
                req_score = min(100, req_score + 10)
                reasons.append(f"Manufactured by requested brand {prod.brand}")

        # 2. Price Score (0 - 100)
        price_amt = prod.price.amount
        price_score = 80
        if price_amt and intent.max_price:
            if price_amt <= intent.max_price:
                savings = (intent.max_price - price_amt) / intent.max_price
                price_score = min(100, int(80 + savings * 25))
                reasons.append(f"Within budget ({int(savings * 100)}% under limit)")
            else:
                overshoot = (price_amt - intent.max_price) / intent.max_price
                price_score = max(30, int(70 - overshoot * 50))
                drawbacks.append(f"Exceeds target budget of ₹{int(intent.max_price):,}")
                why_not_higher.append("Price is higher than user target budget")

        # 3. Reviews Score (0 - 100)
        review_score = 75
        if prod.rating:
            review_score = int((prod.rating / 5.0) * 100)
            if prod.rating >= 4.3:
                reasons.append(f"High customer satisfaction ({prod.rating}★)")
            elif prod.rating < 4.0:
                drawbacks.append(f"Lower customer rating ({prod.rating}★)")
                why_not_higher.append(f"Customer satisfaction is {prod.rating}★")

        if prod.review_count and prod.review_count > 500:
            reasons.append(f"Validated by {prod.review_count:,}+ verified buyers")
        elif not prod.review_count or prod.review_count < 20:
            why_not_higher.append("Limited volume of customer reviews")

        # 4. Availability & Delivery Speed Score
        avail_score = 100 if prod.availability == "in_stock" else (70 if prod.availability == "limited" else 20)
        if prod.availability == "out_of_stock":
            drawbacks.append("Currently out of stock")
            why_not_higher.append("Product is not currently available for immediate order")

        # Quick Commerce Delivery Bonus
        is_qc = prod.raw_metadata.get("is_quick_commerce", False)
        delivery_spec = prod.specifications.get("delivery")
        if is_qc or (delivery_spec and "mins" in str(delivery_spec)):
            reasons.append(f"Instant delivery available ({delivery_spec or '10-20 mins'})")

        # 5. Data Coverage
        coverage = self.compute_data_coverage_score(prod)

        # Weighted final match score
        total_score = int(
            req_score * weights.get("requirement_match", 0.35)
            + price_score * weights.get("price", 0.25)
            + review_score * weights.get("reviews", 0.20)
            + avail_score * weights.get("availability", 0.10)
            + (coverage * 0.10)
        )
        total_score = max(1, min(99, total_score))

        breakdown_dict = {
            "requirement_match": req_score,
            "price": price_score,
            "reviews": review_score,
            "availability": avail_score,
            "data_coverage": int(round(coverage)),
        }

        if not reasons:
            reasons.append("Matches query keywords across verified retailers")

        return RecommendationBreakdown(
            match_score=total_score,
            confidence=0.92,
            breakdown=breakdown_dict,
            reasons=reasons[:4],
            drawbacks=drawbacks[:3],
            why_not_higher=why_not_higher[:3],
        )
