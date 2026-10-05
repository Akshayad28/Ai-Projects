"""Amazon Scraper Engine.

Performs live search queries on Amazon India via Playwright BrowserManager
or PA-API 5.0 (when configured). Detects anti-bot blocks and complies
strictly with access policies (never attempts bypass).
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from urllib.parse import quote_plus

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.amazon.parser import parse_amazon_search_page
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.browser.manager import get_browser_manager

log = get_logger(__name__)


class AmazonScraper:
    """Executes live search requests against Amazon India."""

    def __init__(self) -> None:
        self.browser_manager = get_browser_manager()
        self.settings = get_settings()

    async def scrape_search(self, query: str, max_items: int = 20) -> List[Dict[str, Any]]:
        """Performs live browser navigation to Amazon search page."""
        url = f"https://www.amazon.in/s?k={quote_plus(query)}"
        log.info(f"Navigating to Amazon India: {url}")

        try:
            async with self.browser_manager.create_isolated_page("amazon") as page:
                response = await page.goto(url, wait_until="domcontentloaded")
                
                # Check HTTP status
                if response and response.status in (403, 429, 503):
                    log.warning(f"Amazon responded with HTTP {response.status}")
                    raise ProviderBlocked(f"Amazon refused automated connection (HTTP {response.status})")

                # Verify not blocked / robot verification
                await self.browser_manager.detect_and_assert_not_blocked(page, "amazon")

                # Wait for results or timeout
                try:
                    await page.wait_for_selector(
                        "div[data-component-type='s-search-result'], .s-no-outline, .s-card-container",
                        timeout=8000,
                    )
                except Exception:
                    # Page may have loaded without specific card selector or 0 items
                    pass

                # Get DOM content and parse
                html = await page.content()
                raw_items = parse_amazon_search_page(html, max_items=max_items)
                log.info(f"Amazon scraper parsed {len(raw_items)} items for query '{query}'")
                return raw_items

        except (ProviderBlocked, ProviderTimeout):
            raise
        except Exception as exc:
            log.warning(f"Amazon scraper encounter: {exc}")
            raise ProviderUnavailable(f"Amazon scraping error: {exc}") from exc
