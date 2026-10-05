"""Categories API router."""
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category
from app.db.session import get_db
from app.schemas.api import CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)) -> List[CategoryResponse]:
    """Retrieves all dynamically configured categories."""
    res = await db.execute(select(Category).order_by(Category.sort_order.asc()))
    cats = res.scalars().all()
    return [
        CategoryResponse(
            id=c.id,
            name=c.name,
            department=c.department,
            keywords=c.keywords or [],
            sort_order=c.sort_order,
        )
        for c in cats
    ]
