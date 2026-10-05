"""User preferences, wishlist, and price alerts API router with authenticated isolation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_optional
from app.core.rate_limit import rate_limit
from app.core.sanitizer import sanitize_text
from app.db.models import PriceAlert, User, WishlistItem
from app.db.session import get_db
from app.schemas.api import PriceAlertCreate, WishlistItemCreate

router = APIRouter(prefix="/user", tags=["User"])

_DEV_GUEST_USER_ID = "dev-guest-user"


def _resolve_user_id(user: Optional[User]) -> str:
    """Return authenticated user ID if logged in, otherwise isolated guest ID."""
    return user.id if user else _DEV_GUEST_USER_ID


@router.get("/wishlist")
async def get_wishlist(
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve items from the user's private wishlist."""
    uid = _resolve_user_id(user)
    res = await db.execute(select(WishlistItem).where(WishlistItem.user_id == uid))
    items = res.scalars().all()
    return [
        {
            "id": it.id,
            "product_id": it.product_id,
            "target_price": it.target_price,
            "currency": it.currency,
            "notes": it.notes,
            "created_at": it.created_at.isoformat(),
        }
        for it in items
    ]


@router.post(
    "/wishlist",
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, bucket="user_wishlist"))],
)
async def add_to_wishlist(
    payload: WishlistItemCreate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Add a product to user's private wishlist with sanitized inputs."""
    uid = _resolve_user_id(user)
    clean_product_id = sanitize_text(payload.product_id, max_length=128)
    clean_notes = sanitize_text(payload.notes, max_length=500) if payload.notes else None
    clean_currency = sanitize_text(payload.currency, max_length=3).upper()

    # Check if already in user's wishlist
    res = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == uid,
            WishlistItem.product_id == clean_product_id,
        )
    )
    if res.scalars().first():
        return {"status": "exists", "product_id": clean_product_id}

    item = WishlistItem(
        user_id=uid,
        product_id=clean_product_id,
        target_price=payload.target_price,
        currency=clean_currency,
        notes=clean_notes,
    )
    db.add(item)
    await db.commit()
    return {"status": "created", "id": item.id, "product_id": item.product_id}


@router.delete(
    "/wishlist/{product_id}",
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, bucket="user_wishlist"))],
)
async def remove_from_wishlist(
    product_id: str,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Remove a product from user's private wishlist."""
    uid = _resolve_user_id(user)
    clean_product_id = sanitize_text(product_id, max_length=128)
    await db.execute(
        delete(WishlistItem).where(
            WishlistItem.user_id == uid,
            WishlistItem.product_id == clean_product_id,
        )
    )
    await db.commit()
    return {"status": "deleted", "product_id": clean_product_id}


@router.get("/alerts")
async def get_alerts(
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve user's private price alerts."""
    uid = _resolve_user_id(user)
    res = await db.execute(select(PriceAlert).where(PriceAlert.user_id == uid))
    alerts = res.scalars().all()
    return [
        {
            "id": a.id,
            "product_id": a.product_id,
            "alert_type": a.alert_type,
            "target_price": a.target_price,
            "currency": a.currency,
            "active": a.active,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post(
    "/alerts",
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60, bucket="user_alerts"))],
)
async def create_price_alert(
    payload: PriceAlertCreate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a price drop alert isolated to the user account."""
    uid = _resolve_user_id(user)
    clean_product_id = sanitize_text(payload.product_id, max_length=128)
    clean_alert_type = sanitize_text(payload.alert_type, max_length=32)
    clean_currency = sanitize_text(payload.currency, max_length=3).upper()

    alert = PriceAlert(
        user_id=uid,
        product_id=clean_product_id,
        alert_type=clean_alert_type,
        target_price=payload.target_price,
        percent_drop=payload.percent_drop,
        currency=clean_currency,
        active=True,
    )
    db.add(alert)
    await db.commit()
    return {"status": "created", "id": alert.id, "product_id": alert.product_id}
