"""Application configuration.

All secrets are read from the environment (or a local, git-ignored `.env`).
Nothing in this module is ever sent to the browser.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), env_file_encoding="utf-8", extra="ignore")

    # ── Environment ────────────────────────────────────────────────
    environment: str = Field("development", description="development | staging | production")
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: Union[List[str], str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["http://localhost:3000"]

    # DEMO_MODE must be explicitly enabled. It is refused in production.
    demo_mode: bool = False

    # ── Storage ────────────────────────────────────────────────────
    # PostgreSQL (+pgvector) in staging/production. SQLite is allowed for
    # local development only.
    database_url: str = "sqlite+aiosqlite:///./shopbuddy-dev.db"
    auto_create_tables: bool = True
    redis_url: Optional[str] = None

    # ── Auth ───────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24 * 7
    admin_api_token: Optional[str] = None

    # ── LLM providers (used ONLY for intent parsing / summaries) ──
    llm_provider: str = "auto"  # auto | openai | azure | gemini | anthropic | none
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = "2024-10-21"
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-flash-lite-latest"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-haiku-latest"

    @property
    def gemini_api_token(self) -> Optional[str]:
        return self.gemini_api_key or self.google_api_key

    # ── Product data providers ─────────────────────────────────────
    # SerpApi (Google Shopping results – licensed SERP API)
    serpapi_enabled: bool = True
    search_provider_api_key: Optional[str] = None
    # Best Buy Products API (US) – https://developer.bestbuy.com
    bestbuy_api_key: Optional[str] = None
    # eBay Browse API (OAuth client credentials)
    ebay_client_id: Optional[str] = None
    ebay_client_secret: Optional[str] = None
    ebay_affiliate_campaign_id: Optional[str] = None
    # Amazon Product Advertising API 5.0
    amazon_paapi_access_key: Optional[str] = None
    amazon_paapi_secret_key: Optional[str] = None
    amazon_paapi_partner_tag: Optional[str] = None
    # Flipkart Affiliate API
    flipkart_affiliate_id: Optional[str] = None
    flipkart_affiliate_token: Optional[str] = None
    # Merchant feeds (Google Merchant Center format, TSV/CSV/XML URLs)
    merchant_feed_urls: List[str] = []
    google_merchant_account_id: Optional[str] = None
    # Generic keys kept for forward compatibility with the spec
    provider_api_key: Optional[str] = None
    affiliate_api_key: Optional[str] = None
    image_search_api_key: Optional[str] = None

    # ── Firecrawl Provider Configuration ───────────────────────────
    firecrawl_api_key: Optional[str] = None
    firecrawl_enabled: bool = True
    firecrawl_search_enabled: bool = True
    firecrawl_scrape_enabled: bool = True
    firecrawl_extraction_enabled: bool = True
    firecrawl_max_search_results: int = 20
    firecrawl_max_scrape_pages: int = 10
    firecrawl_request_timeout_seconds: float = 30.0
    firecrawl_concurrency: int = 5
    firecrawl_cache_ttl_seconds: int = 900

    # ── Behaviour ──────────────────────────────────────────────────
    provider_timeout_seconds: float = 12.0
    search_fast_window_seconds: float = 3.0
    search_swr_enabled: bool = True
    search_cache_ttl_seconds: int = 15 * 60
    product_cache_ttl_seconds: int = 30 * 60
    currency_cache_ttl_seconds: int = 12 * 60 * 60
    stale_after_minutes: int = 6 * 60
    min_price_observations_for_advice: int = 8
    user_rate_limit_per_minute: int = 30
    ai_rate_limit_per_minute: int = 20

    # ── Scraper Configuration ──────────────────────────────────────
    scraper_headless: bool = True
    scraper_timeout_ms: int = 15000
    scraper_nav_timeout_ms: int = 20000
    scraper_amazon_enabled: bool = True
    scraper_amazon_max_results: int = 20
    scraper_flipkart_enabled: bool = True
    scraper_flipkart_max_results: int = 20
    scraper_concurrency_providers: int = 2
    scraper_pages_per_provider: int = 2

    # ── Google Shopping Scraper Configuration (Playwright, no API key) ──
    google_scraper_enabled: bool = True
    google_scraper_country: str = "IN"
    google_scraper_language: str = "en"
    google_scraper_currency: str = "INR"
    google_scraper_timeout_seconds: float = 20.0
    google_scraper_max_results: int = 20
    google_scraper_cache_ttl_seconds: int = 300
    google_requests_per_second: float = 1.0
    google_max_retries: int = 1
    google_circuit_breaker_cooldown_seconds: int = 900
    google_extraction_health_threshold: float = 0.2

    # ── Freshness Configuration (Configurable) ──────────────────────
    price_freshness_minutes: int = 30
    availability_freshness_minutes: int = 30
    product_metadata_freshness_hours: int = 24

    @property
    def scraper_config(self) -> dict:
        return {
            "browser": {
                "headless": self.scraper_headless,
                "timeout_ms": self.scraper_timeout_ms,
                "navigation_timeout_ms": self.scraper_nav_timeout_ms,
            },
            "amazon": {
                "enabled": self.scraper_amazon_enabled,
                "max_results": self.scraper_amazon_max_results,
            },
            "flipkart": {
                "enabled": self.scraper_flipkart_enabled,
                "max_results": self.scraper_flipkart_max_results,
            },
            "google": {
                "enabled": self.google_scraper_enabled,
                "max_results": self.google_scraper_max_results,
            },
            "concurrency": {
                "providers": self.scraper_concurrency_providers,
                "pages_per_provider": self.scraper_pages_per_provider,
            },
        }

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql") or self.database_url.startswith("postgres")

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def validate_for_runtime(self) -> None:
        if self.is_production:
            if self.demo_mode:
                raise RuntimeError("DEMO_MODE cannot be enabled in production.")
            if self.jwt_secret == "change-me-in-env":
                raise RuntimeError("JWT_SECRET must be set in production.")
            if not self.is_postgres:
                raise RuntimeError("Production requires PostgreSQL (DATABASE_URL=postgresql+asyncpg://...).")


@lru_cache
def get_settings() -> Settings:
    return Settings()

