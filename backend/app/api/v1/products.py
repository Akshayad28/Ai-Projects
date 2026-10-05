"""Products API router."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Offer, PriceObservation, Product, Review
from app.db.session import get_db
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/products", tags=["Products"])

comparison_service = ComparisonService()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_products_v1_post(
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
async def compare_products_v1_get(
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



@router.get("/{product_id}")
async def get_product_detail(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves full product details, verified offers, and specs."""
    res = await db.execute(select(Product).where(Product.id == product_id))
    product = res.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Fetch live offers
    offers_res = await db.execute(select(Offer).where(Offer.product_id == product_id))
    offers = offers_res.scalars().all()

    # Fetch price history observations
    obs_res = await db.execute(
        select(PriceObservation)
        .where(PriceObservation.product_id == product_id)
        .order_by(PriceObservation.observed_at.asc())
    )
    observations = obs_res.scalars().all()

    return {
        "id": product.id,
        "title": product.title,
        "brand": product.brand,
        "category_id": product.category_id,
        "description": product.description,
        "image_urls": product.image_urls,
        "rating": product.rating,
        "review_count": product.review_count,
        "specs": product.attributes,
        "offers": [
            OfferItemResponse(
                id=o.id,
                provider=o.provider,
                retailer_name=o.retailer_name,
                retailer_domain=o.retailer_domain,
                seller_name=o.seller_name,
                seller_rating=o.seller_rating,
                country=o.country,
                price_amount=o.price_amount,
                currency=o.currency,
                original_price=o.original_price,
                shipping_text=o.shipping_text,
                delivery_estimate=o.delivery_estimate,
                availability=o.availability,  # type: ignore[arg-type]
                condition=o.condition,  # type: ignore[arg-type]
                url=o.url,
                affiliate_url=o.affiliate_url,
                return_policy=o.return_policy,
                warranty=o.warranty,
                confidence=o.confidence,
                checked_at=o.last_checked_at.isoformat(),
            )
            for o in offers
        ],
        "is_demo": product.is_demo,
        "price_observations": [
            {
                "observed_at": ob.observed_at.isoformat(),
                "amount": ob.amount,
                "currency": ob.currency,
                "retailer_name": ob.retailer_name,
            }
            for ob in observations
        ],
    }


@router.get("/{product_id}/price-history")
async def get_price_history(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns stored historical price observations only. Never synthesized."""
    obs_res = await db.execute(
        select(PriceObservation)
        .where(PriceObservation.product_id == product_id)
        .order_by(PriceObservation.observed_at.asc())
    )
    observations = obs_res.scalars().all()
    if not observations:
        return {
            "product_id": product_id,
            "observations": [],
            "status": "insufficient_data",
            "message": "Not enough price history.",
        }

    return {
        "product_id": product_id,
        "observations": [
            {
                "observed_at": ob.observed_at.isoformat(),
                "amount": ob.amount,
                "currency": ob.currency,
                "retailer_name": ob.retailer_name,
            }
            for ob in observations
        ],
        "status": "verified",
    }
