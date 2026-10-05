"""Products API Routes."""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.database.connection import get_db
from app.repositories.offer_repository import OfferRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.schemas.offer import OfferSchema
from app.schemas.price_history import PriceHistoryResponse
from app.schemas.product import CanonicalProductDetail
from app.schemas.review import ReviewAnalysisResponse
from app.services.comparison_service import ComparisonService
from app.services.offer_service import OfferService
from app.services.price_service import PriceService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/products", tags=["Products"])

product_repo = ProductRepository()
offer_repo = OfferRepository()
offer_service = OfferService()
price_service = PriceService()
review_service = ReviewService()
comparison_service = ComparisonService()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_products_post(
    payload: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Performs comprehensive side-by-side AI comparison for 1 to 4 products."""
    try:
        return await comparison_service.compare(payload.product_ids, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


@router.get("/compare", response_model=ComparisonResponse)
async def compare_products_get(
    ids: str = Query(..., description="Comma-separated product IDs to compare"),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """GET variant for product comparison with comma-separated IDs."""
    product_ids = [pid.strip() for pid in ids.split(",") if pid.strip()]
    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided.")
    try:
        return await comparison_service.compare(product_ids, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


@router.get("/{product_id}", response_model=CanonicalProductDetail)
async def get_product_details(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> CanonicalProductDetail:
    # 1. Check Redis cache
    cache = get_cache()
    try:
        cached_data = await cache.get(f"product:{product_id}")
        if cached_data and isinstance(cached_data, dict):
            return CanonicalProductDetail.model_validate(cached_data)
    except Exception:
        pass

    # 2. Check Database
    product = await product_repo.get_by_id(db, product_id)
    if product:
        db_offers = await offer_repo.get_by_product_id(db, product_id)
        offer_schemas = [
            OfferSchema(
                id=o.id,
                product_id=o.product_id,
                retailer=o.retailer_name,
                seller=o.seller_name,
                seller_rating=o.seller_rating,
                url=o.url,
                price=o.price_amount,
                price_amount=o.price_amount,
                currency=o.currency or "INR",
                original_price=o.original_price,
                shipping_cost=o.shipping_amount,
                tax=o.tax_amount,
                final_price=o.price_amount,
                availability=o.availability or "in_stock",
                condition=o.condition or "new",
                delivery_estimate=o.delivery_estimate,
                return_policy=o.return_policy,
                warranty=o.warranty,
                source=o.provider,
                fetched_at=o.last_checked_at.isoformat() if hasattr(o.last_checked_at, "isoformat") else "Just now",
            )
            for o in db_offers
        ]
        price_summary = offer_service.summarize_prices(offer_schemas) if offer_schemas else None
        best_price = price_summary.lowest_price if price_summary else None
        primary_retailer = offer_schemas[0].retailer if offer_schemas else None
        imgs = product.image_urls or []

        return CanonicalProductDetail(
            id=product.id,
            title=product.title,
            brand=product.brand,
            model=product.model,
            category_id=product.category_id,
            description=product.description,
            image_url=imgs[0] if imgs else None,
            images=imgs,
            image_urls=imgs,
            specifications=product.attributes or {},
            identifiers={
                k: v for k, v in {
                    "asin": product.asin,
                    "gtin": product.gtin,
                    "upc": product.upc,
                    "ean": product.ean,
                    "mpn": product.mpn,
                }.items() if v
            },
            rating=product.rating,
            review_count=product.review_count,
            sources=[s.provider for s in product.sources] if product.sources else [],
            offers=offer_schemas,
            price_summary=price_summary,
            best_price=best_price,
            primary_retailer=primary_retailer,
            offers_count=len(offer_schemas),
        )

    raise HTTPException(status_code=404, detail="Product not found")



@router.get("/{product_id}/offers", response_model=List[OfferSchema])
async def get_product_offers(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[OfferSchema]:
    offers = await offer_repo.get_by_product_id(db, product_id)
    return [
        OfferSchema(
            id=o.id,
            product_id=o.product_id,
            retailer=o.retailer_name,
            seller=o.seller_name,
            seller_rating=o.seller_rating,
            url=o.url,
            price=o.price_amount,
            currency=o.currency or "INR",
            original_price=o.original_price,
            discount=o.discount,
            shipping_cost=o.shipping_amount,
            tax=o.tax_amount,
            final_price=o.final_price,
            availability=o.availability,
            condition=o.condition,
            delivery_estimate=o.delivery_estimate,
            return_policy=o.return_policy,
            warranty=o.warranty,
            source=o.provider,
            fetched_at=o.last_checked_at.isoformat(),
        )
        for o in offers
    ]


@router.get("/{product_id}/price-history", response_model=PriceHistoryResponse)
async def get_product_price_history(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    return await price_service.get_price_history(db, product_id)


@router.get("/{product_id}/reviews", response_model=ReviewAnalysisResponse)
async def get_product_reviews(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalysisResponse:
    return await review_service.get_reviews_for_product(db, product_id)
