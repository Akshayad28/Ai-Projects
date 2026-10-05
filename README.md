# ShopBuddy AI — Production Shopping Engine

> **Tagline:** Search smarter. Compare everything. Buy with confidence.  
> **Core Product Philosophy:** *"Don't just find the cheapest product. Find the product the user is least likely to regret buying."*

ShopBuddy AI is an intelligent personal shopping research engine designed to work dynamically across **arbitrary product categories** (laptops, running shoes, phones, air fryers, office chairs, gaming monitors, luggage, power tools, washing machines, skincare, and more).

---

## 1. System Architecture

```
                                USER QUERY
                                    ↓
                           Gemini Intent Parser
                                    ↓
                          Universal Query Model
                                    ↓
                       Marketplace Discovery Engine
                                    ↓
                        Provider Capability Filter
                                    ↓
         ┌────────────────────────────────────────────────────────┐
         │              PARALLEL LIVE PROVIDERS                   │
         │                                                        │
         │ Google Shopping (Playwright scraper, zero-key)         │
         │ Firecrawl (Web Discovery & Structured Extraction)      │
         │ Amazon India (Browser & PA-API integration)            │
         │ Flipkart India (Browser & Affiliate integration)       │
         │ eBay (Browse API OAuth 2.0)                            │
         │ Croma (Electronics specialist)                         │
         │ Reliance Digital (Electronics specialist)              │
         │ Myntra (Fashion marketplace)                           │
         │ IKEA (Home & furniture specialist)                     │
         │ Blinkit (Quick-commerce, 10-20 min ETA)                │
         │ Zepto (Quick-commerce, 10-15 min ETA)                  │
         │ Swiggy Instamart (Quick-commerce, 15-25 min ETA)       │
         │ BigBasket / BB Now (Quick-commerce & Groceries)        │
         │ Merchant Feeds (Google Merchant Center XML/CSV)        │
         └────────────────────────────────────────────────────────┘
                                    ↓
                              Raw Products
                                    ↓
                           Product Normalizer
                                    ↓
                        Image Extraction & Ranking
                                    ↓
                             Variant Matcher
                                    ↓
                         Product Identity Engine
                                    ↓
                            Canonical Products
                                    ↓
                             Offer Aggregator
                                    ↓
         ┌────────────────────────────────────────────────────────┐
         │ Price Intelligence & Unit Economics (₹/kg, ₹/L, ₹/item)│
         │ Review Sentiment & Customer Evidence                   │
         │ Seller Ratings & Fulfillment Intelligence              │
         │ Delivery Intelligence (ETA, windows, fees)             │
         │ Availability Intelligence & Freshness Tracking         │
         └────────────────────────────────────────────────────────┘
                                    ↓
                      Category-Weighted Recommendation
                                    ↓
                          Unbiased "Why This?"
                                    ↓
                             Global Ranking
                                    ↓
                           Backend Pagination
                                    ↓
                             Next.js Frontend
```

---

## 2. Pluggable Provider Architecture

ShopBuddy implements an extensible `ProductProvider` abstraction (`backend/app/providers/base/`):

```python
class ProductProvider(abc.ABC):
    name: ClassVar[str]
    label: ClassVar[str]
    rate_limit_per_second: ClassVar[float] = 2.0
    countries: ClassVar[Set[str]] = set()
    categories: ClassVar[Set[str]] = set()

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]: ...
    async def get_product(self, external_id: str, country: str) -> Optional[RawProduct]: ...
    async def get_offers(self, external_id: str, country: str) -> List[RawOffer]: ...
    async def get_reviews(self, external_id: str, country: str) -> List[RawReview]: ...
    async def check_availability(self, external_id: str, country: str) -> Optional[ProviderAvailability]: ...
    async def get_delivery(self, external_id: str, country: str) -> Optional[dict]: ...
    async def get_images(self, external_id: str, country: str) -> List[str]: ...
    def get_capabilities(self) -> ProviderCapabilities: ...
```

