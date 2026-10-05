"""Health and Provider Status API Routes."""
from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter
from app.providers.amazon.provider import AmazonProvider
from app.providers.firecrawl import FirecrawlProvider
from app.providers.flipkart.provider import FlipkartProvider
from app.providers.google_scraper import GoogleScraperProvider

router = APIRouter(tags=["Health"])

amazon_prov = AmazonProvider()
flipkart_prov = FlipkartProvider()
google_prov = GoogleScraperProvider()
firecrawl_prov = FirecrawlProvider()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "service": "shopbuddy-engine"}


@router.get("/providers/health")
async def provider_health() -> Dict[str, Any]:
    amz_h = await amazon_prov.health_check()
    fk_h = await flipkart_prov.health_check()
    goog_h = await google_prov.health_check()
    goog_diag = google_prov.get_diagnostics() if hasattr(google_prov, "get_diagnostics") else {}
    fc_h = await firecrawl_prov.health_check()
    fc_diag = firecrawl_prov.get_diagnostics() if hasattr(firecrawl_prov, "get_diagnostics") else {}

    return {
        "firecrawl": {
            "enabled": fc_h.enabled,
            "status": fc_h.status,
            "last_success": fc_h.last_success,
            "last_error": fc_h.last_error,
            "circuit_breaker": "open" if fc_diag.get("circuit_breaker", {}).get("open") else "closed",
            "diagnostics": fc_diag,
        },
        "google_scraper": {
            "enabled": goog_h.enabled,
            "status": goog_h.status,
            "last_success": goog_h.last_success,
            "last_error": goog_h.last_error,
            "circuit_breaker": goog_diag.get("circuit_breaker", {}).get("state", "closed"),
            "diagnostics": goog_diag,
        },
        "amazon": {
            "enabled": amz_h.enabled,
            "status": amz_h.status,
            "last_success": amz_h.last_success,
            "last_error": amz_h.last_error,
        },
        "flipkart": {
            "enabled": fk_h.enabled,
            "status": fk_h.status,
            "last_success": fk_h.last_success,
            "last_error": fk_h.last_error,
        },
    }
