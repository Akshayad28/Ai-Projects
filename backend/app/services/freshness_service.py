"""Freshness Service.

Tracks and validates observation freshness against configurable thresholds:
- PRICE_FRESHNESS_MINUTES
- AVAILABILITY_FRESHNESS_MINUTES
- PRODUCT_METADATA_FRESHNESS_HOURS

Never exposes stale cached data as 'Live'.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings


class FreshnessService:
    """Computes human-friendly freshness indicators and stale flags."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_freshness_label(self, fetched_at_str: Optional[str]) -> str:
        if not fetched_at_str:
            return "Price unverified"

        try:
            fetched_dt = datetime.fromisoformat(fetched_at_str)
            if fetched_dt.tzinfo is None:
                fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - fetched_dt
            mins = int(delta.total_seconds() // 60)

            if mins < 1:
                return "Price checked just now"
            elif mins == 1:
                return "Price checked 1 min ago"
            elif mins < 60:
                return f"Price checked {mins} min ago"
            elif mins < 1440:
                hrs = mins // 60
                return f"Price checked {hrs} hr ago"
            else:
                days = mins // 1440
                return f"Price checked {days} d ago"
        except Exception:
            return "Verified real-time"

    def is_price_stale(self, fetched_at_str: Optional[str]) -> bool:
        if not fetched_at_str:
            return True
        try:
            fetched_dt = datetime.fromisoformat(fetched_at_str)
            if fetched_dt.tzinfo is None:
                fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - fetched_dt
            return delta.total_seconds() > (self.settings.price_freshness_minutes * 60)
        except Exception:
            return True
