"""Offers API Route."""
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.repositories.offer_repository import OfferRepository
from app.schemas.offer import OfferSchema

router = APIRouter(prefix="/offers", tags=["Offers"])
offer_repo = OfferRepository()


@router.get("", response_model=List[OfferSchema])
async def list_offers(
    product_id: str = Query(..., description="Canonical product ID to fetch offers for"),
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
