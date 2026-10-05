"""Firecrawl Web Search Discovery.

Generates targeted search queries from user intent, executes web search via Firecrawl,
captures full result provenance, classifies discovered URLs, and filters candidate product URLs.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.providers.firecrawl.cache import FirecrawlCache
from app.providers.firecrawl.client import FirecrawlClient
from app.providers.firecrawl.schemas import (
    FirecrawlSearchResultItem,
    URLClassification,
    utcnow_str,
)
from app.providers.firecrawl.validators import (
    classify_url,
    is_valid_url,
)
from app.schemas.domain import ProviderSearchParams, SearchIntent

log = get_logger(__name__)


class FirecrawlSearcher:
    """Orchestrates web discovery using Firecrawl search."""

    def __init__(self, client: FirecrawlClient, cache: FirecrawlCache) -> None:
        self.client = client
        self.cache = cache

    def generate_search_queries(
        self,
        query: str,
        intent: Optional[SearchIntent] = None,
        country: str = "IN",
        currency: str = "INR",
    ) -> List[str]:
        """Generates 1 primary query and optionally 1-2 refined queries when appropriate.

        Never requires category resolution. Deduplicates queries.
        """
        queries: List[str] = []
        seen: Set[str] = set()

        def _add(q: str) -> None:
            norm = q.strip()
            if norm and norm.lower() not in seen:
                seen.add(norm.lower())
                queries.append(norm)

        # 1. Primary Query: either cleaned provider query or raw query
        primary = (intent.provider_query if intent and intent.provider_query else query).strip()
        _add(primary)

        # 2. Add raw query if different
        if query.strip().lower() != primary.lower():
            _add(query.strip())

        # 3. If budget / price constraints exist and not in query, create a price-bounded query
        if intent and intent.budget and intent.budget.max:
            price_bound = int(intent.budget.max)
            curr_symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
            price_query = f"{primary} under {curr_symbol}{price_bound}"
            _add(price_query)

        # 4. If country specific location helps discovery (e.g. India)
        if country.upper() == "IN" and "india" not in primary.lower():
            _add(f"{primary} India")

        # Limit to max 3 queries total to prevent excess credit usage
        return queries[:3]

    async def execute_discovery(
        self,
        query: str,
        intent: Optional[SearchIntent] = None,
        country: str = "IN",
        currency: str = "INR",
        max_results: int = 20,
    ) -> Tuple[List[FirecrawlSearchResultItem], List[str]]:
        """Executes multi-query Firecrawl search discovery.

        Returns:
            Tuple of (all_search_items_with_provenance, ranked_product_candidate_urls)
        """
        search_queries = self.generate_search_queries(query, intent, country, currency)
        all_items: List[FirecrawlSearchResultItem] = []
        seen_urls: Set[str] = set()

        log.info(f"[FIRECRAWL] Search started with queries: {search_queries}")

        for q in search_queries:
            cache_key = self.cache.hash_search_key(q, country, currency, max_results)
            cached_res = await self.cache.get(cache_key)

            if cached_res is not None and isinstance(cached_res, list):
                raw_results = cached_res
                log.info(f"[FIRECRAWL] Search cache HIT for query: '{q}' ({len(raw_results)} results)")
            else:
                try:
                    raw_results = await self.client.search(
                        query=q,
                        limit=max_results,
                        country=country,
                    )
                    await self.cache.set(cache_key, raw_results)
                    log.info(f"[FIRECRAWL] Search query '{q}' returned {len(raw_results)} results")
                except Exception as exc:
                    log.warning(f"[FIRECRAWL] Search failed for query '{q}': {exc}")
                    continue

            # Process discovered results
            for idx, item in enumerate(raw_results):
                if not isinstance(item, dict):
                    continue

                item_url = item.get("url") or ""
                if not is_valid_url(item_url) or item_url in seen_urls:
                    continue
                seen_urls.add(item_url)

                title = item.get("title") or ""
                desc = item.get("description") or ""

                classification = classify_url(item_url, title, desc)

                netloc = ""
                try:
                    netloc = urlparse(item_url).netloc
                except Exception:
                    pass

                result_item = FirecrawlSearchResultItem(
                    title=title,
                    url=item_url,
                    description=desc,
                    domain=netloc,
                    position=idx + 1,
                    query=q,
                    classification=classification,
                    fetched_at=utcnow_str(),
                )
                all_items.append(result_item)

            # If primary query returned 10+ results, no need to dispatch remaining refined queries
            if len(all_items) >= 12:
                break

        # Filter candidate product URLs: prioritize product_page classification
        product_urls: List[str] = []
        secondary_urls: List[str] = []

        for item in all_items:
            if item.classification == URLClassification.PRODUCT_PAGE:
                product_urls.append(item.url)
            elif item.classification in (URLClassification.RETAILER_CATEGORY, URLClassification.COMPARISON_PAGE):
                secondary_urls.append(item.url)

        # Strictly prioritize actual product detail pages
        candidate_urls = product_urls if product_urls else secondary_urls

        log.info(
            f"[FIRECRAWL] Discovery complete: {len(all_items)} total web results, "
            f"{len(product_urls)} product candidates, {len(candidate_urls)} selected for scraping"
        )

        return all_items, candidate_urls
