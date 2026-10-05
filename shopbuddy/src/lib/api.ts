/**
 * ShopBuddy AI API Client
 * Connects the frontend directly to the FastAPI shopping engine backend.
 * All product discovery, normalized offers, and recommendations originate here.
 */

export interface SearchIntentDTO {
  raw_query: string;
  provider_query: string;
  category?: string;
  category_confidence?: number;
  product_type?: string;
  brand?: string;
  model?: string;
  budget: {
    min?: number;
    max?: number;
    currency?: string;
  };
  use_cases: string[];
  requirements: string[];
  preferred_brands: string[];
  country: string;
  parser: 'llm' | 'rules';
}

export interface DynamicCardAttributeDTO {
  key: string;
  label: string;
  value: any;
  unit?: string;
}

export interface RecommendationBreakdownDTO {
  match_score: number;
  reasons: string[];
  drawbacks: string[];
  why_not_higher: string[];
}

export interface ProductOfferDTO {
  retailer: string;
  price: number;
  price_amount?: number;
  original_price?: number;
  currency: string;
  url: string;
  availability: string;
  seller?: string;
  seller_name?: string;
  rating?: number;
  shipping_cost?: number;
  warranty?: string;
  is_verified?: boolean;
  is_quick_commerce?: boolean;
  delivery_eta_minutes?: number;
  delivery_estimate?: string;
  pack_size?: string;
  unit_price?: number;
  unit_measure?: string;
  delivery_fee?: number;
  platform_fee?: number;
}


export interface ProductCardDTO {
  id: string;
  title: string;
  brand?: string;
  category_id?: string;
  image_url?: string;
  image_urls: string[];
  rating?: number;
  review_count?: number;
  best_price?: number;
  original_price?: number;
  currency: string;
  discount_percent?: number;
  primary_retailer: string;
  offers_count: number;
  offers?: ProductOfferDTO[];
  availability: 'in_stock' | 'limited' | 'out_of_stock' | 'preorder' | 'unknown';
  card_attributes: DynamicCardAttributeDTO[];
  recommendation: RecommendationBreakdownDTO;
  sources: string[];
  is_demo: boolean;
  last_updated: string;
  is_quick_commerce?: boolean;
  quick_commerce_eta?: string;
  best_unit_price?: string;
  data_coverage_score?: number;
}

export interface LiveProviderInfoDTO {
  name: string;
  label: string;
  configured: boolean;
  status: 'healthy' | 'degraded' | 'blocked' | 'unavailable' | 'configured';
  products_found?: number;
  offers_count?: number;
  latency_ms?: number;
  error?: string;
  is_demo: boolean;
  required_env: string[];
  countries: string[];
  rate_limit_per_second: number;
}

export interface PaginationMetadataDTO {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  total_offers: number;
  providers_contributing: number;
}

export interface SearchMetadataDTO {
  search_id: string;
  search_duration_ms: number;
  time_to_first_product_ms?: number;
  is_cached?: boolean;
  is_revalidating?: boolean;
  timing_breakdown?: Record<string, any>;
  providers_used: string[];
  products_found: number;
  deduped_count: number;
  total_offers?: number;
  providers_contributing?: number;
  pagination?: PaginationMetadataDTO;
  is_live: boolean;
  live_providers_configured: number;
  live_providers: LiveProviderInfoDTO[];
  freshness_label: string;
  is_demo: boolean;
  demo_mode_active: boolean;
  demo_notice?: string;
  unconfigured_notice?: string;
}

export interface SearchResponseDTO {
  query: string;
  intent: SearchIntentDTO;
  products: ProductCardDTO[];
  search_metadata: SearchMetadataDTO;
}

export interface CategoryDTO {
  id: string;
  name: string;
  department: string;
  keywords: string[];
  sort_order: number;
}

const rawApiUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
const API_BASE = rawApiUrl ? (rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl}/api`) : '/api';

const CLIENT_SEARCH_CACHE = new Map<string, { data: SearchResponseDTO; timestamp: number }>();

export function clearClientSearchCache(query?: string): void {
  if (!query) {
    CLIENT_SEARCH_CACHE.clear();
    return;
  }
  const prefix = query.toLowerCase().trim() + ':';
  for (const key of Array.from(CLIENT_SEARCH_CACHE.keys())) {
    if (key.startsWith(prefix)) {
      CLIENT_SEARCH_CACHE.delete(key);
    }
  }
}

export function getCachedSearch(
  query: string,
  currency: string = 'INR',
  sortBy: string = 'recommended',
  page: number = 1
): SearchResponseDTO | null {
  if (!query) return null;
  const key = `${query.toLowerCase().trim()}:${currency}:${sortBy}:${page}`;
  const entry = CLIENT_SEARCH_CACHE.get(key);
  if (entry && Date.now() - entry.timestamp < 5 * 60 * 1000) {
    return entry.data;
  }
  return null;
}

export async function searchProducts(
  query: string,
  country: string = 'IN',
  currency: string = 'INR',
  sortBy: string = 'recommended',
  page: number = 1,
  pageSize: number = 24,
  signal?: AbortSignal
): Promise<SearchResponseDTO> {
  const cacheKey = `${query.toLowerCase().trim()}:${currency}:${sortBy}:${page}`;
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      query,
      country,
      currency,
      sort_by: sortBy,
      page,
      page_size: pageSize,
    }),
  });

  if (!res.ok) {
    throw new Error(`Search request failed with HTTP ${res.status}`);
  }

  const data = await res.json();

  // If already standard SearchResponseDTO (from /api/v1/search)
  if (data.search_metadata && data.intent) {
    return data as SearchResponseDTO;
  }

  // Normalize UnifiedSearchResponse (from /api/search)
  const products: ProductCardDTO[] = (data.products || []).map((p: any) => ({
    id: p.id,
    title: p.title,
    brand: p.brand || undefined,
    category_id: p.category_id || undefined,
    image_url: p.image || p.image_urls?.[0],
    image_urls: p.image_urls || (p.image ? [p.image] : []),
    rating: p.rating,
    review_count: p.review_count,
    best_price: p.price_summary?.lowest_price ?? (p.offers?.[0]?.price ?? 0),
    original_price: p.offers?.[0]?.original_price,
    currency: p.price_summary?.currency || 'INR',
    discount_percent:
      p.offers?.[0]?.discount && p.offers?.[0]?.original_price
        ? Math.round((p.offers[0].discount / p.offers[0].original_price) * 100)
        : undefined,
    primary_retailer: p.offers?.[0]?.retailer || p.sources?.[0] || 'Unknown Retailer',
    offers_count: p.offers?.length || 1,
    offers: (p.offers || []).map((o: any) => ({
      retailer: o.retailer || o.source,
      price: o.price,
      original_price: o.original_price,
      currency: o.currency || 'INR',
      url: o.url,
      availability: o.availability || 'in_stock',
      seller_name: o.seller_name,
      rating: o.rating,
      shipping_cost: o.shipping_cost,
      is_verified: o.is_verified,
    })),
    availability: p.offers?.[0]?.availability || 'in_stock',
    card_attributes: p.card_attributes || [],
    recommendation: {
      match_score: p.recommendation?.match_score || 85,
      reasons: p.recommendation?.reasons || [],
      drawbacks: p.recommendation?.drawbacks || [],
      why_not_higher: p.recommendation?.why_not_higher || [],
    },
    sources: p.sources || (p.offers ? [...new Set(p.offers.map((o: any) => o.retailer || o.source))] : []),
    is_demo: false,
    last_updated: p.freshness_label || 'Price checked just now',
    is_quick_commerce: p.is_quick_commerce ?? (p.offers || []).some((o: any) => o.is_quick_commerce),
    quick_commerce_eta: p.quick_commerce_eta || (p.offers || []).find((o: any) => o.is_quick_commerce)?.delivery_estimate,
    best_unit_price: p.best_unit_price,
    data_coverage_score: p.data_coverage_score,
  }));

  const providersList: LiveProviderInfoDTO[] = Object.entries(data.providers || {}).map(
    ([name, info]: [string, any]) => {
      const statusStr = (info?.status || 'configured').toLowerCase();
      const validStatus: LiveProviderInfoDTO['status'] =
        statusStr === 'healthy' || statusStr === 'degraded' || statusStr === 'blocked' || statusStr === 'unavailable'
          ? statusStr
          : 'configured';

      return {
        name,
        label: name.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
        configured: validStatus !== 'unavailable',
        status: validStatus,
        products_found: info?.products_found || 0,
        offers_count: info?.offers_count || info?.products_found || 0,
        latency_ms: info?.latency_ms ? Math.round(info.latency_ms) : undefined,
        error: info?.error || undefined,
        is_demo: false,
        required_env: [],
        countries: ['IN', 'US', 'UK'],
        rate_limit_per_second: 2,
      };
    }
  );

  const totalOffers =
    data.pagination?.total_offers ||
    products.reduce((acc, p) => acc + (p.offers_count || 1), 0);

  const providersContributing =
    data.pagination?.providers_contributing ||
    providersList.filter((p) => (p.products_found || 0) > 0).length;

  const result: SearchResponseDTO = {
    query: data.query?.raw || query,
    intent: {
      raw_query: query,
      provider_query: data.query?.clean_query || query,
      category: data.query?.category || undefined,
      product_type: data.query?.product_type || undefined,
      brand: data.query?.brand || undefined,
      model: data.query?.model || undefined,
      budget: {
        min: data.query?.min_price,
        max: data.query?.max_price,
        currency: data.query?.currency || currency,
      },
      use_cases: data.query?.use_cases || [],
      requirements: data.query?.requirements || [],
      preferred_brands: data.query?.preferred_brands || [],
      country,
      parser: data.query?.parser || 'rules',
    },
    products,
    search_metadata: {
      search_id: data.search_id || 'search-1',
      search_duration_ms: data.search_duration_ms ? Math.round(data.search_duration_ms) : 1200,
      time_to_first_product_ms: data.time_to_first_product_ms ? Math.round(data.time_to_first_product_ms) : undefined,
      is_cached: Boolean(data.is_cached),
      is_revalidating: Boolean(data.is_revalidating),
      timing_breakdown: data.timing_breakdown || {},
      providers_used: Object.keys(data.providers || {}),
      products_found: data.pagination?.total || data.total_products_found || products.length,
      deduped_count: data.pagination?.total || data.deduped_count || products.length,
      total_offers: totalOffers,
      providers_contributing: providersContributing,
      pagination: data.pagination,
      is_live: true,
      live_providers_configured: providersList.filter((p) => p.status !== 'unavailable').length,
      live_providers: providersList,
      freshness_label: data.is_cached ? 'Instant Cached Results' : 'Live Real-Time Data',
      is_demo: false,
      demo_mode_active: false,
      demo_notice: undefined,
      unconfigured_notice: undefined,
    },
  };

  CLIENT_SEARCH_CACHE.set(cacheKey, { data: result, timestamp: Date.now() });
  return result;
}

export async function getProductDetail(productId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/products/${encodeURIComponent(productId)}`);
  if (!res.ok) {
    throw new Error(`Product fetch failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function getPriceHistory(productId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/products/${encodeURIComponent(productId)}/price-history`);
  if (!res.ok) {
    throw new Error(`Price history fetch failed with HTTP ${res.status}`);
  }
  return res.json();
}

