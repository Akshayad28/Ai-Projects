"""Data Quality Service."""
from __future__ import annotations

from typing import Any, Dict
from app.providers.base.models import ProviderProduct


class DataQualityService:
    """Evaluates data completeness, seller reliability, and field accuracy."""

    def evaluate(self, prod: ProviderProduct) -> Dict[str, Any]:
        issues = []
        if not prod.price.amount or prod.price.amount <= 0:
            issues.append("Missing price")
        if not prod.image_url:
            issues.append("Missing image")
        if not prod.brand:
            issues.append("Unidentified brand")
        if prod.rating is None:
            issues.append("No user rating")

        quality_score = max(0.0, 1.0 - (len(issues) * 0.2))
        return {
            "score": round(quality_score, 2),
            "is_sufficient_for_ranking": (prod.price.amount is not None and prod.price.amount > 0),
            "issues": issues,
        }
