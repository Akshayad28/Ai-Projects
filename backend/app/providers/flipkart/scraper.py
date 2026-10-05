"""Flipkart Scraper Engine.

Performs live search queries on Flipkart India using Playwright BrowserManager.
Strictly respects anti-bot protections and marks provider BLOCKED if challenged.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from urllib.parse import quote_plus

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.browser.manager import get_browser_manager
from app.providers.flipkart.parser import parse_flipkart_search_page

log = get_logger(__name__)


class FlipkartScraper:
    """Executes live search requests against Flipkart India."""

    def __init__(self) -> None:
        self.browser_manager = get_browser_manager()
        self.settings = get_settings()

    async def scrape_search(self, query: str, max_items: int = 20) -> List[Dict[str, Any]]:
        """Performs live browser navigation to Flipkart search page."""
        url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
        log.info(f"Navigating to Flipkart India: {url}")

        try:
            async with self.browser_manager.create_isolated_page("flipkart") as page:
                response = await page.goto(url, wait_until="domcontentloaded")

                # Check HTTP status
                if response and response.status in (403, 429, 503):
                    log.warning(f"Flipkart responded with HTTP {response.status}")
                    raise ProviderBlocked(f"Flipkart refused automated connection (HTTP {response.status})")

                # Verify not blocked / robot verification
                await self.browser_manager.detect_and_assert_not_blocked(page, "flipkart")

                # Wait for search container
                try:
                    await page.wait_for_selector("div[data-id], ._1AtVbE, .KzDlHZ", timeout=8000)
                except Exception:
                    pass

                # Get DOM content and parse
                html = await page.content()
                raw_items = parse_flipkart_search_page(html, max_items=max_items)
                log.info(f"Flipkart scraper parsed {len(raw_items)} items for query '{query}'")
                return raw_items

        except (ProviderBlocked, ProviderTimeout):
            raise
        except Exception as exc:
            log.warning(f"Flipkart scraper encounter: {exc}")
            raise ProviderUnavailable(f"Flipkart scraping error: {exc}") from exc
