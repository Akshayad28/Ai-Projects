"""Firecrawl Rate Limiter.

Provides bounded async concurrency and requests-per-second throttling to respect
Firecrawl API rate limits and avoid saturating system or network resources.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional


class FirecrawlRateLimiter:
    """Combines an async Semaphore (concurrency limit) with a TokenBucket (RPS limit)."""

    def __init__(
        self,
        max_concurrency: int = 5,
        requests_per_second: float = 5.0,
    ) -> None:
        self.max_concurrency = max(1, max_concurrency)
        self.rate = max(0.1, requests_per_second)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._token_lock = asyncio.Lock()
        self._tokens = float(self.rate)
        self._last_update = time.monotonic()

    async def acquire_concurrency(self) -> None:
        """Acquires a slot from the concurrency semaphore."""
        await self._semaphore.acquire()

    def release_concurrency(self) -> None:
        """Releases a slot back to the concurrency semaphore."""
        self._semaphore.release()

    async def throttle(self) -> None:
        """Throttles execution to maintain desired requests-per-second rate."""
        async with self._token_lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(float(self.rate), self._tokens + elapsed * self.rate)
                self._last_update = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                wait_time = (1.0 - self._tokens) / self.rate
                await asyncio.sleep(max(0.01, wait_time))

    async def __aenter__(self) -> "FirecrawlRateLimiter":
        await self.acquire_concurrency()
        await self.throttle()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release_concurrency()
