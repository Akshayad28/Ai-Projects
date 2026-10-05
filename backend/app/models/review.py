"""Review and Review Analysis Models."""
from __future__ import annotations

from app.db.models import Review, ReviewSummary

# Aliased to ReviewAnalysis per specification
ReviewAnalysis = ReviewSummary

__all__ = ["Review", "ReviewAnalysis", "ReviewSummary"]