### Supported Providers:
1. **Firecrawl Universal Web Discovery & Scraper** (`backend/app/providers/firecrawl/`):
   - Open-web discovery across arbitrary retailers, brand stores, and specialist commerce domains.
   - Structured JSON-LD / Microdata / Schema.org extraction with fallback heuristic parsing.
   - Bounded concurrency (default: 5), per-domain rate limiting, and prompt injection defense.
2. **Quick Commerce (First-Class Live Sources)** (`backend/app/providers/quick_commerce.py`):
   - **Blinkit**, **Zepto**, **Swiggy Instamart**, and **BigBasket / BB Now**.
   - Preserves delivery ETAs in minutes (e.g. 10-25 mins), pack sizes, delivery/platform fees, and unit prices (₹/L, ₹/kg, ₹/item).
   - Strict variant safety: 500ml and 1L, or 250g and 500g, never merge into a single offer.
3. **Specialist Marketplaces** (`backend/app/providers/specialists.py`):
   - **Electronics & Tech:** Croma, Reliance Digital.
   - **Fashion & Footwear:** Myntra.
   - **Furniture & Home:** IKEA.
4. **General Marketplaces**:
   - Amazon India, Flipkart, eBay.
5. **Google Shopping Playwright Scraper** (`backend/app/providers/google_scraper/`):
   - Multi-tier resilient parser (Grid v1/v2, Carousel v1/v2, List, and semantic fallback).
   - Rate limited with circuit breaker; never attempts to bypass CAPTCHA.
6. **Merchant Feeds** (`backend/app/providers/merchant_feed.py`):
   - Direct ingestion of Google Merchant Center XML/TSV/CSV feeds.

---

## 3. Dynamic UI and Marketplace Filtering

The Next.js frontend (`shopbuddy/`) dynamically reflects actual contributing retailers:
- **No Hardcoded Amazon/Flipkart Monopoly:** Marketplace filter tabs (`All`, `⚡ Quick Commerce`, `Amazon`, `Flipkart`, `Croma`, `Reliance Digital`, `Blinkit`, etc.) are computed directly from live offer provenance returned by `/api/v1/search`.
- **Runtime Telemetry Bar:** Displays real-time provider statuses:
  - `✓ Contributing` (with active offer counts)
  - `○ Healthy / Standby`
  - `⚠ Blocked / Degraded` (with honest failure isolation reason)
- **Quick-Commerce Badges & Unit Economics:** Renders `⚡ 10-20 min ETA` chips and normalized unit pricing (e.g., `₹136.00 / L`, `₹240.00 / kg`) on cards.
- **Image Fallback Pipeline:** Multi-tier extraction prioritizes structured JSON-LD images, OpenGraph, and main DOM images; validates against tracking pixels, 1x1 transparent GIFs, and placeholder assets. Displays a clean, elegant "Image unavailable" fallback if no legitimate image exists.

---

## 4. How to Add a New Marketplace Provider

Adding a new marketplace (e.g., Nykaa, Decathlon, or a brand store) requires **zero changes** to `SearchOrchestrator`, `RecommendationEngine`, or the frontend product model.

### Step 1: Create the Provider Class
In `backend/app/providers/`, subclass `ProductProvider`:

```python
from app.providers.base import ProductProvider
from app.providers.capabilities import MarketplaceType, ProviderCapabilities
from app.schemas.domain import ProviderSearchParams, RawProduct, RawOffer, PriceData

class DecathlonProvider(ProductProvider):
    name = "decathlon"
    label = "Decathlon"
    countries = {"IN", "FR", "UK"}
    categories = {"sports", "fitness", "outdoor", "footwear"}
    rate_limit_per_second = 2.0

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            product_search=True,
            offers=True,
            availability=True,
            delivery=True,
            images=True,
            marketplace_type=MarketplaceType.SPORTS,
        )

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        # Implement API call, feed ingestion, or scraper
        ...
```

