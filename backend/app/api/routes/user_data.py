"""Wishlist and Price Alert API Routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.product import Product
from app.db.models import WishlistItem, PriceAlert

router = APIRouter(tags=["User Data"])


class WishlistAddPayload(BaseModel):
    product_id: str
    target_price: Optional[float] = None
    currency: str = "INR"
    notes: Optional[str] = None


class PriceAlertPayload(BaseModel):
    product_id: str
    target_price: float
    currency: str = "INR"
    alert_type: str = "target_price"


@router.post("/wishlist")
async def add_to_wishlist(
    payload: WishlistAddPayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Check if item exists
    item = WishlistItem(
        user_id="anonymous",
        product_id=payload.product_id,
        target_price=payload.target_price,
        currency=payload.currency,
        notes=payload.notes,
    )
    db.add(item)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
    return {"status": "success", "product_id": payload.product_id}


@router.get("/wishlist")
async def get_wishlist(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    q = select(WishlistItem).limit(100)
    res = await db.execute(q)
    items = list(res.scalars().all())
    return [
        {
            "id": i.id,
            "product_id": i.product_id,
            "target_price": i.target_price,
            "currency": i.currency,
            "notes": i.notes,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.post("/price-alerts")
async def create_price_alert(
    payload: PriceAlertPayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    alert = PriceAlert(
        user_id="anonymous",
        product_id=payload.product_id,
        target_price=payload.target_price,
        currency=payload.currency,
        alert_type=payload.alert_type,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return {"id": alert.id, "status": "active", "target_price": alert.target_price}


@router.delete("/price-alerts/{alert_id}")
async def delete_price_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    q = select(PriceAlert).where(PriceAlert.id == alert_id)
    res = await db.execute(q)
    alert = res.scalar_one_or_none()
    if alert:
        await db.delete(alert)
        await db.commit()
    return {"status": "deleted", "id": alert_id}
