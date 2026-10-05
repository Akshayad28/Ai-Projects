"""Provider Exceptions."""
from __future__ import annotations


class ProviderError(Exception):
    """Base exception for provider failures."""
    pass


class ProviderTimeout(ProviderError):
    """Provider timed out during search or item fetch."""
    pass


class ProviderUnavailable(ProviderError):
    """Provider service is down, unreachable, or not configured."""
    pass


class ProviderBlocked(ProviderError):
    """Provider returned CAPTCHA, robot check, or access denial.
    Per compliance rules, ShopBuddy NEVER attempts to bypass anti-bot controls.
    """
    pass


class ProviderRateLimited(ProviderError):
    """Provider rate limit reached. Backoff requested."""
    pass


class ProviderParseError(ProviderError):
    """Provider HTML or API response structure changed and failed to parse."""
    pass


class ProviderDataError(ProviderError):
    """Data integrity issue in provider response."""
    pass
