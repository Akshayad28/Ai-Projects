# Firecrawl Provider for ShopBuddy

The Firecrawl provider (`backend/app/providers/firecrawl/`) integrates the official Firecrawl API (`firecrawl-py`) as a first-class web discovery and structured product extraction provider in the ShopBuddy architecture.

It enables universal product search across the open web, discovering unknown retailers, direct-to-consumer (D2C) brands, specialty stores, and niche product pages without requiring pre-integrated merchant APIs or category restrictions.

---

## 1. Obtaining a Firecrawl API Key

1. Visit [firecrawl.dev](https://firecrawl.dev) and sign up for an account.
2. Navigate to your dashboard to obtain your API key (`fc-...`).
3. Connect the CLI or configure your backend environment directly:
   ```bash
   npx -y firecrawl-cli@latest init --all -k <YOUR_API_KEY>
   ```

---

## 2. Environment Variables

Configure the following variables in `backend/.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `FIRECRAWL_API_KEY` | string | `""` | Official Firecrawl API key (`fc-...`). If missing, provider status = `UNAVAILABLE`. Never exposed to frontend. |
| `FIRECRAWL_ENABLED` | bool | `true` | Master switch to enable or disable the Firecrawl provider. |
| `FIRECRAWL_SEARCH_ENABLED` | bool | `true` | Enables Firecrawl web search discovery. |
| `FIRECRAWL_SCRAPE_ENABLED` | bool | `true` | Enables page scraping for discovered candidate URLs. |
| `FIRECRAWL_EXTRACTION_ENABLED` | bool | `true` | Enables JSON schema-based structured product extraction. |
| `FIRECRAWL_MAX_SEARCH_RESULTS` | int | `20` | Maximum web search results retrieved per discovery query. |
| `FIRECRAWL_MAX_SCRAPE_PAGES` | int | `10` | Maximum candidate product detail pages scraped per search. |
| `FIRECRAWL_REQUEST_TIMEOUT_SECONDS` | int | `30` | Network request timeout for search and scrape API calls. |
| `FIRECRAWL_CONCURRENCY` | int | `5` | Maximum concurrent scraping requests allowed. |
| `FIRECRAWL_CACHE_TTL_SECONDS` | int | `900` | TTL in seconds for search and scraped page caches (default 15 minutes). |

---

## 3. How It Works

### Staged Discovery & Extraction Pipeline
1. **Query Strategy**:
   - Takes the user query and intent constraints (budget, currency, attributes).
   - Generates 1 primary discovery query and up to 2 refined/geographic queries when appropriate (e.g. price-bounded query).
   - Deduplicates search queries to avoid redundant API calls.
2. **Web Search & Provenance**:
   - Discovers web results via Firecrawl `/search`.
   - Captures title, URL, snippet, domain, query, and timestamp provenance.
3. **URL Classification & Filtering**:
   - Analyzes URLs to classify into: `PRODUCT_PAGE`, `RETAILER_CATEGORY`, `SEARCH_PAGE`, `ARTICLE_REVIEW`, and `IRRELEVANT_PAGE`.
   - Filters out non-product pages, video sites, search engines, and generic homepages.
4. **Concurrent Bounded Scraping**:
   - Scrapes prioritized candidate product URLs using bounded concurrency (`asyncio.Semaphore(concurrency)`).
   - Staggers requests (0.3s) to prevent bursting against provider rate limits.
5. **Multi-Tier Structured Extraction**:
   - **Tier 1 (Structured Schema)**: Firecrawl LLM JSON-schema extraction using strict prompt preventing hallucinations. Dynamic attributes support arbitrary product domains (fashion, tools, furniture, electronics, etc.).
   - **Tier 2 (Schema.org / JSON-LD)**: Extracts `Product`, `Offer`, `AggregateRating`, `Brand` from HTML structured data.
   - **Tier 3 (OpenGraph & Meta)**: Extracts canonical URLs, og:image, og:price, and twitter tags.
6. **Validation & Sanitization**:
   - Validates titles, numeric prices, currency ISO normalization, rating ranges (0-5), non-negative review counts, and real image URLs.
   - Protects against prompt-injection by treating all scraped page content strictly as untrusted data.
7. **Identity Matching & Canonical Offer Aggregation**:
   - Maps extracted products into canonical `RawProduct` and `RawOffer` models.
   - Merges with offers from Amazon, Flipkart, eBay, and Google Shopping via `ProductIdentityEngine`.
   - Preserves all retailer offers without overwriting or short-circuiting.

---

## 4. Rate Limiting & Concurrency

- **Bounded Concurrency**: Uses `FirecrawlRateLimiter` with an internal `asyncio.Semaphore(max_concurrency)` and token bucket algorithm to respect provider credit budgets.
- **Circuit Breaker**: Detects consecutive failures or rate limit exhaustion (HTTP 429). Trips circuit to `BLOCKED`/`DEGRADED` for a 15-minute cooldown, allowing other providers (Amazon, Flipkart, Google) to continue uninterrupted.

---

## 5. Caching

- `FirecrawlCache`: In-memory async cache for search results and scraped URLs.
- Keys incorporate query text, country, currency, and URL.
- Cached items retain original timestamps and record `from_cache=True` in internal metrics.

---

## 6. Provider Diagnostics

Firecrawl reports granular diagnostics accessible via `/api/v1/search` and `/api/v1/providers/health`:

```json
{
  "firecrawl": {
    "status": "HEALTHY",
    "search_attempted": true,
    "search_results": 20,
    "product_urls_detected": 14,
    "pages_scraped": 10,
    "extraction_attempted": 10,
    "products_extracted": 8,
    "products_validated": 7,
    "products_rejected": 1,
    "offers_extracted": 7,
    "errors": 0,
    "raw": 7,
    "normalized": 7,
    "canonical": 6,
    "offers": 7
  }
}
```

---

## 7. Testing

### Run Unit Tests (20 test cases):
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/providers/test_firecrawl.py -v
```

### Run Integration Tests (11 test cases):
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/integration/test_firecrawl_integration.py -v
```

### Run Multi-Provider Integration Test:
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/integration/test_firecrawl_integration.py -k test_multi_provider_parallel_execution -v
```