### Step 2: Register in `ProductProviderRegistry`
In `backend/app/providers/registry.py`:

```python
from app.providers.decathlon import DecathlonProvider
from app.providers.capabilities import ProviderMetadata, MarketplaceType

# Inside ProductProviderRegistry.__init__:
self.providers[DecathlonProvider.name] = DecathlonProvider()
self.discovery_engine.register_metadata(
    DecathlonProvider.name,
    ProviderMetadata(
        name=DecathlonProvider.name,
        label=DecathlonProvider.label,
        marketplace_type=MarketplaceType.SPORTS,
        priority=35,
    )
)
```

The system will now automatically:
- Discover Decathlon for sports/outdoor queries.
- Execute it in parallel with other providers.
- Normalize, deduplicate variants, extract unit prices, and rank offers globally.
- Expose Decathlon in provider diagnostics and frontend marketplace filters.

---

## 4. Admin Search Diagnostics API

Every search generates a comprehensive telemetry audit record accessible via:

```http
GET /api/v1/admin/search-diagnostics/{search_id}
GET /api/v1/admin/search-diagnostics/latest/report
```

Response payload includes:
- `search_id`, `query`, `duration_ms`
- `providers_requested`, `providers_executed`, `providers_failed`, `providers_blocked`
- Breakdown per provider: `raw_count`, `normalized_count`, `canonical_count`, `offer_count`, `images_extracted`
- `quick_commerce_offers_count`

---

## 5. Environment Configuration

Copy `backend/.env.example` to `backend/.env`:

```bash
# Environment
ENVIRONMENT=development
DEMO_MODE=true
LOG_LEVEL=INFO

# Storage
DATABASE_URL=sqlite+aiosqlite:///./shopbuddy-dev.db
# For PostgreSQL in staging/production:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/shopbuddy

# Real Provider API Keys (Plug in anytime to immediately retrieve live data):
GOOGLE_SCRAPER_ENABLED=true
SEARCH_PROVIDER_API_KEY=
BESTBUY_API_KEY=
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=

# Firecrawl Web Discovery & Structured Extraction
FIRECRAWL_API_KEY=
FIRECRAWL_ENABLED=true
FIRECRAWL_SEARCH_ENABLED=true
FIRECRAWL_SCRAPE_ENABLED=true
FIRECRAWL_EXTRACTION_ENABLED=true
FIRECRAWL_MAX_SEARCH_RESULTS=20
FIRECRAWL_MAX_SCRAPE_PAGES=10
FIRECRAWL_REQUEST_TIMEOUT_SECONDS=30
FIRECRAWL_CONCURRENCY=5
FIRECRAWL_CACHE_TTL_SECONDS=900

# AI Intent Extraction:
OPENAI_API_KEY=
```

---

## 4. Google Shopping Scraper (Playwright)

ShopBuddy features a built-in browser-based **Google Shopping scraper** that queries Google Shopping directly using Playwright Chromium:

- **Zero API Key Requirement**: Works out-of-the-box without SerpApi, DataForSEO, or paid data proxies.
- **Multinational Coverage**: Supports localized searches across India (`IN`), United States (`US`), United Kingdom (`GB`), Germany (`DE`), UAE (`AE`), and Singapore (`SG`).
- **Real-Time Data Extraction**: Extracts actual observed product titles, prices, currencies, original prices, merchant/retailers, destination links, images, ratings, review counts, and shipping terms.
- **Compliance & Integrity**: Strictly honors website access restrictions. If an anti-bot or CAPTCHA challenge is presented, it logs the condition, marks the provider as `BLOCKED`, and fails gracefully without attempting unauthorized evasion or blocking other providers.
- **DOM Selector Resilience**: Uses a multi-tiered CSS selector fallback architecture (`selectors.py`) so future Google markup shifts can be adapted without altering backend normalization or recommendation pipelines.

