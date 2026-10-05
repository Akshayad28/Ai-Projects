"""Admin & Provider diagnostic router with role-based access control and rate limiting."""
from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.providers.registry import get_provider_registry

router = APIRouter(prefix="/admin", tags=["Admin & Diagnostics"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Public sanitized service health check."""
    settings = get_settings()
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "demo_mode": settings.demo_mode,
    }


@router.get(
    "/providers",
    dependencies=[
        Depends(require_admin),
        Depends(rate_limit(max_requests=30, window_seconds=60, bucket="admin_providers")),
    ],
)
async def list_provider_status() -> List[Dict[str, Any]]:
    """Returns registration and configuration status for all product providers (Admin only)."""
    registry = get_provider_registry()
    return registry.get_provider_status()


@router.get(
    "/search-diagnostics/{search_id}",
    dependencies=[
        Depends(require_admin),
        Depends(rate_limit(max_requests=60, window_seconds=60, bucket="admin_diagnostics")),
    ],
)
async def get_search_diagnostics(search_id: str) -> Dict[str, Any]:
    """Retrieve detailed provider execution diagnostics for a search run (Admin only)."""
    from app.services.diagnostics_store import diagnostics_store

    record = diagnostics_store.get(search_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No search diagnostics found for search_id '{search_id}'",
        )
    return record.model_dump()


@router.get(
    "/search-diagnostics/latest/report",
    dependencies=[
        Depends(require_admin),
        Depends(rate_limit(max_requests=60, window_seconds=60, bucket="admin_diagnostics")),
    ],
)
async def get_latest_search_diagnostics() -> Dict[str, Any]:
    """Retrieve the most recent search diagnostics report (Admin only)."""
    from app.services.diagnostics_store import diagnostics_store

    record = diagnostics_store.get_latest()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No search diagnostics recorded yet.",
        )
    return record.model_dump()
