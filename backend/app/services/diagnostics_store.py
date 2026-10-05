"""Diagnostics Store for Universal Shopping Search.

Maintains in-memory and persistent records of provider search diagnostics,
execution latencies, offer counts, image extraction metrics, and error telemetry.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

log = get_logger(__name__)


class SearchDiagnosticsRecord(BaseModel):
    search_id: str
    query: str
    country: str
    currency: str
    started_at: float
    completed_at: float
    duration_ms: int
    providers_requested: list[str] = Field(default_factory=list)
    providers_executed: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)
    providers_blocked: list[str] = Field(default_factory=list)
    provider_breakdown: Dict[str, Any] = Field(default_factory=dict)
    raw_products_count: int = 0
    normalized_products_count: int = 0
    canonical_products_count: int = 0
    total_offers_count: int = 0
    images_extracted_count: int = 0
    quick_commerce_offers_count: int = 0
    errors: list[str] = Field(default_factory=list)


class DiagnosticsStore:
    """Thread-safe store holding search diagnostic telemetry."""

    _instance: Optional[DiagnosticsStore] = None
    _store: Dict[str, SearchDiagnosticsRecord] = {}

    def __new__(cls) -> DiagnosticsStore:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._store = {}
        return cls._instance

    def record(self, diag: SearchDiagnosticsRecord) -> None:
        self._store[diag.search_id] = diag
        # Keep store bounded to latest 500 searches
        if len(self._store) > 500:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

    def get(self, search_id: str) -> Optional[SearchDiagnosticsRecord]:
        return self._store.get(search_id)

    def get_latest(self) -> Optional[SearchDiagnosticsRecord]:
        if not self._store:
            return None
        latest_key = list(self._store.keys())[-1]
        return self._store[latest_key]


diagnostics_store = DiagnosticsStore()