### Setup:
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### Configuration Variables:
```ini
GOOGLE_SCRAPER_ENABLED=true
GOOGLE_SCRAPER_COUNTRY=IN
GOOGLE_SCRAPER_LANGUAGE=en
GOOGLE_SCRAPER_CURRENCY=INR
GOOGLE_SCRAPER_TIMEOUT_SECONDS=20
GOOGLE_SCRAPER_MAX_RESULTS=20
GOOGLE_SCRAPER_CACHE_TTL_SECONDS=300
GOOGLE_REQUESTS_PER_SECOND=1.0
GOOGLE_MAX_RETRIES=1
GOOGLE_CIRCUIT_BREAKER_COOLDOWN_SECONDS=900
GOOGLE_EXTRACTION_HEALTH_THRESHOLD=0.2
```

---

## 5. Google Shopping Scraper Architecture & Resilience

The browser-based Google Shopping scraper operates through Playwright Chromium with zero paid API requirements and adheres strictly to access control rules.

### 5.1 Architecture & Modular Layout Parsers

Google Shopping dynamically delivers diverse layouts depending on country, session, device, and experiment groups. Rather than relying on a single static parser, the scraper uses a modular dispatcher pattern:

```
Rendered Google HTML / DOM
            ↓
GoogleParserDispatcher
            ├── detect_layout()
            │     ├── SHOPPING_GRID     → GridParser (sh-dgr__grid-result, multi-column grid)
            │     ├── SHOPPING_CAROUSEL → CarouselParser (pla-unit, mnr-c, horizontal units)
            │     ├── SHOPPING_LIST     → ListParser (sh-dlr__list-result, vertical cards)
            │     └── UNKNOWN           → GenericParser (Microdata schema.org, semantic DOM)
            ↓
Multi-Layer Field Extractors (selectors.py, extraction.py, validation.py)
            ├── Layer 1: Primary CSS selectors
            ├── Layer 2: Alternative fallback selectors
            ├── Layer 3: Semantic DOM attributes, aria-labels, itemprop, srcset
            └── Layer 4: Validated pattern-based text extraction
            ↓
Product Candidate Validation (is_product_candidate)
            ↓
Normalized GoogleScrapedItem → RawProduct / ProviderProduct
```

### 5.2 CAPTCHA & Access Block Detection (No Bypassing)

- **Strict Compliance:** The scraper **never** attempts to solve, bypass, or spoof CAPTCHAs, bot detections, or access restrictions.
- **Immediate Detection:** `detect_google_block()` inspects HTTP status codes (`429`, `403`, `503`), redirect URLs (`/sorry/index`), and page content (`recaptcha`, `unusual traffic from your computer network`).
- **Zero Immediate Retries:** Once a block is detected, execution halts immediately with zero retries to prevent hammering Google.
- **Circuit Breaker:** The provider circuit breaker trips to `OPEN` for `GOOGLE_CIRCUIT_BREAKER_COOLDOWN_SECONDS` (default: 900s). During this cooldown, any subsequent search skips Google and lets other providers (Amazon, Flipkart, etc.) handle product discovery. After cooldown, state transitions to `HALF_OPEN` to permit a single controlled probe.

### 5.3 Extraction Health & Degradation Detection

Every Google scrape tracks detailed telemetry:
- `cards_found`, `products_detected`, `products_parsed`
- Success rates: `price_success_rate`, `image_success_rate`, `merchant_success_rate`, `url_success_rate`
- **Degradation Detection:** If `cards_found >= 5` but `products_parsed / cards_found < GOOGLE_EXTRACTION_HEALTH_THRESHOLD` (default 0.2), the system emits a structured warning: `"Google extraction health degraded; possible DOM/layout change."` and marks the provider status as `degraded` in `/api/providers/health`.

### 5.4 How to Update Selectors When Google Changes

