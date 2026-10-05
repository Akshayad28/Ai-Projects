"""Input sanitization and XSS defense utilities."""
from __future__ import annotations

import html
import re
from typing import Optional
from urllib.parse import urlparse

# Pattern matching dangerous HTML tags and script elements
_DANGEROUS_HTML_PATTERN = re.compile(
    r"<\s*(script|iframe|object|embed|applet|meta|link|style|base|svg|form|input)[^>]*>.*?</\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_GENERIC_HTML_TAGS = re.compile(r"<[^>]+>")

# Pattern for javascript:, data:, vbscript: URIs
_DANGEROUS_URI_SCHEMES = re.compile(
    r"^\s*(javascript|data|vbscript|file):",
    re.IGNORECASE,
)

# Control characters except newline, tab, carriage return
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: Optional[str], max_length: int = 500) -> str:
    """Sanitize freeform user text to prevent XSS and control-character injection."""
    if not text:
        return ""

    # Remove null bytes and dangerous control chars
    clean = _CONTROL_CHARS.sub("", text)

    # Strip dangerous executable HTML containers
    clean = _DANGEROUS_HTML_PATTERN.sub("", clean)

    # Strip any remaining HTML tags
    clean = _GENERIC_HTML_TAGS.sub("", clean)

    # Unescape HTML entities then re-escape special characters for safe output
    clean = html.escape(clean.strip())

    # Limit length
    if len(clean) > max_length:
        clean = clean[:max_length]

    return clean


def sanitize_query(query: Optional[str], max_length: int = 300) -> str:
    """Sanitize search query strings."""
    if not query:
        return ""
    # Strip dangerous HTML and control chars
    clean = _CONTROL_CHARS.sub("", query)
    clean = _DANGEROUS_HTML_PATTERN.sub("", clean)
    clean = _GENERIC_HTML_TAGS.sub("", clean)
    clean = clean.strip()
    return clean[:max_length]


def is_safe_url(url: Optional[str]) -> bool:
    """Verify that an external or affiliate URL uses http or https, avoiding javascript/data URLs."""
    if not url:
        return False
    clean_url = url.strip()
    if _DANGEROUS_URI_SCHEMES.search(clean_url):
        return False
    try:
        parsed = urlparse(clean_url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False
