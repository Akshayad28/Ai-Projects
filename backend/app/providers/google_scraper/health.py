"""Health, Block Detection, Circuit Breaker, and Rate Limiter for Google Scraper.

Ensures zero retries on CAPTCHA, enforces provider-level circuit breaking,
and provides async-safe rate limiting without bypassing access controls.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.providers.google_scraper.models import CircuitState

log = get_logger(__name__)

# Signatures indicating Google anti-bot / CAPTCHA challenge
_BLOCK_PATTERNS = [
    (r"unusual traffic from your computer network", "UNUSUAL_TRAFFIC"),
    (r"our systems have detected unusual traffic", "UNUSUAL_TRAFFIC"),
    (r"recaptcha", "CAPTCHA_DETECTED"),
    (r"g-recaptcha", "CAPTCHA_DETECTED"),
    (r"verify you(?:'re| are) not a robot", "BOT_VERIFICATION"),
    (r"google\.com/sorry", "GOOGLE_SORRY_PAGE"),
    (r"please solve the challenge below", "CAPTCHA_CHALLENGE"),
    (r"bot detection", "BOT_DETECTION"),
    (r"suspicious activity", "SUSPICIOUS_ACTIVITY"),
]


def detect_google_block(
    html_content: Optional[str] = None,
    status_code: Optional[int] = None,
    current_url: Optional[str] = None,
) -> Optional[str]:
    """Detects whether Google has presented a CAPTCHA or access restriction page.

    Returns the block reason code (e.g. 'CAPTCHA_DETECTED', 'HTTP_429') or None if normal.
    """
    # 1. HTTP Status Code Checks
    if status_code in (429, 403, 503):
        return f"HTTP_{status_code}"

    # 2. URL Path Checks
    if current_url and ("sorry/index" in current_url or "google.com/sorry" in current_url):
        return "GOOGLE_SORRY_REDIRECT"

    # 3. HTML Content Pattern Matching
    if html_content:
        content_lower = html_content.lower()

        # Check for Google "Sorry" page title
        if "<title>sorry...</title>" in content_lower or "<title>sorry..." in content_lower:
            return "GOOGLE_SORRY_PAGE"

        for pattern, reason in _BLOCK_PATTERNS:
            if re.search(pattern, content_lower):
                return reason

    return None


class GoogleCircuitBreaker:
    """Provider-level circuit breaker with CLOSED, OPEN, and HALF_OPEN states."""

    def __init__(self, cooldown_seconds: float = 900.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.state: CircuitState = CircuitState.CLOSED
        self.opened_at: Optional[float] = None
        self.last_block_reason: Optional[str] = None
        self.total_blocks: int = 0
        self.total_requests: int = 0
        self.total_successes: int = 0
        self._lock = asyncio.Lock()

    async def can_request(self) -> bool:
        """Determines if a request can proceed based on current circuit breaker state."""
        async with self._lock:
            self.total_requests += 1

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                now = time.time()
                if self.opened_at and (now - self.opened_at) >= self.cooldown_seconds:
                    log.info(
                        f"Google circuit breaker cooldown ({self.cooldown_seconds}s) elapsed. Moving to HALF_OPEN."
                    )
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                # In HALF_OPEN, allow probe request
                return True

            return False

    async def record_success(self) -> None:
        """Records a successful request, resetting circuit breaker to CLOSED."""
        async with self._lock:
            self.total_successes += 1
            if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                log.info("Google probe request succeeded. Closing circuit breaker.")
            self.state = CircuitState.CLOSED
            self.opened_at = None

    async def record_block(self, reason: str) -> None:
        """Records a CAPTCHA/block event, immediately tripping circuit breaker to OPEN."""
        async with self._lock:
            self.total_blocks += 1
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            self.last_block_reason = reason
            log.warning(
                f"Google circuit breaker TRIPPED to OPEN: reason='{reason}', cooldown={self.cooldown_seconds}s"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "opened_at": self.opened_at,
            "cooldown_seconds": self.cooldown_seconds,
            "last_block_reason": self.last_block_reason,
            "total_blocks": self.total_blocks,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
        }


class GoogleRateLimiter:
    """Token-bucket rate limiter for Google scraping requests."""

    def __init__(self, requests_per_second: float = 1.0) -> None:
        self.rate = max(0.1, requests_per_second)
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    async def acquire(self) -> None:
        """Throttles execution to maintain desired requests-per-second rate."""
        min_interval = 1.0 / self.rate
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                delay = min_interval - elapsed
                await asyncio.sleep(delay)
            self._last_request_time = time.monotonic()
