"""Playwright Google Shopping Scraper.

Performs live search queries on Google Shopping via Playwright BrowserManager.
Maintains context isolation, checks for automated access challenges, enforces circuit breaking,
throttles requests with token-bucket rate limiting, and uses modular layout parsers.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.browser.manager import get_browser_manager
from app.providers.google_scraper.health import (
    GoogleCircuitBreaker,
    GoogleRateLimiter,
    detect_google_block,
)
from app.providers.google_scraper.models import ExtractionHealth, GoogleScrapedItem
from app.providers.google_scraper.parser.dispatcher import GoogleParserDispatcher

log = get_logger(__name__)

# Country to Google domain & locale mappings
COUNTRY_DOMAIN_CONFIG = {
    "IN": {"domain": "www.google.co.in", "hl": "en", "gl": "in", "locale": "en-IN", "tz": "Asia/Kolkata"},
    "US": {"domain": "www.google.com", "hl": "en", "gl": "us", "locale": "en-US", "tz": "America/New_York"},
    "GB": {"domain": "www.google.co.uk", "hl": "en", "gl": "gb", "locale": "en-GB", "tz": "Europe/London"},
    "DE": {"domain": "www.google.de", "hl": "de", "gl": "de", "locale": "de-DE", "tz": "Europe/Berlin"},
    "AE": {"domain": "www.google.ae", "hl": "en", "gl": "ae", "locale": "en-AE", "tz": "Asia/Dubai"},
    "SG": {"domain": "www.google.com.sg", "hl": "en", "gl": "sg", "locale": "en-SG", "tz": "Asia/Singapore"},
}


class GoogleScraper:
    """Executes live browser-based Google Shopping searches with resilience."""

    def __init__(self) -> None:
        self.browser_manager = get_browser_manager()
        self.settings = get_settings()
        self.dispatcher = GoogleParserDispatcher()
        self.circuit_breaker = GoogleCircuitBreaker(
            cooldown_seconds=getattr(self.settings, "google_circuit_breaker_cooldown_seconds", 900.0)
        )
        self.rate_limiter = GoogleRateLimiter(
            requests_per_second=getattr(self.settings, "google_requests_per_second", 1.0)
        )
        self.last_health: Optional[ExtractionHealth] = None

    async def scrape_search(
        self,
        query: str,
        country: str = "IN",
        currency: str = "INR",
        language: str = "en",
        max_results: int = 20,
    ) -> List[GoogleScrapedItem]:
        """Navigates to Google Shopping and extracts visible product listings."""
        country_code = (country or self.settings.google_scraper_country or "IN").upper()
        cfg = COUNTRY_DOMAIN_CONFIG.get(country_code, COUNTRY_DOMAIN_CONFIG["IN"])
        domain = cfg["domain"]
        gl = cfg["gl"]
        hl = language or cfg["hl"]

        # 1. Circuit Breaker Check
        if not await self.circuit_breaker.can_request():
            reason = self.circuit_breaker.last_block_reason or "PREVIOUS_BLOCK"
            log.info(
                f"\nGOOGLE SEARCH\n"
                f'query="{query}"\n'
                f'country="{country_code}"\n'
                f'language="{hl}"\n'
                f'requested_url="https://{domain}/search?q={query}"\n'
                f'final_url="N/A"\n'
                f'page_title="N/A"\n'
                f"navigation_success=false\n"
                f"timeout=false\n"
                f"blocked=true\n"
                f'layout="UNKNOWN"\n'
                f"cards_found=0\n"
                f"candidates=0\n"
                f"parsed_products=0\n"
                f"rejected_products=0\n"
                f'rejection_reasons=["Circuit breaker OPEN ({reason})"]'
            )
            log.warning(
                f"Google scraper request dropped: circuit breaker is OPEN (reason='{reason}', cooldown={self.circuit_breaker.cooldown_seconds}s)"
            )
            raise ProviderBlocked(f"Google scraper circuit breaker is OPEN (blocked by {reason})")

        # 2. Check Cache Layer
        norm_query = " ".join(query.strip().lower().split())
        cache_key = f"google_scraper:{country_code}:{hl}:{currency}:{norm_query}"
        cache = get_cache()
        cached = await cache.get(cache_key)
        if cached and isinstance(cached, list):
            log.info(
                f"Google scraper cache HIT for '{query}' [{country_code}]",
                extra={"query": query, "country": country_code, "cached_count": len(cached)},
            )
            try:
                return [GoogleScrapedItem.model_validate(item) for item in cached]
            except Exception as e:
                log.debug(f"Failed to deserialize cached Google scraper items: {e}")

        # 3. Rate Limiter Throttle
        await self.rate_limiter.acquire()

        # 4. Build Search URL with proper URL encoding
        from urllib.parse import urlencode
        params = {"q": query.strip(), "tbm": "shop", "gl": gl, "hl": hl}
        url = f"https://{domain}/search?{urlencode(params)}"
        log.info(
            f"Google search started: query='{query}', country='{country_code}', url='{url}'",
            extra={"query": query, "country": country_code, "domain": domain},
        )

        # 5. Execute with Bounded Retries (zero retries on CAPTCHA / block)
        max_retries = getattr(self.settings, "google_max_retries", 1)
        nav_timeout_ms = int(self.settings.google_scraper_timeout_seconds * 1000)

        for attempt in range(max_retries + 1):
            try:
                async with self.browser_manager.create_isolated_page(
                    "google",
                    locale=cfg.get("locale", "en-IN"),
                    timezone_id=cfg.get("tz", "Asia/Kolkata"),
                ) as page:
                    page_title = ""
                    try:
                        response = await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=nav_timeout_ms,
                        )
                        page_title = await page.title()
                    except asyncio.TimeoutError as exc:
                        log.info(
                            f"\nGOOGLE SEARCH\n"
                            f'query="{query}"\n'
                            f'country="{country_code}"\n'
                            f'language="{hl}"\n'
                            f'requested_url="{url}"\n'
                            f'final_url="{page.url if page else "N/A"}"\n'
                            f'page_title="{page_title}"\n'
                            f"navigation_success=false\n"
                            f"timeout=true\n"
                            f"blocked=false\n"
                            f'layout="UNKNOWN"\n'
                            f"cards_found=0\n"
                            f"candidates=0\n"
                            f"parsed_products=0\n"
                            f"rejected_products=0\n"
                            f'rejection_reasons=["Navigation timeout after {self.settings.google_scraper_timeout_seconds}s"]'
                        )
                        log.warning(f"Google scraper navigation timed out (attempt {attempt+1}/{max_retries+1}): {exc}")
                        if attempt < max_retries:
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        raise ProviderTimeout(f"Google navigation timed out after {self.settings.google_scraper_timeout_seconds}s") from exc

                    current_url = page.url
                    # Check HTTP status for blocking
                    status_code = response.status if response else 200
                    block_reason = detect_google_block(status_code=status_code, current_url=current_url)
                    if block_reason:
                        await self.circuit_breaker.record_block(block_reason)
                        log.info(
                            f"\nGOOGLE SEARCH\n"
                            f'query="{query}"\n'
                            f'country="{country_code}"\n'
                            f'language="{hl}"\n'
                            f'requested_url="{url}"\n'
                            f'final_url="{current_url}"\n'
                            f'page_title="{page_title}"\n'
                            f"navigation_success=true\n"
                            f"timeout=false\n"
                            f"blocked=true\n"
                            f'layout="UNKNOWN"\n'
                            f"cards_found=0\n"
                            f"candidates=0\n"
                            f"parsed_products=0\n"
                            f"rejected_products=0\n"
                            f'rejection_reasons=["Google block detected ({block_reason})"]'
                        )
                        raise ProviderBlocked(f"Google access restricted ({block_reason})")

                    # Handle EU / Global Cookie Consent dialog
                    try:
                        consent_button = page.locator(
                            "button:has-text('Accept all'), button:has-text('Alle akzeptieren'), button:has-text('I agree'), button:has-text('Accept')"
                        )
                        if await consent_button.count() > 0 and await consent_button.first.is_visible():
                            await consent_button.first.click(timeout=2000)
                            await page.wait_for_load_state("domcontentloaded")
                    except Exception:
                        pass

                    # Wait briefly for product card elements
                    try:
                        await page.wait_for_selector(
                            "div.sh-dgr__grid-result, div.sh-dgr__content, div.pla-unit, div.mnr-c, div[data-docid]",
                            timeout=5000,
                        )
                    except Exception:
                        pass

                    # Retrieve rendered HTML content
                    html_content = await page.content()

                    # Block detection on HTML content
                    block_reason = detect_google_block(html_content=html_content, current_url=page.url)
                    if block_reason:
                        await self.circuit_breaker.record_block(block_reason)
                        log.info(
                            f"\nGOOGLE SEARCH\n"
                            f'query="{query}"\n'
                            f'country="{country_code}"\n'
                            f'language="{hl}"\n'
                            f'requested_url="{url}"\n'
                            f'final_url="{page.url}"\n'
                            f'page_title="{page_title}"\n'
                            f"navigation_success=true\n"
                            f"timeout=false\n"
                            f"blocked=true\n"
                            f'layout="UNKNOWN"\n'
                            f"cards_found=0\n"
                            f"candidates=0\n"
                            f"parsed_products=0\n"
                            f"rejected_products=0\n"
                            f'rejection_reasons=["Google content block detected ({block_reason})"]'
                        )
                        raise ProviderBlocked(f"Google access restricted ({block_reason})")

                    # Dispatch to modular layout parser
                    items, health = self.dispatcher.parse(
                        html_content=html_content,
                        country=country_code,
                        currency=currency,
                        max_results=max_results,
                    )
                    self.last_health = health

                    # Record success in circuit breaker
                    await self.circuit_breaker.record_success()

                    log.info(
                        f"\nGOOGLE SEARCH\n"
                        f'query="{query}"\n'
                        f'country="{country_code}"\n'
                        f'language="{hl}"\n'
                        f'requested_url="{url}"\n'
                        f'final_url="{page.url}"\n'
                        f'page_title="{page_title}"\n'
                        f"navigation_success=true\n"
                        f"timeout=false\n"
                        f"blocked=false\n"
                        f'layout="{health.layout.value}"\n'
                        f"cards_found={health.cards_found}\n"
                        f"detected={health.products_detected}\n"
                        f"parsed_products={len(items)}\n"
                        f"errors={len(health.extraction_errors)}"

                    )

                    # Store in cache
                    if items:
                        await cache.set(
                            cache_key,
                            [item.model_dump() for item in items],
                            ttl=self.settings.google_scraper_cache_ttl_seconds,
                        )

                    return items

            except ProviderBlocked:
                # NON-RETRYABLE: Stop immediately, do not hammer Google
                raise
            except ProviderTimeout:
                if attempt >= max_retries:
                    raise
            except Exception as exc:
                log.warning(f"Google scraper attempt {attempt+1} failed: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise ProviderUnavailable(f"Google scraper error: {exc}") from exc

        return []

    def get_health_telemetry(self) -> Dict[str, Any]:
        """Returns runtime circuit breaker and layout health diagnostics."""
        telemetry = {
            "circuit_breaker": self.circuit_breaker.to_dict(),
            "rate_limiter": {"requests_per_second": self.rate_limiter.rate},
        }
        if self.last_health:
            telemetry["last_extraction_health"] = self.last_health.to_summary_dict()
        return telemetry
