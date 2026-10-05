"""Product Search Orchestrator.

Orchestrates concurrent provider queries across Google Shopping Scraper, Amazon, Flipkart,
eBay, Merchant Feeds, and other configured retail providers.
Isolates provider errors/blocks, normalizes results, merges identical products into canonical entities,
aggregates cross-retailer offers without losing provider attribution, calculates true cost,
computes global recommendation scores, stores price observations, supports full pagination,
and strictly enforces production integrity (NO fabricated data).
"""
from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.amazon.provider import AmazonProvider
from app.providers.base.exceptions import (
    ProviderBlocked,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.providers.base.models import (
    ProviderPrice,
    ProviderProduct,
    SearchQuery,
)
from app.providers.bestbuy import BestBuyProvider
from app.providers.ebay import EbayProvider
from app.providers.firecrawl import FirecrawlProvider
from app.providers.flipkart.provider import FlipkartProvider
from app.providers.google_scraper import GoogleScraperProvider
from app.providers.merchant_feed import MerchantFeedProvider
from app.providers.serp_shopping import SerpShoppingProvider
from app.providers.quick_commerce import (
    BigBasketProvider,
    BlinkitProvider,
    InstamartProvider,
    ZeptoProvider,
)
from app.providers.specialists import (
    CromaProvider,
    IkeaProvider,
    MyntraProvider,
    RelianceDigitalProvider,
)
from app.providers.capabilities import MarketplaceType, ProviderCapabilities, ProviderMetadata
from app.providers.discovery_engine import MarketplaceDiscoveryEngine
from app.services.image_service import ImageExtractionService
from app.services.unit_economics import UnitEconomicsService
from app.services.diagnostics_store import diagnostics_store, SearchDiagnosticsRecord
from app.schemas.domain import (
    Budget,
    Condition,
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    SearchIntent,
)
from app.schemas.search import (
    CanonicalSearchProduct,
    ExtractedQueryIntent,
    PaginationMetadata,
    ProviderExecutionStatus,
    UnifiedSearchResponse,
)
from app.models.product import Product
from app.models.offer import Offer
from app.repositories.product_repository import ProductRepository
from app.repositories.offer_repository import OfferRepository
from app.services.freshness_service import FreshnessService
from app.services.intent_service import IntentService
from app.services.normalization_service import NormalizationService
from app.services.offer_service import OfferService
from app.services.price_service import PriceService
from app.services.product_identity_service import ProductIdentityService
from app.services.recommendation_service import RecommendationService
from app.utils.hashing import hash_query

log = get_logger(__name__)


def raw_product_to_provider_product(raw: RawProduct) -> ProviderProduct:
    """Converts a catalog RawProduct into a standardized ProviderProduct for orchestration."""
    price_amount = None
    currency = "INR"
    original_price = None
    discount = None
    availability = "unknown"
    seller = None

    if raw.offers:
        first_offer = raw.offers[0]
        price_amount = first_offer.price_amount
        currency = first_offer.currency or "INR"
        original_price = first_offer.original_price
        if original_price and price_amount and original_price > price_amount:
            discount = original_price - price_amount
        availability = first_offer.availability
        seller = first_offer.seller_name or raw.provider.capitalize()

    identifiers = {}
    for key, val in [
        ("gtin", raw.gtin),
        ("upc", raw.upc),
        ("ean", raw.ean),
        ("mpn", raw.mpn),
        ("asin", raw.asin),
        ("sku", raw.sku),
    ]:
        if val:
            identifiers[key] = val

    return ProviderProduct(
        provider=raw.provider,
        provider_product_id=raw.external_id,
        title=raw.title,
        url=raw.url,
        image_url=raw.image_urls[0] if raw.image_urls else None,
        image_urls=raw.image_urls,
        brand=raw.brand,
        model=raw.model,
        price=ProviderPrice(
            amount=price_amount,
            currency=currency,
            original_price=original_price,
            discount=discount,
        ),
        rating=raw.rating,
        review_count=raw.review_count,
        availability=availability,
        seller=seller,
        identifiers=identifiers,
        specifications=raw.specs,
        is_demo=raw.is_demo,
    )


class SearchOrchestrator:
    """Coordinates the full end-to-end shopping search pipeline across multiple providers."""

    def __init__(self) -> None:
        self.intent_service = IntentService()
        self.normalization_service = NormalizationService()
        self.identity_service = ProductIdentityService()
        self.offer_service = OfferService()
        self.recommendation_service = RecommendationService()
        self.price_service = PriceService()
        self.freshness_service = FreshnessService()
        self.product_repo = ProductRepository()
        self.settings = get_settings()
        self._browser_semaphore = asyncio.Semaphore(self.settings.scraper_concurrency_providers)

        self.image_service = ImageExtractionService()
        self.discovery_engine = MarketplaceDiscoveryEngine()

        # Configured retail and quick-commerce providers
        self.providers: Dict[str, Any] = {
            "google_scraper": GoogleScraperProvider(),
            "firecrawl": FirecrawlProvider(),
            "amazon": AmazonProvider(),
            "flipkart": FlipkartProvider(),
            "ebay": EbayProvider(),
            "croma": CromaProvider(),
            "reliance_digital": RelianceDigitalProvider(),
            "myntra": MyntraProvider(),
            "ikea": IkeaProvider(),
            "blinkit": BlinkitProvider(),
            "zepto": ZeptoProvider(),
            "instamart": InstamartProvider(),
            "bigbasket": BigBasketProvider(),
            "merchant_feed": MerchantFeedProvider(),
            "serp_shopping": SerpShoppingProvider(),
            "bestbuy": BestBuyProvider(),
        }

        self._setup_discovery_metadata()

    def _setup_discovery_metadata(self) -> None:
        """Configures metadata for dynamic routing across providers."""
        self.discovery_engine.register_metadata(
            "google_scraper",
            ProviderMetadata(name="google_scraper", label="Google Shopping", marketplace_type=MarketplaceType.WEB_DISCOVERY, priority=10),
        )
        self.discovery_engine.register_metadata(
            "firecrawl",
            ProviderMetadata(name="firecrawl", label="Firecrawl Web Discovery", marketplace_type=MarketplaceType.WEB_DISCOVERY, priority=20),
        )
        self.discovery_engine.register_metadata(
            "amazon",
            ProviderMetadata(name="amazon", label="Amazon", marketplace_type=MarketplaceType.GENERAL_MARKETPLACE, priority=30),
        )
        self.discovery_engine.register_metadata(
            "flipkart",
            ProviderMetadata(name="flipkart", label="Flipkart", marketplace_type=MarketplaceType.GENERAL_MARKETPLACE, countries={"IN"}, priority=30),
        )
        self.discovery_engine.register_metadata(
            "ebay",
            ProviderMetadata(name="ebay", label="eBay", marketplace_type=MarketplaceType.GENERAL_MARKETPLACE, priority=40),
        )
        self.discovery_engine.register_metadata(
            "croma",
            ProviderMetadata(name="croma", label="Croma", marketplace_type=MarketplaceType.ELECTRONICS, countries={"IN"}, priority=50),
        )
        self.discovery_engine.register_metadata(
            "reliance_digital",
            ProviderMetadata(name="reliance_digital", label="Reliance Digital", marketplace_type=MarketplaceType.ELECTRONICS, countries={"IN"}, priority=50),
        )
        self.discovery_engine.register_metadata(
            "myntra",
            ProviderMetadata(name="myntra", label="Myntra", marketplace_type=MarketplaceType.FASHION, countries={"IN"}, priority=50),
        )
        self.discovery_engine.register_metadata(
            "ikea",
            ProviderMetadata(name="ikea", label="IKEA", marketplace_type=MarketplaceType.HOME_FURNITURE, countries={"IN"}, priority=50),
        )
        for qc_name, qc_label in [("blinkit", "Blinkit"), ("zepto", "Zepto"), ("instamart", "Swiggy Instamart"), ("bigbasket", "BigBasket")]:
            self.discovery_engine.register_metadata(
                qc_name,
                ProviderMetadata(
                    name=qc_name,
                    label=qc_label,
                    marketplace_type=MarketplaceType.QUICK_COMMERCE,
                    capabilities=ProviderCapabilities(quick_commerce=True, unit_economics=True, location_aware=True),
                    countries={"IN"},
                    priority=25,
                ),
            )

    async def _revalidate_and_cache(
        self,
        raw_query: str,
        country: str = "IN",
        currency: str = "INR",
        sort_by: str = "recommended",
    ) -> None:
        """Background worker to revalidate and freshen cached search results without blocking user requests."""
        try:
            log.info(f"[SWR] Background revalidating search for '{raw_query}'...")
            await self.execute_search(
                raw_query=raw_query,
                country=country,
                currency=currency,
                sort_by=sort_by,
                bypass_cache=True,
            )
            log.info(f"[SWR] Background revalidation completed for '{raw_query}'.")
        except Exception as e:
            log.warning(f"[SWR] Background revalidation failed for '{raw_query}': {e}")

    async def _complete_pending_and_merge(
        self,
        pending: Set[asyncio.Task],
        task_map: Dict[asyncio.Task, str],
        raw_query: str,
        country: str,
        currency: str,
        sort_by: str,
        existing_raw_products: List[ProviderProduct],
        provider_statuses: Dict[str, ProviderExecutionStatus],
    ) -> None:
        """Background worker to complete pending provider scrapes and merge them into the cached canonical products."""
        try:
            done, _ = await asyncio.wait(pending, timeout=25.0)
            new_products: List[ProviderProduct] = []
            for t in done:
                try:
                    name, prods, status = t.result()
                    provider_statuses[name] = status
                    if prods:
                        new_products.extend(prods)
                except Exception as exc:
                    name = task_map.get(t, "unknown")
                    log.warning(f"[BACKGROUND] Provider {name} failed: {exc}")

            if not new_products:
                log.info(f"[BACKGROUND] Pending providers completed with 0 new products for '{raw_query}'.")
                return

            merged_raw = existing_raw_products + new_products
            log.info(f"[BACKGROUND] Merging {len(new_products)} late products (total {len(merged_raw)}) for '{raw_query}'")

            # Cluster and normalize merged products
            clusters = self.identity_service.cluster_products(merged_raw)
            canonical_products = []
            cluster_items = []
            for cluster in clusters:
                primary_prod = cluster[0]
                candidate_imgs = []
                for item in cluster:
                    if getattr(item, "primary_image", None):
                        candidate_imgs.append(item.primary_image)
                    if getattr(item, "image_url", None):
                        candidate_imgs.append(item.image_url)
                    if getattr(item, "image_urls", None):
                        candidate_imgs.extend(item.image_urls)
                best_img, gallery_imgs = self.image_service.select_best_image(candidate_imgs, primary_prod.title)

                canonical_detail = self.normalization_service.normalize_provider_product(
                    primary_prod,
                    category_id="general",
                )
                canonical_detail.image_url = best_img
                canonical_detail.images = ([best_img] + [g for g in gallery_imgs if g != best_img]) if best_img else []
                canonical_detail.image_urls = canonical_detail.images

                offers = [self.offer_service.build_offer(item, canonical_detail.id) for item in cluster]
                price_summary = self.offer_service.summarize_prices(offers)
                rec = self.recommendation_service.evaluate_product(primary_prod)

                has_qc = any(o.is_quick_commerce for o in offers)
                qc_eta = next((o.delivery_estimate for o in offers if o.is_quick_commerce and o.delivery_estimate), None)
                data_coverage = self.recommendation_service.compute_data_coverage_score(primary_prod)

                canonical_detail.offers = offers
                canonical_detail.price_summary = price_summary
                canonical_detail.best_price = price_summary.lowest_price if price_summary else None
                canonical_detail.primary_retailer = offers[0].retailer if offers else None
                canonical_detail.offers_count = len(offers)

                cluster_items.append((cluster, primary_prod, canonical_detail, offers, price_summary, rec, has_qc, qc_eta, None, data_coverage))

                canonical_products.append(
                    CanonicalSearchProduct(
                        id=canonical_detail.id,
                        title=canonical_detail.title,
                        brand=canonical_detail.brand,
                        model=canonical_detail.model,
                        category_id=canonical_detail.category_id,
                        image=canonical_detail.images[0] if canonical_detail.images else None,
                        image_urls=canonical_detail.images,
                        rating=canonical_detail.rating,
                        review_count=canonical_detail.review_count,
                        recommendation=rec,
                        offers=offers,
                        price_summary=price_summary,
                        sources=list({o.retailer for o in offers}),
                        card_attributes=[],
                        freshness_label=self.freshness_service.get_freshness_label(offers[0].fetched_at if offers else None),
                        data_coverage_score=data_coverage,
                        is_quick_commerce=has_qc,
                        quick_commerce_eta=qc_eta,
                        best_unit_price=None,
                    )
                )

            # Sort canonical products
            if sort_by == "price_asc":
                canonical_products.sort(key=lambda x: x.price_summary.lowest_price or float("inf"))
            elif sort_by == "price_desc":
                canonical_products.sort(key=lambda x: x.price_summary.lowest_price or 0, reverse=True)
            elif sort_by == "rating":
                canonical_products.sort(key=lambda x: x.rating or 0, reverse=True)
            else:
                canonical_products.sort(key=lambda x: x.recommendation.match_score, reverse=True)

            # Update cache
            cache = get_cache()
            cache_key = f"search:{hash_query(raw_query, country, currency)}:{sort_by}"
            intent = ExtractedQueryIntent(raw_query=raw_query, clean_query=raw_query)
            pagination_meta = PaginationMetadata(
                page=1,
                page_size=24,
                total=len(canonical_products),
                total_pages=max(1, (len(canonical_products) + 23) // 24),
                has_next=len(canonical_products) > 24,
                has_prev=False,
                total_offers=sum(len(p.offers) for p in canonical_products),
                providers_contributing=len({o.source.lower() for p in canonical_products for o in p.offers}),
            )
            full_cached_response = UnifiedSearchResponse(
                search_id=uuid.uuid4().hex[:12],
                query=intent,
                products=canonical_products,
                providers=provider_statuses,
                search_duration_ms=0,
                total_products_found=len(merged_raw),
                deduped_count=len(canonical_products),
                pagination=pagination_meta,
                status="SUCCESS",
                is_cached=True,
                is_revalidating=False,
            )
            await cache.set(cache_key, full_cached_response.model_dump(), ttl=600)
            log.info(f"[BACKGROUND] Cache successfully updated with {len(canonical_products)} canonical products for '{raw_query}'.")

            # Persist merged items to database in background
            await self._persist_cluster_items_bg(cluster_items, currency=currency)
        except Exception as e:
            log.warning(f"[BACKGROUND] Error merging pending results for '{raw_query}': {e}")

    async def _persist_cluster_items_bg(
        self, cluster_items: List[Any], currency: str = "INR"
    ) -> None:
        """Asynchronously persists products, offers, and price observations to the database."""
        if not cluster_items:
            return
        t_db_start = time.perf_counter()
        try:
            from app.db.session import SessionLocal
            async with SessionLocal() as db:
                all_canonical_ids = [item[2].id for item in cluster_items]
                existing_prods_res = await db.execute(
                    select(Product).where(Product.id.in_(all_canonical_ids))
                )
                existing_prods_map = {p.id: p for p in existing_prods_res.scalars().all()}

                for (cluster, primary_prod, canonical_detail, offers, price_summary, rec, has_qc, qc_eta, best_unit_str, data_coverage) in cluster_items:
                    existing_product = existing_prods_map.get(canonical_detail.id)
                    if not existing_product:
                        prod_entity = Product(
                            id=canonical_detail.id,
                            identity_key=getattr(primary_prod, "identity_key", None) or canonical_detail.id,
                            title=canonical_detail.title,
                            normalized_name=canonical_detail.title.lower(),
                            brand=canonical_detail.brand,
                            model=canonical_detail.model,
                            category_id=canonical_detail.category_id,
                            description=canonical_detail.description,
                            image_urls=canonical_detail.images,
                            rating=canonical_detail.rating,
                            review_count=canonical_detail.review_count,
                            attributes=canonical_detail.specifications,
                            is_demo=False,
                        )
                        db.add(prod_entity)
                        existing_prods_map[canonical_detail.id] = prod_entity
                    else:
                        if canonical_detail.images and not existing_product.image_urls:
                            existing_product.image_urls = canonical_detail.images
                        if canonical_detail.rating and not existing_product.rating:
                            existing_product.rating = canonical_detail.rating
                        if canonical_detail.review_count and not existing_product.review_count:
                            existing_product.review_count = canonical_detail.review_count

                existing_offers_res = await db.execute(
                    select(Offer).where(Offer.product_id.in_(all_canonical_ids))
                )
                existing_offers_map = {
                    (o.product_id, o.provider, o.retailer_name, o.seller_name or ""): o
                    for o in existing_offers_res.scalars().all()
                }

                for (cluster, primary_prod, canonical_detail, offers, price_summary, rec, has_qc, qc_eta, best_unit_str, data_coverage) in cluster_items:
                    for off in offers:
                        prov = off.source or "retailer"
                        ret_name = off.retailer or "Retailer"
                        sel_name = off.seller or ""
                        key = (canonical_detail.id, prov, ret_name, sel_name)

                        if key in existing_offers_map:
                            db_offer = existing_offers_map[key]
                            db_offer.price_amount = off.price
                            db_offer.currency = off.currency or currency
                            if off.original_price:
                                db_offer.original_price = off.original_price
                            if off.url:
                                db_offer.url = off.url
                            db_offer.availability = off.availability or "in_stock"
                            db_offer.condition = off.condition or "new"
                        else:
                            db_offer = Offer(
                                product_id=canonical_detail.id,
                                provider=prov,
                                retailer_name=ret_name,
                                retailer_domain=(ret_name.lower().replace(" ", "") + ".com") if ret_name else None,
                                seller_name=sel_name,
                                seller_rating=off.seller_rating,
                                price_amount=off.price,
                                currency=off.currency or currency,
                                original_price=off.original_price,
                                shipping_amount=off.shipping_cost,
                                tax_amount=off.tax,
                                availability=off.availability or "in_stock",
                                condition=off.condition or "new",
                                url=off.url,
                                delivery_estimate=off.delivery_estimate,
                                return_policy=off.return_policy,
                                warranty=off.warranty,
                            )
                            db.add(db_offer)
                            existing_offers_map[key] = db_offer

                        if off.price:
                            try:
                                await self.price_service.record_observation(
                                    db=db,
                                    product_id=canonical_detail.id,
                                    retailer=off.retailer,
                                    price=off.price,
                                    currency=off.currency,
                                )
                            except Exception as e:
                                log.debug(f"Error recording price observation: {e}")

                await db.commit()
                db_duration = int((time.perf_counter() - t_db_start) * 1000)
                log.info(f"[DB] Persisted {len(cluster_items)} products and offers in {db_duration}ms")
        except Exception as e:
            log.warning(f"[DB] Error in background DB persistence: {e}")

    async def execute_search(
        self,
        raw_query: str,
        country: str = "IN",
        currency: str = "INR",
        sort_by: str = "recommended",
        page: int = 1,
        page_size: int = 24,
        db: Optional[AsyncSession] = None,
        bypass_cache: bool = False,
    ) -> UnifiedSearchResponse:
        t0 = time.perf_counter()
        search_id = uuid.uuid4().hex[:12]

        # 1. Stale-While-Revalidate (SWR) Cache Check
        cache = get_cache()
        cache_key = f"search:{hash_query(raw_query, country, currency)}:{sort_by}"
        if not bypass_cache:
            cached_data = await cache.get(cache_key)
            if cached_data and isinstance(cached_data, dict):
                t_cache = int((time.perf_counter() - t0) * 1000)
                log.info(f"Search cache HIT for query: '{raw_query}' in {t_cache}ms")
                try:
                    cached_res = UnifiedSearchResponse.model_validate(cached_data)
                    cached_res.search_id = search_id
                    cached_res.is_cached = True
                    cached_res.is_revalidating = True
                    cached_res.timing_breakdown = {
                        "cache_hit": True,
                        "total_search_time_ms": t_cache,
                        "time_to_first_product_ms": max(1, t_cache),
                    }

                    # Trigger non-blocking asynchronous background revalidation
                    if self.settings.search_swr_enabled:
                        asyncio.create_task(
                            self._revalidate_and_cache(
                                raw_query=raw_query,
                                country=country,
                                currency=currency,
                                sort_by=sort_by,
                            )
                        )

                    # Handle pagination on cached results if requested
                    total = len(cached_res.products)
                    total_pages = max(1, (total + page_size - 1) // page_size)
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    cached_res.pagination = PaginationMetadata(
                        page=page,
                        page_size=page_size,
                        total=total,
                        total_pages=total_pages,
                        has_next=end_idx < total,
                        has_prev=page > 1,
                        total_offers=sum(len(p.offers) for p in cached_res.products),
                        providers_contributing=len(
                            {o.source.lower() for p in cached_res.products for o in p.offers}
                        ),
                    )
                    cached_res.products = cached_res.products[start_idx:end_idx]
                    return cached_res
                except Exception as e:
                    log.warning(f"Failed to deserialize cache: {e}")

        # 2. Intent Extraction (Gemini LLM with robust rule-based fallback)
        intent = await self.intent_service.extract_intent(raw_query, country=country, currency=currency)

        search_query = SearchQuery(
            query=raw_query,
            category=intent.category,
            max_price=intent.max_price,
            min_price=intent.min_price,
            currency=currency,
            country=country,
            limit=30,
        )

        domain_intent = SearchIntent(
            raw_query=raw_query,
            provider_query=intent.clean_provider_query or raw_query,
            category=intent.category,
            budget=Budget(min=intent.min_price, max=intent.max_price, currency=currency),
            use_cases=intent.use_cases,
            preferred_brands=[intent.brand] if intent.brand else [],
            keywords=intent.keywords,
            country=country,
        )

        domain_params = ProviderSearchParams(
            query=raw_query,
            intent=domain_intent,
            country=country,
            currency=currency,
            limit=30,
        )

        # 3. Universal Provider Search with Isolated Failures
        async def _run_provider(
            name: str, prov: Any
        ) -> Tuple[str, List[ProviderProduct], ProviderExecutionStatus]:
            p_start = time.perf_counter()

            # Check if provider is configured / enabled
            if hasattr(prov, "is_configured"):
                try:
                    conf_res = prov.is_configured()
                    if inspect.iscoroutine(conf_res):
                        conf_res = await conf_res
                    if not conf_res:
                        p_elapsed = int((time.perf_counter() - p_start) * 1000)
                        status = ProviderExecutionStatus(
                            status="unavailable",
                            result_count=0,
                            duration_ms=p_elapsed,
                            reason="API_KEY_OR_CONFIG_NOT_SET",
                        )
                        return name, [], status
                except Exception as e:
                    log.warning(f"Error checking is_configured for {name}: {e}")

            try:
                # Dispatch query using the method supported by the provider
                if hasattr(prov, "search_products"):
                    if name in ("google_scraper", "amazon", "flipkart"):
                        async with self._browser_semaphore:
                            try:
                                res = await prov.search_products(search_query)
                            except (TypeError, AttributeError):
                                res = await prov.search_products(domain_params)
                    else:
                        try:
                            res = await prov.search_products(domain_params)
                        except (TypeError, AttributeError):
                            res = await prov.search_products(search_query)
                else:
                    res = []

                p_elapsed = int((time.perf_counter() - p_start) * 1000)

                # Normalize items into ProviderProduct
                normalized_items: List[ProviderProduct] = []
                for item in res:
                    if isinstance(item, ProviderProduct):
                        if intent.max_price and item.price.amount and item.price.amount > intent.max_price:
                            continue
                        if intent.min_price and item.price.amount and item.price.amount < intent.min_price:
                            continue
                        normalized_items.append(item)
                    elif isinstance(item, RawProduct):
                        pp = raw_product_to_provider_product(item)
                        if intent.max_price and pp.price.amount and pp.price.amount > intent.max_price:
                            continue
                        if intent.min_price and pp.price.amount and pp.price.amount < intent.min_price:
                            continue
                        normalized_items.append(pp)

                if normalized_items:
                    status = ProviderExecutionStatus(
                        status="healthy",
                        result_count=len(normalized_items),
                        duration_ms=p_elapsed,
                    )
                else:
                    status = ProviderExecutionStatus(
                        status="degraded",
                        result_count=0,
                        duration_ms=p_elapsed,
                        reason="ZERO_PRODUCTS_PARSED",
                    )

                return name, normalized_items, status

            except ProviderBlocked as exc:
                p_elapsed = int((time.perf_counter() - p_start) * 1000)
                log.warning(f"Provider {name} was BLOCKED: {exc}")
                status = ProviderExecutionStatus(
                    status="blocked",
                    duration_ms=p_elapsed,
                    error=str(exc),
                    reason=str(exc),
                )
                return name, [], status
            except ProviderTimeout as exc:
                p_elapsed = int((time.perf_counter() - p_start) * 1000)
                log.warning(f"Provider {name} TIMED OUT: {exc}")
                status = ProviderExecutionStatus(
                    status="degraded",
                    duration_ms=p_elapsed,
                    error=str(exc),
                    reason=f"TIMEOUT: {exc}",
                )
                return name, [], status
            except ProviderUnavailable as exc:
                p_elapsed = int((time.perf_counter() - p_start) * 1000)
                log.warning(f"Provider {name} UNAVAILABLE: {exc}")
                status = ProviderExecutionStatus(
                    status="unavailable",
                    duration_ms=p_elapsed,
                    error=str(exc),
                    reason=str(exc),
                )
                return name, [], status
            except Exception as exc:
                p_elapsed = int((time.perf_counter() - p_start) * 1000)
                log.warning(f"Provider {name} encountered error: {exc}")
                status = ProviderExecutionStatus(
                    status="degraded",
                    duration_ms=p_elapsed,
                    error=str(exc),
                    reason=str(exc),
                )
                return name, [], status

        # Dynamic Marketplace & Provider Discovery
        selected_provider_names = self.discovery_engine.select_relevant_providers(
            self.providers,
            domain_intent,
            country=country,
        )
        task_map = {
            asyncio.create_task(_run_provider(name, self.providers[name])): name
            for name in selected_provider_names
            if name in self.providers
        }

        # Fast initial window: wait up to search_fast_window_seconds
        fast_window = self.settings.search_fast_window_seconds
        done, pending = await asyncio.wait(task_map.keys(), timeout=fast_window)

        results: List[Tuple[str, List[ProviderProduct], ProviderExecutionStatus]] = []
        for t in done:
            try:
                results.append(t.result())
            except Exception as exc:
                p_name = task_map.get(t, "unknown")
                log.warning(f"Provider task {p_name} threw exception: {exc}")
                results.append((p_name, [], ProviderExecutionStatus(status="degraded", duration_ms=int(fast_window * 1000), error=str(exc))))

        provider_statuses: Dict[str, ProviderExecutionStatus] = {}
        all_raw_products: List[ProviderProduct] = []

        for name, prods, status in results:
            provider_statuses[name] = status
            all_raw_products.extend(prods)

        time_to_first_product_ms = None
        if all_raw_products:
            time_to_first_product_ms = int((time.perf_counter() - t0) * 1000)

        # If no products were returned within the fast window, wait up to secondary timeout for pending tasks
        if not all_raw_products and pending:
            secondary_timeout = max(1.0, self.settings.provider_timeout_seconds - fast_window)
            done2, pending = await asyncio.wait(pending, timeout=secondary_timeout)
            for t in done2:
                try:
                    res2 = t.result()
                    results.append(res2)
                    name, prods, status = res2
                    provider_statuses[name] = status
                    all_raw_products.extend(prods)
                except Exception as exc:
                    p_name = task_map.get(t, "unknown")
                    results.append((p_name, [], ProviderExecutionStatus(status="degraded", duration_ms=int(secondary_timeout * 1000), error=str(exc))))
            if all_raw_products and not time_to_first_product_ms:
                time_to_first_product_ms = int((time.perf_counter() - t0) * 1000)

        # If there are still pending tasks, launch non-blocking background task to await and merge them into cache
        if pending:
            asyncio.create_task(
                self._complete_pending_and_merge(
                    pending=pending,
                    task_map=task_map,
                    raw_query=raw_query,
                    country=country,
                    currency=currency,
                    sort_by=sort_by,
                    existing_raw_products=list(all_raw_products),
                    provider_statuses=dict(provider_statuses),
                )
            )

        # 4. Query Simplification Fallback (if 0 products and query has long phrasing)
        if not all_raw_products and intent.clean_provider_query and intent.clean_provider_query.lower() != raw_query.lower():
            log.info(
                f"Initial search for '{raw_query}' returned 0 products. Retrying with simplified query: '{intent.clean_provider_query}'"
            )
            retry_tasks = [
                _run_provider(name, p)
                for name, p in self.providers.items()
                if name in provider_statuses and provider_statuses[name].status not in ("blocked", "unavailable")
            ]
            if retry_tasks:
                retry_results = await asyncio.gather(*retry_tasks)
                for name, prods, status in retry_results:
                    if prods:
                        provider_statuses[name] = status
                        all_raw_products.extend(prods)
            if all_raw_products and not time_to_first_product_ms:
                time_to_first_product_ms = int((time.perf_counter() - t0) * 1000)

        # 5. If all providers failed or returned 0 live products
        if not all_raw_products:
            elapsed = int((time.perf_counter() - t0) * 1000)
            any_blocked = any(s.status == "blocked" for s in provider_statuses.values())
            overall_status = "BLOCKED" if any_blocked else "NO_LIVE_DATA"
            msg = "Live product data is temporarily unavailable from configured retailers."
            return UnifiedSearchResponse(
                search_id=search_id,
                query=intent,
                products=[],
                providers=provider_statuses,
                search_duration_ms=elapsed,
                total_products_found=0,
                deduped_count=0,
                pagination=PaginationMetadata(page=page, page_size=page_size, total=0, total_pages=1),
                status=overall_status,
                message=msg,
                is_cached=False,
                is_revalidating=False,
                time_to_first_product_ms=None,
                timing_breakdown={"total_search_time_ms": elapsed, "cache_hit": False},
            )

        # 6. Group into Canonical Clusters via ProductIdentityService
        t_dedup = time.perf_counter()
        clusters = self.identity_service.cluster_products(all_raw_products)
        dedup_duration_ms = int((time.perf_counter() - t_dedup) * 1000)

        # 7. Normalize and Merge Offers per Canonical Product
        t_rec = time.perf_counter()
        canonical_products: List[CanonicalSearchProduct] = []
        cluster_items = []

        for cluster in clusters:
            primary_prod = cluster[0]

            # 1. Multi-tier Image Validation and Ranking across all items in cluster
            candidate_imgs = []
            for item in cluster:
                if getattr(item, "primary_image", None):
                    candidate_imgs.append(item.primary_image)
                if getattr(item, "image_url", None):
                    candidate_imgs.append(item.image_url)
                if getattr(item, "image_urls", None):
                    candidate_imgs.extend(item.image_urls)
            best_img, gallery_imgs = self.image_service.select_best_image(candidate_imgs, primary_prod.title)

            canonical_detail = self.normalization_service.normalize_provider_product(
                primary_prod,
                category_id=intent.category or "general",
            )
            canonical_detail.image_url = best_img
            canonical_detail.images = ([best_img] + [g for g in gallery_imgs if g != best_img]) if best_img else []
            canonical_detail.image_urls = canonical_detail.images

            offers = [self.offer_service.build_offer(item, canonical_detail.id) for item in cluster]
            price_summary = self.offer_service.summarize_prices(offers)
            rec = self.recommendation_service.evaluate_product(primary_prod, intent)

            # Quick commerce intelligence
            has_qc = any(o.is_quick_commerce for o in offers)
            qc_eta = next((o.delivery_estimate for o in offers if o.is_quick_commerce and o.delivery_estimate), None)

            # Unit economics
            best_unit_str = None
            for o in offers:
                if o.unit_price and o.unit_measure:
                    sym = "₹" if currency in ("INR", "₹") else f"{currency} "
                    best_unit_str = f"{sym}{o.unit_price:,.2f} / {o.unit_measure}"
                    break
            if not best_unit_str:
                unit_econ = UnitEconomicsService.extract_and_calculate(price_summary.lowest_price, primary_prod.title, currency=currency)
                if unit_econ:
                    best_unit_str = unit_econ.formatted_unit_price

            data_coverage = self.recommendation_service.compute_data_coverage_score(primary_prod)

            canonical_detail.offers = offers
            canonical_detail.price_summary = price_summary
            canonical_detail.best_price = price_summary.lowest_price if price_summary else None
            canonical_detail.primary_retailer = offers[0].retailer if offers else None
            canonical_detail.offers_count = len(offers)

            cluster_items.append((cluster, primary_prod, canonical_detail, offers, price_summary, rec, has_qc, qc_eta, best_unit_str, data_coverage))

        rec_duration_ms = int((time.perf_counter() - t_rec) * 1000)

        # Offload batched database persistence to asynchronous background task (eliminates HTTP response blocking)
        asyncio.create_task(self._persist_cluster_items_bg(cluster_items, currency=currency))

        # Build final canonical products list and cache individual products
        for (cluster, primary_prod, canonical_detail, offers, price_summary, rec, has_qc, qc_eta, best_unit_str, data_coverage) in cluster_items:
            try:
                await cache.set(f"product:{canonical_detail.id}", canonical_detail.model_dump(), ttl=3600)
            except Exception as e:
                log.debug(f"Error caching product:{canonical_detail.id}: {e}")

            sources = list({o.retailer for o in offers})
            freshness_label = self.freshness_service.get_freshness_label(offers[0].fetched_at if offers else None)

            canonical_products.append(
                CanonicalSearchProduct(
                    id=canonical_detail.id,
                    title=canonical_detail.title,
                    brand=canonical_detail.brand,
                    model=canonical_detail.model,
                    category_id=canonical_detail.category_id,
                    image=canonical_detail.images[0] if canonical_detail.images else None,
                    image_urls=canonical_detail.images,
                    rating=canonical_detail.rating,
                    review_count=canonical_detail.review_count,
                    recommendation=rec,
                    offers=offers,
                    price_summary=price_summary,
                    sources=sources,
                    card_attributes=[],
                    freshness_label=freshness_label,
                    data_coverage_score=data_coverage,
                    is_quick_commerce=has_qc,
                    quick_commerce_eta=qc_eta,
                    best_unit_price=best_unit_str,
                )
            )

        # 8. Sort Globally
        if sort_by == "price_asc":
            canonical_products.sort(key=lambda x: x.price_summary.lowest_price or float("inf"))
        elif sort_by == "price_desc":
            canonical_products.sort(key=lambda x: x.price_summary.lowest_price or 0, reverse=True)
        elif sort_by == "rating":
            canonical_products.sort(key=lambda x: x.rating or 0, reverse=True)
        else:  # recommended
            canonical_products.sort(key=lambda x: x.recommendation.match_score, reverse=True)

        total_canonical = len(canonical_products)
        total_raw = len(all_raw_products)
        total_offers = sum(len(p.offers) for p in canonical_products)
        unique_sources = len({o.source.lower() for p in canonical_products for o in p.offers})

        # Structured diagnostic logs
        log.info(
            f"\nNORMALIZATION & DEDUPLICATION REPORT\n"
            f"raw_products={total_raw}\n"
            f"canonical_products={total_canonical}\n"
            f"total_offers={total_offers}\n"
            f"contributing_sources={unique_sources}"
        )

        # 9. Pagination
        total_pages = max(1, (total_canonical + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_products = canonical_products[start_idx:end_idx]

        pagination_meta = PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total_canonical,
            total_pages=total_pages,
            has_next=end_idx < total_canonical,
            has_prev=page > 1,
            total_offers=total_offers,
            providers_contributing=unique_sources,
        )

        elapsed = int((time.perf_counter() - t0) * 1000)

        # Granular timing breakdown
        qc_latencies = [
            s.duration_ms for name, s in provider_statuses.items()
            if name in ("blinkit", "zepto", "instamart", "bigbasket") and s.duration_ms > 0
        ]
        avg_qc_latency = int(sum(qc_latencies) / len(qc_latencies)) if qc_latencies else None

        timing_breakdown = {
            "total_search_time_ms": elapsed,
            "time_to_first_product_ms": time_to_first_product_ms or elapsed,
            "google_latency_ms": provider_statuses.get("google_scraper", ProviderExecutionStatus(status="none")).duration_ms,
            "amazon_latency_ms": provider_statuses.get("amazon", ProviderExecutionStatus(status="none")).duration_ms,
            "flipkart_latency_ms": provider_statuses.get("flipkart", ProviderExecutionStatus(status="none")).duration_ms,
            "ebay_latency_ms": provider_statuses.get("ebay", ProviderExecutionStatus(status="none")).duration_ms,
            "quick_commerce_latency_ms": avg_qc_latency,
            "firecrawl_latency_ms": provider_statuses.get("firecrawl", ProviderExecutionStatus(status="none")).duration_ms,
            "deduplication_time_ms": dedup_duration_ms,
            "recommendation_time_ms": rec_duration_ms,
            "database_latency_ms": 0,
            "cache_hit": False,
        }

        # Record diagnostics telemetry for admin endpoints
        try:
            diag_rec = SearchDiagnosticsRecord(
                search_id=search_id,
                query=raw_query,
                country=country,
                currency=currency,
                started_at=t0,
                completed_at=time.perf_counter(),
                duration_ms=elapsed,
                providers_requested=list(selected_provider_names),
                providers_executed=[name for name, s in provider_statuses.items() if s.status in ("healthy", "success", "degraded")],
                providers_failed=[name for name, s in provider_statuses.items() if s.status in ("error", "timeout", "unavailable")],
                providers_blocked=[name for name, s in provider_statuses.items() if s.status == "blocked"],
                provider_breakdown={name: s.model_dump() for name, s in provider_statuses.items()},
                raw_products_count=total_raw,
                normalized_products_count=len(all_raw_products),
                canonical_products_count=total_canonical,
                total_offers_count=total_offers,
                images_extracted_count=sum(1 for p in canonical_products if p.image),
                quick_commerce_offers_count=sum(1 for p in canonical_products if p.is_quick_commerce),
            )
            diagnostics_store.record(diag_rec)
        except Exception as exc:
            log.warning(f"Error recording search telemetry: {exc}")

        response = UnifiedSearchResponse(
            search_id=search_id,
            query=intent,
            products=paginated_products,
            providers=provider_statuses,
            search_duration_ms=elapsed,
            total_products_found=total_raw,
            deduped_count=total_canonical,
            pagination=pagination_meta,
            status="SUCCESS",
            is_cached=False,
            is_revalidating=bool(pending),
            time_to_first_product_ms=time_to_first_product_ms or elapsed,
            timing_breakdown=timing_breakdown,
        )

        # Cache full dataset in Redis (TTL: 10 minutes)
        full_cached_response = UnifiedSearchResponse(
            search_id=search_id,
            query=intent,
            products=canonical_products,
            providers=provider_statuses,
            search_duration_ms=elapsed,
            total_products_found=total_raw,
            deduped_count=total_canonical,
            pagination=pagination_meta,
            status="SUCCESS",
            is_cached=True,
            is_revalidating=False,
            time_to_first_product_ms=time_to_first_product_ms or elapsed,
            timing_breakdown=timing_breakdown,
        )
        await cache.set(cache_key, full_cached_response.model_dump(), ttl=600)

        return response