export async function getCategories(): Promise<CategoryDTO[]> {
  try {
    const res = await fetch(`${API_BASE}/categories`);
    if (res.ok) {
      return res.json();
    }
  } catch (err) {
    console.warn('Could not fetch dynamic categories from backend', err);
  }
  return [];
}

export async function getSystemHealth(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/admin/health`);
    if (res.ok) return res.json();
  } catch {
    // Backend offline
  }
  return { status: 'offline', demo_mode: false };
}

export interface ComparisonProductItemDTO {
  id: string;
  title: string;
  brand?: string;
  model?: string;
  category_id?: string;
  image_url?: string;
  image_urls: string[];
  rating?: number;
  review_count?: number;
  best_price?: number;
  currency: string;
  primary_retailer?: string;
  offers_count: number;
  offers: ProductOfferDTO[];
  specifications: Record<string, any>;
  identifiers: Record<string, string>;
  condition: string;
}

export interface ScorecardDimensionDTO {
  dimension: string;
  scores: Record<string, number>;
  winner_id?: string;
  rationale: string;
}

export interface ComparisonAttributeRowDTO {
  key: string;
  label: string;
  values: Record<string, any>;
  unit?: string;
  winner_id?: string;
  winner_reason?: string;
  is_highlight: boolean;
  is_neutral: boolean;
  is_different?: boolean;
  sources?: Record<string, string>;
  verified?: boolean;
  score_explanation?: Record<string, string>;
  raw_values?: Record<string, any>;
}

export interface ComparisonCategoryScoreDTO {
  name: string;
  weight: number;
  scores: Record<string, number>;
  winner_id?: string;
  winner_reason?: string;
  reasons: Record<string, string[]>;
  attributes: ComparisonAttributeRowDTO[];
}

export interface PriceComparisonDTO {
  min_price?: number;
  max_price?: number;
  price_difference?: number;
  percentage_difference?: number;
  cheapest_product_id?: string;
  currency: string;
  product_prices: Record<string, number | null>;
  best_retailers: Record<string, string | null>;
  best_offer_urls: Record<string, string | null>;
  value_scores: Record<string, number>;
  value_rationale: string;
}

export interface RatingComparisonDTO {
  product_ratings: Record<
    string,
    {
      rating: number | null;
      review_count: number | null;
      formatted: string;
      stars_count: number;
    }
  >;
  highest_rated_id?: string;
  rating_advantage?: string;
}

export interface ReviewInsightsDTO {
  insights: Record<
    string,
    {
      likes: string[];
      complaints: string[];
      summary: string;
    }
  >;
  available: boolean;
  status_message: string;
}

export interface ComparisonSectionDTO {
  id: string;
  title: string;
  description?: string;
  is_default_expanded?: boolean;
  attributes: ComparisonAttributeRowDTO[];
}

export interface ProductBuyingInsightsDTO {
  product_id: string;
  why_choose: string[];
  considerations: string[];
  best_suited_for: string;
}

export interface ComparisonAIVerdictDTO {
  best_overall_id?: string;
  best_overall_title?: string;
  best_value_id?: string;
  best_value_title?: string;
  verdict_summary: string;
  confidence?: number;
  best_for?: string[];
  why_it_wins?: string;
  why_best_value?: string;
  key_differences: string[];
  trade_offs?: Record<string, string[]>;
  buying_recommendations?: Record<string, string>;
}

export interface ComparisonResponseDTO {
  products: ComparisonProductItemDTO[];
  verdict: ComparisonAIVerdictDTO;
  scorecard: ScorecardDimensionDTO[];
  sections: ComparisonSectionDTO[];
  buying_insights: ProductBuyingInsightsDTO[];
  category_name?: string;
  generated_at: string;
  ai_powered: boolean;
  product_type?: string;
  categories?: ComparisonCategoryScoreDTO[];
  overall_scores?: Record<string, number>;
  overall_winner_id?: string;
  overall_winner_reason?: string;
  price_comparison?: PriceComparisonDTO;
  rating_comparison?: RatingComparisonDTO;
  review_insights?: ReviewInsightsDTO;
  data_coverage?: Record<string, number>;
  available_specs_count?: Record<string, number>;
}


export async function compareProducts(productIds: string[]): Promise<ComparisonResponseDTO> {
  const queryParam = productIds.map(encodeURIComponent).join(',');
  const res = await fetch(`${API_BASE}/products/compare?ids=${queryParam}`);
  if (!res.ok) {
    throw new Error(`Comparison request failed with HTTP ${res.status}`);
  }
  return res.json();
}

