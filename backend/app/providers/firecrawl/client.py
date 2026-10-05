"""Firecrawl Official API Client Wrapper.

Wraps the official Firecrawl Python SDK (AsyncV1FirecrawlApp) with resilience,
timeouts, rate limits, credit usage monitoring, and ShopBuddy exception translation.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
import aiohttp

from firecrawl import AsyncV1FirecrawlApp

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.firecrawl.exceptions import (
    FirecrawlAPIError,
    FirecrawlAuthError,
    FirecrawlBlockedError,
    FirecrawlRateLimitError,
    FirecrawlTimeoutError,
)
from app.providers.firecrawl.rate_limiter import FirecrawlRateLimiter

log = get_logger(__name__)


class FirecrawlClient:
    """Async client wrapper for official Firecrawl API operations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        concurrency: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.firecrawl_api_key
        self.timeout_seconds = timeout_seconds or settings.firecrawl_request_timeout_seconds
        self.concurrency = concurrency or settings.firecrawl_concurrency
        self.rate_limiter = FirecrawlRateLimiter(max_concurrency=self.concurrency, requests_per_second=5.0)

        self._app: Optional[AsyncV1FirecrawlApp] = None
        if self.api_key:
            try:
                self._app = AsyncV1FirecrawlApp(api_key=self.api_key)
            except Exception as e:
                log.warning(f"Failed to initialize FirecrawlApp: {e}")
                self._app = None

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid API key is present."""
        return bool(self.api_key and self.api_key.strip())

    async def search(
        self,
        query: str,
        limit: int = 20,
        country: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Executes a web search via Firecrawl discovery."""
        if not self.is_configured or self._app is None:
            raise FirecrawlAuthError("Firecrawl API key is missing or not configured.")

        timeout_ms = int(self.timeout_seconds * 1000)

        async with self.rate_limiter:
            try:
                res = await asyncio.wait_for(
                    self._app.search(
                        query=query,
                        limit=limit,
                        country=country.lower() if country else None,
                        lang=lang or "en",
                        timeout=timeout_ms,
                    ),
                    timeout=self.timeout_seconds,
                )

                if isinstance(res, dict):
                    if not res.get("success", True):
                        err_msg = res.get("error", "Unknown search error")
                        raise FirecrawlAPIError(f"Firecrawl search error: {err_msg}")
                    return res.get("data", []) or []

                # Handle object response if returned by newer SDK versions
                data = getattr(res, "data", None)
                if isinstance(data, list):
                    return data
                return []

            except asyncio.TimeoutError as exc:
                raise FirecrawlTimeoutError(f"Firecrawl search timed out after {self.timeout_seconds}s for query '{query}'") from exc
            except aiohttp.ClientResponseError as exc:
                if exc.status == 401 or exc.status == 403:
                    raise FirecrawlAuthError(f"Firecrawl authentication failed: HTTP {exc.status}") from exc
                elif exc.status == 429:
                    raise FirecrawlRateLimitError("Firecrawl rate limit exceeded or credits exhausted.") from exc
                elif exc.status in (403, 503):
                    raise FirecrawlBlockedError(f"Firecrawl request blocked: HTTP {exc.status}") from exc
                raise FirecrawlAPIError(f"Firecrawl HTTP error {exc.status}: {exc.message}") from exc
            except (FirecrawlTimeoutError, FirecrawlAuthError, FirecrawlRateLimitError, FirecrawlBlockedError, FirecrawlAPIError):
                raise
            except Exception as exc:
                err_str = str(exc).lower()
                if "429" in err_str or "rate limit" in err_str:
                    raise FirecrawlRateLimitError(f"Firecrawl rate limited: {exc}") from exc
                if "timeout" in err_str:
                    raise FirecrawlTimeoutError(f"Firecrawl timeout: {exc}") from exc
                if "unauthorized" in err_str or "invalid api key" in err_str:
                    raise FirecrawlAuthError(f"Firecrawl auth error: {exc}") from exc
                raise FirecrawlAPIError(f"Firecrawl search exception: {exc}") from exc

    async def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        json_options: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Scrapes a URL via Firecrawl with structured extraction options."""
        if not self.is_configured or self._app is None:
            raise FirecrawlAuthError("Firecrawl API key is missing or not configured.")

        formats = formats or ["markdown", "html", "json"]
        timeout_ms = int(self.timeout_seconds * 1000)

        async with self.rate_limiter:
            try:
                kwargs: Dict[str, Any] = {
                    "formats": formats,
                    "timeout": timeout_ms,
                    "only_main_content": True,
                }
                if json_options and "json" in formats:
                    kwargs["json_options"] = json_options

                res = await asyncio.wait_for(
                    self._app.scrape_url(url, **kwargs),
                    timeout=self.timeout_seconds,
                )
                return res

            except asyncio.TimeoutError as exc:
                raise FirecrawlTimeoutError(f"Firecrawl scrape timed out after {self.timeout_seconds}s for URL '{url}'") from exc
            except aiohttp.ClientResponseError as exc:
                if exc.status == 401 or exc.status == 403:
                    raise FirecrawlAuthError(f"Firecrawl authentication failed: HTTP {exc.status}") from exc
                elif exc.status == 429:
                    raise FirecrawlRateLimitError("Firecrawl rate limit exceeded or credits exhausted.") from exc
                elif exc.status in (403, 503):
                    raise FirecrawlBlockedError(f"Firecrawl scrape blocked by target: HTTP {exc.status}") from exc
                raise FirecrawlAPIError(f"Firecrawl HTTP error {exc.status}: {exc.message}") from exc
            except (FirecrawlTimeoutError, FirecrawlAuthError, FirecrawlRateLimitError, FirecrawlBlockedError, FirecrawlAPIError):
                raise
            except Exception as exc:
                err_str = str(exc).lower()
                if "429" in err_str or "rate limit" in err_str:
                    raise FirecrawlRateLimitError(f"Firecrawl rate limited: {exc}") from exc
                if "timeout" in err_str:
                    raise FirecrawlTimeoutError(f"Firecrawl timeout: {exc}") from exc
                if "unauthorized" in err_str or "invalid api key" in err_str:
                    raise FirecrawlAuthError(f"Firecrawl auth error: {exc}") from exc
                raise FirecrawlAPIError(f"Firecrawl scrape exception: {exc}") from exc
