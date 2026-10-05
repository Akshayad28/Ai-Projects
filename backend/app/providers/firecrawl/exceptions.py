"""Firecrawl Provider Exceptions.

Maps internal Firecrawl SDK errors and API failure modes to canonical
ShopBuddy provider exceptions so failure isolation and circuit breaking operate cleanly.
"""
from __future__ import annotations

from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderDataError,
    ProviderError,
    ProviderParseError,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)


class FirecrawlException(ProviderError):
    """Base exception for Firecrawl provider errors."""
    pass


class FirecrawlAuthError(ProviderUnavailable, FirecrawlException):
    """Raised when Firecrawl API key is missing or invalid."""
    pass


class FirecrawlAPIError(FirecrawlException):
    """Raised when Firecrawl API returns an HTTP or payload error."""
    pass


class FirecrawlTimeoutError(ProviderTimeout, FirecrawlException):
    """Raised when a search or scrape operation exceeds the configured timeout."""
    pass


class FirecrawlRateLimitError(ProviderRateLimited, FirecrawlException):
    """Raised when Firecrawl rate limits or credits are exhausted (HTTP 429)."""
    pass


class FirecrawlBlockedError(ProviderBlocked, FirecrawlException):
    """Raised when the target website or Firecrawl detects a block or anti-bot challenge."""
    pass


class FirecrawlExtractionError(ProviderParseError, FirecrawlException):
    """Raised when structured JSON extraction or JSON-LD parsing fails."""
    pass


class FirecrawlValidationError(ProviderDataError, FirecrawlException):
    """Raised when extracted product data fails fundamental validation checks."""
    pass
