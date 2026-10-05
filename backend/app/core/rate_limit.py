"""Sliding-window in-memory rate limiter with per-route policies."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable, Dict, Optional
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

log = get_logger(__name__)


class SlidingWindowRateLimiter:
    """Sliding-window request rate limiter."""

    def __init__(self) -> None:
        # Maps (client_key, bucket_name) -> deque of request timestamps
        self._records: Dict[str, deque] = defaultdict(deque)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Check if client key exceeded max_requests in window_seconds.
        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds
        dq = self._records[key]

        # Purge old timestamps
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= max_requests:
            oldest = dq[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return True, retry_after

        dq.append(now)
        return False, 0

    def cleanup(self, max_age_seconds: int = 300) -> None:
        """Periodically purge empty keys to prevent memory leak."""
        now = time.time()
        cutoff = now - max_age_seconds
        keys_to_remove = []
        for key, dq in self._records.items():
            while dq and dq[0] < cutoff:
                dq.popleft()
            if not dq:
                keys_to_remove.append(key)
        for k in keys_to_remove:
            self._records.pop(k, None)


limiter = SlidingWindowRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Extract client IP safely from request headers or socket."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Get leftmost client IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def rate_limit(max_requests: int, window_seconds: int = 60, bucket: str = "default") -> Callable:
    """FastAPI route dependency for rate limiting."""
    async def dependency(request: Request) -> None:
        client_id = get_client_identifier(request)
        rate_key = f"{bucket}:{client_id}"

        limited, retry_after = limiter.is_rate_limited(rate_key, max_requests, window_seconds)
        if limited:
            log.warning(
                "Rate limit exceeded",
                extra={"client": client_id, "bucket": bucket, "limit": max_requests, "retry_after": retry_after},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
