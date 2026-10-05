"""Search API router."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.engine import extract_attributes, resolve_category_from_text
from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resilience import enforce_rate_limit
from app.db.models import Category, CategoryAttribute, CategoryRule, CategoryWeight
from app.db.session import get_db
from app.nlp.intent import parse_intent
from app.providers.registry import get_provider_registry
from app.recommendations.engine import RecommendationEngine
from app.schemas.api import (
    DynamicCardAttribute,
    OfferItemResponse,
    PaginationMetadataResponse,
    ProductCardResponse,
    RecommendationBreakdownResponse,
    SearchMetadataResponse,
    SearchRequest,
    SearchResponse,
)
from app.schemas.domain import ProviderSearchParams, RawProduct

router = APIRouter(prefix="/search", tags=["Search"])
log = get_logger(__name__)
rec_engine = RecommendationEngine()

_categories_cache: Optional[Tuple[float, List[Category]]] = None


async def _get_cached_categories(db: AsyncSession) -> List[Category]:
    global _categories_cache
    now = time.time()
    if _categories_cache and (now - _categories_cache[0]) < 300:
        return _categories_cache[1]
    categories_res = await db.execute(select(Category))
    all_categories = list(categories_res.scalars().all())
    _categories_cache = (now, all_categories)
    return all_categories


@router.post("", response_model=SearchResponse)
async def execute_search(
    req: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    t0 = time.perf_counter()
    settings = get_settings()

    # Rate limiting
    await enforce_rate_limit(request, "search", settings.user_rate_limit_per_minute)

    # 1. Parse Search Intent (NLP / LLM)
    intent = await parse_intent(req.query, country=req.country, currency=req.currency)

    # 2. Category resolution (cached in-memory for 5 minutes)
    all_categories = await _get_cached_categories(db)

    resolved_cat, conf = resolve_category_from_text(req.query, all_categories)
    if resolved_cat:
        intent.category = resolved_cat
        intent.category_confidence = conf

    # 3. Provider search in parallel
    provider_params = ProviderSearchParams(
        query=req.query,
        intent=intent,
        country=req.country,
        currency=req.currency,
        limit=25,
    )

    registry = get_provider_registry()
    live_count = registry.count_live_configured()
    provider_status = registry.get_provider_status()
    raw_products, provider_results = await registry.search_parallel(provider_params)

    # If no results from live providers
    if not raw_products:
        elapsed = int((time.perf_counter() - t0) * 1000)
        if live_count == 0:
            unconfigured_msg = (
                "No live retail data providers configured. ShopBuddy strictly adheres to data integrity "
                "and NEVER fabricates mock products in production."
            )
            notice_msg = "Live product search is currently unavailable. No live providers configured."
        else:
            unconfigured_msg = "No live products matching your criteria were returned by the active retailers. Try broadening your query or budget."
            notice_msg = "No live products found."

        providers_diag_map = {}
        for r in provider_results:
            prov_obj = registry.providers.get(r.provider)
            if prov_obj and hasattr(prov_obj, "get_diagnostics"):
                providers_diag_map[r.provider] = prov_obj.get_diagnostics()
            else:
                providers_diag_map[r.provider] = {
                    "status": r.status.upper(),
                    "raw": len(r.products),
                    "offers": sum(len(p.offers) for p in r.products),
                    "latency_ms": r.latency_ms,
                }

        page = max(1, getattr(req, "page", 1))
        page_size = max(1, getattr(req, "page_size", 24))

        pagination_meta = PaginationMetadataResponse(
            page=page,
            page_size=page_size,
            total=0,
            total_pages=1,
            has_next=False,
            total_offers=0,
            providers_contributing=0,
        )

        return SearchResponse(
            query=req.query,
            intent=intent,
            products=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=1,
            has_next=False,
            providers=providers_diag_map,
            search_metadata=SearchMetadataResponse(
                search_id=uuid.uuid4().hex[:12],
                search_duration_ms=elapsed,
                providers_used=[r.provider for r in provider_results],
                products_found=0,
                deduped_count=0,
                total_offers=0,
                providers_contributing=0,
                pagination=pagination_meta,
                providers=providers_diag_map,
                is_live=live_count > 0,
                live_providers_configured=live_count,
                live_providers=provider_status,
                freshness_label="Live Real-Time Data" if live_count > 0 else "No Providers Configured",
                is_demo=False,
                demo_mode_active=False,
                demo_notice=notice_msg,
                unconfigured_notice=unconfigured_msg,
            ),
        )

    # 4. Fetch category attributes, weights & rules for dynamic extraction & scoring
    cat_id = intent.category or "general"
    attr_res = await db.execute(select(CategoryAttribute).where(CategoryAttribute.category_id == cat_id))
    cat_attributes = list(attr_res.scalars().all())

    weights_res = await db.execute(select(CategoryWeight).where(CategoryWeight.category_id == cat_id))
    cat_weights = {w.factor: w.weight for w in weights_res.scalars().all()}

    rules_res = await db.execute(select(CategoryRule).where(CategoryRule.category_id == cat_id))
    cat_rules = list(rules_res.scalars().all())

    # Extract dynamic attributes for each product
    for p in raw_products:
        p.specs = extract_attributes(p.title, p.description, p.specs, cat_attributes)

    # 5. Score and rank via RecommendationEngine
    ranked = rec_engine.rank_products(raw_products, intent, cat_weights, cat_rules)

    # Apply sorting if requested
    if req.sort_by == "price_asc":
        ranked.sort(key=lambda x: min((o.price_amount or float("inf")) for o in x[0].offers) if x[0].offers else float("inf"))
    elif req.sort_by == "price_desc":
        ranked.sort(key=lambda x: max((o.price_amount or 0) for o in x[0].offers) if x[0].offers else 0, reverse=True)
    elif req.sort_by == "rating":
        ranked.sort(key=lambda x: x[0].rating or 0, reverse=True)

    # 6. Transform to Response DTOs
    product_dtos: List[ProductCardResponse] = []
    any_demo = False

    for prod, score, breakdown in ranked:
        if prod.is_demo:
            any_demo = True

        best_offer = min(prod.offers, key=lambda o: o.price_amount or float("inf")) if prod.offers else None
        best_price = best_offer.price_amount if best_offer else None
        original_price = best_offer.original_price if best_offer else None
        discount_pct = None
        if best_price and original_price and original_price > best_price:
            discount_pct = int(round(((original_price - best_price) / original_price) * 100))

        # Dynamic card attributes configured for this category (show_on_card == True)
        card_attrs: List[DynamicCardAttribute] = []
        for a_def in cat_attributes:
            if a_def.show_on_card and a_def.key in prod.specs:
                card_attrs.append(DynamicCardAttribute(
                    key=a_def.key,
                    label=a_def.label,
                    value=prod.specs[a_def.key],
                    unit=a_def.unit,
                ))

        sources = list({o.retailer_name for o in prod.offers if o.retailer_name})
        primary_retailer = best_offer.retailer_name if best_offer else (sources[0] if sources else "Verified Seller")

        checked_str = best_offer.checked_at.isoformat() if best_offer and hasattr(best_offer.checked_at, "isoformat") else str(best_offer.checked_at if best_offer else "")

        offer_dtos: List[OfferItemResponse] = []
        for o in (prod.offers or []):
            disc_pct = None
            if o.original_price and o.price_amount and o.original_price > o.price_amount:
                disc_pct = int(round(((o.original_price - o.price_amount) / o.original_price) * 100))
            offer_dtos.append(OfferItemResponse(
                provider=o.provider,
                retailer_name=o.retailer_name or o.provider.capitalize(),
                retailer_domain=getattr(o, "retailer_domain", None),
                seller_name=o.seller_name or "",
                price_amount=o.price_amount,
                currency=o.currency or req.currency,
                original_price=o.original_price,
                discount_percent=disc_pct,
                delivery_estimate=o.delivery_estimate or (f"{o.delivery_eta_minutes} mins" if getattr(o, "delivery_eta_minutes", None) else None),
                availability=o.availability or "in_stock",
                url=o.url,
                checked_at=o.checked_at.isoformat() if hasattr(o.checked_at, "isoformat") else str(o.checked_at),
            ))

        is_qc = any(getattr(o, "is_quick_commerce", False) for o in prod.offers)
        qc_eta = next((f"{o.delivery_eta_minutes} mins" for o in prod.offers if getattr(o, "is_quick_commerce", False) and getattr(o, "delivery_eta_minutes", None)), None)
        unit_str = next((getattr(o, "formatted_unit_price", None) or (f"₹{getattr(o, 'unit_price'):.2f} / {getattr(o, 'unit_measure', 'unit')}" if getattr(o, "unit_price", None) else None) for o in prod.offers if getattr(o, "unit_price", None)), None)

        product_dtos.append(ProductCardResponse(
            id=prod.external_id,
            title=prod.title,
            brand=prod.brand,
            category_id=prod.category_hint or intent.category,
            image_url=prod.image_urls[0] if prod.image_urls else None,
            image_urls=prod.image_urls,
            rating=prod.rating,
            review_count=prod.review_count,
            best_price=best_price,
            original_price=original_price,
            currency=best_offer.currency if best_offer and best_offer.currency else req.currency,
            discount_percent=discount_pct,
            primary_retailer=primary_retailer,
            offers_count=len(prod.offers),
            availability=best_offer.availability if best_offer else "unknown",
            card_attributes=card_attrs[:4],
            recommendation=RecommendationBreakdownResponse(
                match_score=breakdown["match_score"],
                reasons=breakdown["reasons"],
                drawbacks=breakdown["drawbacks"],
                why_not_higher=breakdown["why_not_higher"],
            ),
            sources=sources,
            is_demo=prod.is_demo,
            last_updated=checked_str,
            is_quick_commerce=is_qc,
            quick_commerce_eta=qc_eta,
            best_unit_price=unit_str,
            data_coverage_score=getattr(prod, "data_coverage_score", None),
            offers=offer_dtos,
        ))

    elapsed = int((time.perf_counter() - t0) * 1000)

    total = len(product_dtos)
    page = max(1, getattr(req, "page", 1))
    page_size = max(1, getattr(req, "page_size", 24))
    total_pages = max(1, (total + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_dtos = product_dtos[start_idx:end_idx]
    has_next = end_idx < total

    total_offers = sum(p.offers_count for p in product_dtos)
    providers_contributing = len({s for p in product_dtos for s in p.sources})

    providers_diag_map = {}
    for r in provider_results:
        prov_obj = registry.providers.get(r.provider)
        if prov_obj and hasattr(prov_obj, "get_diagnostics"):
            providers_diag_map[r.provider] = prov_obj.get_diagnostics()
        else:
            providers_diag_map[r.provider] = {
                "status": r.status.upper(),
                "raw": len(r.products),
                "offers": sum(len(p.offers) for p in r.products),
                "latency_ms": r.latency_ms,
            }

    # Aggregate live marketplace counts dynamically
    marketplace_counts: Dict[str, int] = {}
    for p in product_dtos:
        for s in (p.sources or []):
            if s:
                marketplace_counts[s] = marketplace_counts.get(s, 0) + 1
        for o in (p.offers or []):
            ret = o.retailer_name or o.provider.capitalize()
            if ret:
                marketplace_counts[ret] = marketplace_counts.get(ret, 0) + 1

    marketplaces_list = [
        {"name": name, "offers": count}
        for name, count in sorted(marketplace_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    pagination_meta = PaginationMetadataResponse(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        total_offers=total_offers,
        providers_contributing=providers_contributing,
    )

    return SearchResponse(
        query=req.query,
        intent=intent,
        products=paginated_dtos,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        providers=providers_diag_map,
        marketplaces=marketplaces_list,
        search_metadata=SearchMetadataResponse(
            search_id=uuid.uuid4().hex[:12],
            search_duration_ms=elapsed,
            providers_used=[r.provider for r in provider_results],
            products_found=len(raw_products),
            deduped_count=len(product_dtos),
            total_offers=total_offers,
            providers_contributing=providers_contributing,
            pagination=pagination_meta,
            providers=providers_diag_map,
            is_live=not any_demo,
            live_providers_configured=live_count,
            live_providers=provider_status,
            freshness_label="Live Real-Time Data (Sub-minute freshness)" if not any_demo else "Demo Mode Data",
            is_demo=any_demo,
            demo_mode_active=settings.demo_mode,
            demo_notice="Demo data – DEMO_MODE enabled" if any_demo else None,
            unconfigured_notice=None,
        ),
    )


@router.get("/facets")
async def get_search_facets(
    category: str = Query(..., description="Category ID to fetch filter facets for"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns database-driven filter facets for the given category."""
    attr_res = await db.execute(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == category,
            CategoryAttribute.filterable == True,
        ).order_by(CategoryAttribute.display_order)
    )
    facets = []
    for a in attr_res.scalars().all():
        facets.append({
            "key": a.key,
            "label": a.label,
            "value_type": a.value_type,
            "unit": a.unit,
        })
    return {"category": category, "facets": facets}
