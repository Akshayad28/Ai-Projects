"""Firecrawl Provider Cache.

In-memory TTL cache for search queries and scraped product pages
to prevent redundant Firecrawl requests and credit exhaustion.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Dict, Optional, Tuple


class FirecrawlCache:
    """Thread-safe and async-safe in-memory TTL cache."""

    def __init__(self, default_ttl_seconds: int = 900) -> None:
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def hash_search_key(query: str, country: str = "IN", currency: str = "INR", limit: int = 20) -> str:
        raw = f"fc_search:{query.strip().lower()}:{country.upper()}:{currency.upper()}:{limit}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_scrape_key(url: str) -> str:
        raw = f"fc_scrape:{url.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._store:
                return None
            expires_at, value = self._store[key]
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        async with self._lock:
            # Periodic cleanup of expired entries if store gets large
            if len(self._store) > 1000:
                now = time.time()
                expired = [k for k, (exp, _) in self._store.items() if now > exp]
                for k in expired:
                    del self._store[k]

            self._store[key] = (time.time() + ttl, value)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
