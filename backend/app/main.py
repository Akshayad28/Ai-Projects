"""FastAPI application entry point with enterprise security, rate limiting, and RBAC."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.products import router as products_router
from app.api.v1.search import router as search_router
from app.api.v1.user import router as user_router
from app.catalog.engine import seed_categories_if_empty
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import get_client_identifier, limiter
from app.db.session import SessionLocal, create_all

log = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth security response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; object-src 'none';"
        )
        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Global request throttling to prevent DoS attacks."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        # Skip static or health check routes from tight global limits
        path = request.url.path
        if path in ("/", "/health", "/docs", "/openapi.json", "/api/v1/admin/health"):
            return await call_next(request)

        client_id = get_client_identifier(request)
        is_limited, retry_after = limiter.is_rate_limited(f"global:{client_id}", max_requests=120, window_seconds=60)
        if is_limited:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validate_for_runtime()
    configure_logging(settings.log_level)
    log.info("Starting ShopBuddy AI Backend", extra={"env": settings.environment, "demo_mode": settings.demo_mode})

    # Ensure tables exist
    await create_all()

    # Seed dynamic categories if empty
    async with SessionLocal() as session:
        await seed_categories_if_empty(session)

    yield

    log.info("Shutting down ShopBuddy AI Backend")


def create_app() -> FastAPI:
    settings = get_settings()

    # Disable interactive docs in production to prevent schema reconnaissance
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    app = FastAPI(
        title="ShopBuddy AI Engine",
        description="Intelligent multi-category shopping search & recommendation engine API",
        version="1.0.0",
        debug=False,  # Explicitly turn off debug mode
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # 1. Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Global Rate Limiter
    app.add_middleware(GlobalRateLimitMiddleware)

    # 3. Explicit CORS Protection (Disallows wildcard with credentials)
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    for origin in settings.cors_origins:
        if origin and origin not in allowed_origins:
            allowed_origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
    )

    # 4. GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Global Exception Handler (sanitized output, never leaks stack traces)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("Unhandled server exception", extra={"path": request.url.path, "error": str(exc)}, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    # Mount API routes
    from app.api.routes import api_router as standard_api_router
    app.include_router(standard_api_router, prefix="/api")

    # Mount v1 API routers
    prefix = settings.api_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(products_router, prefix=prefix)
    app.include_router(categories_router, prefix=prefix)
    app.include_router(user_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)

    @app.get("/health")
    async def health_root():
        """Lightweight root health check endpoint for cloud load balancers and Render."""
        return {"status": "ok", "environment": settings.environment}

    @app.get("/")
    async def root():
        return {
            "name": "ShopBuddy AI API",
            "docs": docs_url or "disabled in production",
            "health": "/health",
            "diagnostics": f"{prefix}/admin/health",
            "demo_mode": settings.demo_mode,
        }

    return app


app = create_app()