1. Open [`backend/app/providers/google_scraper/selectors.py`](file:///Users/akshaydeshmukh/Documents/ShopFi/backend/app/providers/google_scraper/selectors.py).
2. Selectors are categorized cleanly by field:
   - `CARD_SELECTORS`: Top-level card wrappers.
   - `TITLE_SELECTORS`: Product title text and headings.
   - `PRICE_SELECTORS` & `ORIGINAL_PRICE_SELECTORS`: Monetary amounts and strikethroughs.
   - `MERCHANT_SELECTORS`: Retailer names and domain labels.
   - `IMAGE_SELECTORS`: Product images, thumbnails, `srcset`, and `data-src` tags.
   - `URL_SELECTORS`: Target links and Google redirect wrappers (`/url?url=...`).
3. Add new classes or tag patterns to the relevant list. All selectors support hierarchical fallback (Layer 1 → Layer 2 → Layer 3 semantic).

### 5.5 How to Add a New Google Layout Parser

1. Create a new parser class subclassing `GoogleLayoutParser` in [`backend/app/providers/google_scraper/parser/`](file:///Users/akshaydeshmukh/Documents/ShopFi/backend/app/providers/google_scraper/parser/):
   ```python
   class ModernFeedParser(GoogleLayoutParser):
       layout_type = GoogleLayout.SHOPPING_GRID # or new layout enum
       def can_parse(self, soup: BeautifulSoup) -> bool:
           return len(soup.select("div.new-feed-card")) >= 2
       def parse(self, soup: BeautifulSoup, ...) -> Tuple[List[GoogleScrapedItem], ExtractionHealth]:
           ...
   ```
2. Register the parser in `GoogleParserDispatcher` (`backend/app/providers/google_scraper/parser/dispatcher.py`).
3. Add a corresponding test HTML fixture in `backend/tests/fixtures/google/`.

---

## 6. Running Locally

### Backend (FastAPI):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`
- Provider Telemetry: `http://127.0.0.1:8000/api/providers/health`

### Frontend (Next.js):
```bash
cd shopbuddy
npm install
npm run dev
```
- Web Application: `http://localhost:3000`

---

## 7. Running Tests

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/ -v -k "not live"
```

All 108 unit and integration tests run deterministically:
- `tests/services/test_universal_expansion.py`: Verifies variant safety across volumes (750ml vs 1L), weights (250g vs 500g), and electronics storage (256GB vs 512GB); unit economics (₹/kg, ₹/L, ₹/item); image rejection rules (tracking pixels, 1x1 GIFs, broken assets); marketplace capability routing; in-memory diagnostic storage and admin API endpoints.
- `tests/providers/test_firecrawl.py`: Validates Firecrawl client, token-bucket rate limiter, cache, schema validation, URL classifier, structured JSON-LD extractor, and fault tolerance.
- `tests/integration/test_firecrawl_integration.py`: End-to-end multi-query pipeline validation across arbitrary categories (S26 Ultra, office chairs, running shoes, cordless drills, air fryers, etc.).
- `tests/providers/test_google_resilience.py`: Validates Grid v1/v2, Carousel v1/v2, List, and Unknown semantic parsing, candidate validation, CAPTCHA block detection, circuit breaker transitions, rate limiting, and extraction health.
- `tests/providers/test_google_scraper.py`: Validates localized price/currency normalization, URL unquoting, retailer cleaning, model conversions, and configuration flags.
- `tests/integration/test_search_flow.py`: Verifies multi-provider fault tolerance (if Google or Amazon is blocked, other live providers succeed).
- `tests/test_engine.py`: Verifies deduplication, attributes, recommendation scoring, and DEMO_MODE zero-fake-data enforcement.

### Optional Live Google Shopping Test:
```bash
RUN_GOOGLE_LIVE_TESTS=true PYTHONPATH=. .venv/bin/pytest tests/integration/test_google_scraper_live.py -v
```
*(Disabled by default to ensure local and CI test runs remain fast, reliable, and hermetic).*

