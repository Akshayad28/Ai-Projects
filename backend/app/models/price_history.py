"""Price History / Observation Model."""
from __future__ import annotations

from app.db.models import PriceObservation

# Aliased to PriceHistory per specification
PriceHistory = PriceObservation

__all__ = ["PriceHistory", "PriceObservation"]
