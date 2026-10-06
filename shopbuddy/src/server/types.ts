/**
 * Server Data Contracts for ShopBuddy Engine
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
  specifications?: Record<string, any>;
  description?: string;
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

export interface CatalogProductRecord {
  id: string;
  title: string;
  brand?: string;
  model?: string;
  category_id?: string;
  description?: string;
  rating?: number;
  review_count?: number;
  image_urls: string[];
  attributes?: Record<string, any>;
  offers: Array<{
    retailer: string;
    seller?: string;
    price: number;
    original_price?: number;
    currency: string;
    url: string;
    availability: string;
    delivery_estimate?: string;
    warranty?: string;
  }>;
  price_history?: Array<{
    retailer: string;
    price: number;
    currency: string;
    date: string;
  }>;
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

