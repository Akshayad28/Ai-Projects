"""Firecrawl Provider Package.

Provides universal web discovery and structured product extraction
using the official Firecrawl API.
"""
from __future__ import annotations

from app.providers.firecrawl.provider import FirecrawlProvider
from app.providers.firecrawl.exceptions import (
    FirecrawlAPIError,
    FirecrawlAuthError,
    FirecrawlBlockedError,
    FirecrawlException,
    FirecrawlRateLimitError,
    FirecrawlTimeoutError,
)
from app.providers.firecrawl.schemas import (
    AttributeItem,
    FirecrawlDiagnostics,
    FirecrawlExtractedProduct,
    FirecrawlSearchResultItem,
    URLClassification,
)

__all__ = [
    "FirecrawlProvider",
    "FirecrawlException",
    "FirecrawlAuthError",
    "FirecrawlAPIError",
    "FirecrawlTimeoutError",
    "FirecrawlRateLimitError",
    "FirecrawlBlockedError",
    "AttributeItem",
    "FirecrawlExtractedProduct",
    "FirecrawlSearchResultItem",
    "URLClassification",
    "FirecrawlDiagnostics",
]
