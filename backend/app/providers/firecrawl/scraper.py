"""Firecrawl Web Scraper and Extraction Orchestrator.

Manages concurrent scraping of candidate product URLs, multi-layer extraction
(JSON-LD, OpenGraph, JSON Schema), data validation, and cache management.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.providers.firecrawl.cache import FirecrawlCache
from app.providers.firecrawl.client import FirecrawlClient
from app.providers.firecrawl.extractor import (
    FIRECRAWL_EXTRACTION_PROMPT,
    FIRECRAWL_PRODUCT_SCHEMA,
    extract_json_ld,
    extract_opengraph_metadata,
    merge_extracted_layers,
    parse_json_ld_product,
)
from app.providers.firecrawl.schemas import FirecrawlExtractedProduct
from app.providers.firecrawl.validators import validate_extracted_product

log = get_logger(__name__)


class FirecrawlScraper:
    """Performs concurrent page scraping and structured extraction."""

    def __init__(self, client: FirecrawlClient, cache: FirecrawlCache) -> None:
        self.client = client
        self.cache = cache

    async def scrape_single_url(
        self,
        url: str,
    ) -> Tuple[Optional[FirecrawlExtractedProduct], Optional[str]]:
        """Scrapes a single URL and extracts structured product data.

        Returns:
            Tuple of (extracted_product, rejection_reason_if_any)
        """
        cache_key = self.cache.hash_scrape_key(url)
        cached_data = await self.cache.get(cache_key)

        html_content = ""
        sdk_json = None
        metadata = {}

        if cached_data is not None and isinstance(cached_data, dict):
            html_content = cached_data.get("html", "")
            sdk_json = cached_data.get("json", None)
            metadata = cached_data.get("metadata", {})
            log.debug(f"[FIRECRAWL] Scrape cache HIT for URL: {url}")
        else:
            try:
                res = await self.client.scrape_url(
                    url=url,
                    formats=["markdown", "html", "json"],
                    json_options={
                        "schema": FIRECRAWL_PRODUCT_SCHEMA,
                        "prompt": FIRECRAWL_EXTRACTION_PROMPT,
                    },
                )

                # Extract attributes from Firecrawl response
                html_content = getattr(res, "html", "") or ""
                sdk_json = getattr(res, "json_field", None) or getattr(res, "extract", None)
                metadata = getattr(res, "metadata", {}) or {}

                # Cache raw scrape response for TTL
                await self.cache.set(
                    cache_key,
                    {
                        "html": html_content,
                        "json": sdk_json,
                        "metadata": metadata,
                    },
                )
            except Exception as exc:
                log.warning(f"[FIRECRAWL] Failed to scrape {url}: {exc}")
                return None, f"Scrape error: {exc}"

        # 1. Extract JSON-LD (Schema.org Product)
        json_ld_raw = extract_json_ld(html_content)
        json_ld_prod = parse_json_ld_product(json_ld_raw) if json_ld_raw else None

        # 2. Extract OpenGraph and HTML meta tags
        og_meta = extract_opengraph_metadata(html_content)

        # 3. Layer and merge
        merged = merge_extracted_layers(
            json_ld_prod=json_ld_prod,
            og_meta=og_meta,
            sdk_json=sdk_json if isinstance(sdk_json, dict) else None,
            source_url=url,
        )

        # 4. Validate extracted product
        is_valid, reason = validate_extracted_product(merged)
        if not is_valid:
            log.debug(f"[FIRECRAWL] Rejected extracted product from {url}: {reason}")
            return None, reason

        return merged, None

    async def scrape_candidate_urls(
        self,
        urls: List[str],
        max_pages: int = 10,
    ) -> Tuple[List[FirecrawlExtractedProduct], int, int]:
        """Scrapes multiple product URLs concurrently up to max_pages.

        Returns:
            Tuple of (valid_products, total_scraped_count, rejected_count)
        """
        urls_to_scrape = urls[:max_pages]
        if not urls_to_scrape:
            return [], 0, 0

        log.info(f"[FIRECRAWL] Concurrently scraping {len(urls_to_scrape)} product pages...")

        async def _scrape_staggered(u: str, delay: float):
            if delay > 0:
                await asyncio.sleep(delay)
            return await self.scrape_single_url(u)

        tasks = [_scrape_staggered(u, i * 0.3) for i, u in enumerate(urls_to_scrape)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_products: List[FirecrawlExtractedProduct] = []
        rejected_count = 0
        scraped_count = 0

        for r in results:
            if isinstance(r, Exception):
                rejected_count += 1
                continue
            scraped_count += 1
            prod, reason = r
            if prod:
                valid_products.append(prod)
            else:
                rejected_count += 1

        log.info(
            f"[FIRECRAWL] Scraping complete: {scraped_count} pages scraped, "
            f"{len(valid_products)} products validated, {rejected_count} rejected"
        )

        return valid_products, scraped_count, rejected_count
