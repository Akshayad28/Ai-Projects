"""Rate limiting and retry helpers."""
from __future__ import annotations

import asyncio
import random
import time
from typing import Awaitable, Callable, Dict, Optional, Tuple, Type, TypeVar

from fastapi import HTTPException, Request

from app.core.cache import get_cache

T = TypeVar("T")


class TokenBucket:
    """Per-provider outbound rate limiter (in-process)."""

    def __init__(self, rate_per_second: float, capacity: Optional[int] = None) -> None:
        self.rate = rate_per_second
        self.capacity = capacity or max(1, int(rate_per_second * 2))
        self.tokens = float(self.capacity)
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await asyncio.sleep((1 - self.tokens) / self.rate)


class RetryableError(Exception):
    """Raised for transient failures (timeouts, 429, 5xx)."""


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    attempts: int = 3,
    base_delay: float = 0.4,
    retry_on: Tuple[Type[BaseException], ...] = (RetryableError,),
) -> T:
    last: Optional[BaseException] = None
    for attempt in range(attempts):
        try:
            return await fn()
        except retry_on as exc:  # type: ignore[misc]
            last = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, base_delay))
    assert last is not None
    raise last


_buckets: Dict[str, TokenBucket] = {}


def provider_bucket(name: str, rate_per_second: float) -> TokenBucket:
    if name not in _buckets:
        _buckets[name] = TokenBucket(rate_per_second)
    return _buckets[name]


async def enforce_rate_limit(request: Request, scope: str, limit_per_minute: int) -> None:
    """Fixed-window limiter keyed by user id (if authenticated) or client IP."""
    identity = getattr(request.state, "user_id", None) or (request.client.host if request.client else "anon")
    window = int(time.time() // 60)
    key = f"rl:{scope}:{identity}:{window}"
    count = await get_cache().incr(key, 70)
    if count > limit_per_minute:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
