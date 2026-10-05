"""API Routes Package."""
from __future__ import annotations

from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.offers import router as offers_router
from app.api.routes.price_history import router as price_history_router
from app.api.routes.products import router as products_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.search import router as search_router
from app.api.routes.user_data import router as user_data_router

api_router = APIRouter()

api_router.include_router(search_router)
api_router.include_router(products_router)
api_router.include_router(offers_router)
api_router.include_router(price_history_router)
api_router.include_router(reviews_router)
api_router.include_router(health_router)
api_router.include_router(user_data_router)

__all__ = ["api_router"]
