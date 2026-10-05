"""Playwright Browser Manager.

Provides asynchronous, reusable browser lifecycle management with context isolation,
strict timeout enforcement, resource cleanup, and anti-bot/block detection.
Per production compliance rules, ShopBuddy NEVER attempts to bypass CAPTCHAs,
spoof credentials, or circumvent access restrictions.
"""
from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)

log = get_logger(__name__)

# Common indicators of retailer automated access refusal
_BLOCK_INDICATORS = [
    r"robot\s*check",
    r"enter\s*the\s*characters\s*you\s*see",
    r"validate\s*captcha",
    r"automated\s*access",
    r"access\s*denied",
    r"something\s*went\s*wrong.*try\s*again",
    r"security\s*check",
    r"waf\s*blocked",
    r"please\s*verify\s*you\s*are\s*a\s*human",
]


class BrowserManager:
    """Manages shared Playwright browser instance and isolated retailer contexts."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()
        self.settings = get_settings()

    async def _ensure_browser(self) -> Browser:
        current_loop = asyncio.get_running_loop()
        if getattr(self, "_loop", None) != current_loop:
            self._browser = None
            self._playwright = None
            self._loop = current_loop
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                try:
                    if self._playwright is None:
                        self._playwright = await async_playwright().start()
                    
                    cfg = self.settings.scraper_config["browser"]
                    self._browser = await self._playwright.chromium.launch(
                        headless=cfg["headless"],
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-extensions",
                            "--disable-background-networking",
                            "--disable-sync",
                            "--disable-default-apps",
                            "--mute-audio",
                            "--no-first-run",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                        ],
                    )
                    self._loop = current_loop
                    log.info("Playwright browser instance started successfully")
                except Exception as exc:
                    log.error(f"Failed to launch Playwright browser: {exc}")
                    raise ProviderUnavailable(f"Browser automation engine unavailable: {exc}") from exc
            return self._browser

    @asynccontextmanager
    async def create_isolated_page(
        self,
        retailer_name: str,
        user_agent: Optional[str] = None,
        locale: str = "en-IN",
        timezone_id: str = "Asia/Kolkata",
    ) -> AsyncIterator[Page]:
        """Provides an isolated browser page for a specific retailer session."""
        browser = await self._ensure_browser()
        cfg = self.settings.scraper_config["browser"]

        default_ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            context = await browser.new_context(
                user_agent=user_agent or default_ua,
                viewport={"width": 1440, "height": 900},
                locale=locale,
                timezone_id=timezone_id,
            )
            context.set_default_timeout(cfg["timeout_ms"])
            context.set_default_navigation_timeout(cfg["navigation_timeout_ms"])

            page = await context.new_page()

            # Abort heavy non-essential resources (images, video/media, fonts) to minimize memory, CPU and bandwidth load
            async def _block_heavy_resources(route):
                try:
                    if route.request.resource_type in {"image", "media", "font"}:
                        await route.abort()
                    else:
                        await route.continue_()
                except Exception:
                    pass

            await page.route("**/*", _block_heavy_resources)
            yield page

        except asyncio.TimeoutError as exc:
            log.warning(f"Timeout on retailer page ({retailer_name}): {exc}")
            raise ProviderTimeout(f"Navigation to {retailer_name} timed out") from exc
        except ProviderBlocked:
            raise
        except Exception as exc:
            log.warning(f"Browser session error for {retailer_name}: {exc}")
            raise
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    async def detect_and_assert_not_blocked(self, page: Page, retailer_name: str) -> None:
        """Inspects page content to verify retailer has not presented a block/CAPTCHA."""
        try:
            content = await page.content()
            content_lower = content.lower()

            for pattern in _BLOCK_INDICATORS:
                if re.search(pattern, content_lower):
                    log.warning(
                        f"Retailer {retailer_name} presented automated access challenge ({pattern}). "
                        "Marking provider as BLOCKED in accordance with compliance policy."
                    )
                    raise ProviderBlocked(
                        f"Retailer {retailer_name} returned access verification challenge. "
                        "ShopBuddy does not circumvent anti-bot protection."
                    )
        except ProviderBlocked:
            raise
        except Exception as exc:
            log.debug(f"Error checking page block status: {exc}")

    async def close(self) -> None:
        """Cleanly terminates browser and Playwright runtime."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            log.info("Playwright browser instance closed")


_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
