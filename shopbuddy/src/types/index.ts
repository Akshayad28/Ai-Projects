// ============================================
// SHOPBUDDY AI — Core Types
// ============================================

// --- Product Types ---
export interface Product {
  id: string;
  brand: string;
  name: string;
  description: string;
  categoryId: string;
  canonicalUrl: string;
  imageUrls: string[];
  attributes: Record<string, string | number | boolean>;
  rating: number;
  reviewCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProductVariant {
  id: string;
  productId: string;
  sku: string;
  gtin?: string;
  mpn?: string;
  color?: string;
  size?: string;
  storage?: string;
  capacity?: string;
  condition: 'new' | 'refurbished' | 'used';
  region?: string;
}

export interface Offer {
  id: string;
  productVariantId: string;
  retailerId: string;
  sellerId?: string;
  price: number;
  currency: CurrencyCode;
  originalPrice?: number;
  shippingCost: number;
  tax?: number;
  importDuty?: number;
  coupon?: string;
  couponDiscount?: number;
  cashback?: number;
  availability: AvailabilityStatus;
  deliveryEstimate: string;
  returnPolicyId?: string;
  warrantyId?: string;
  productUrl: string;
  lastChecked: string;
}

export type AvailabilityStatus =
  | 'in_stock'
  | 'low_stock'
  | 'out_of_stock'
  | 'pre_order'
  | 'discontinued'
  | 'unknown';

// --- Retailer & Seller ---
export interface Retailer {
  id: string;
  name: string;
  logoUrl: string;
  website: string;
  trustScore: number;
}

export interface Seller {
  id: string;
  name: string;
  retailerId: string;
  rating: number;
  tenure?: string;
  fulfillment: 'marketplace' | 'first_party' | 'fulfilled_by_retailer';
}

// --- Price ---
export interface PricePoint {
  date: string;
  price: number;
  retailerId: string;
}

export interface PriceHistory {
  productId: string;
  currency: CurrencyCode;
  data: PricePoint[];
  currentPrice: number;
  ninetyDayLow: number;
  ninetyDayAvg: number;
  historicalHigh: number;
  historicalLow: number;
}

export type PriceAdvice =
  | 'buy_now'
  | 'good_price'
  | 'normal_price'
  | 'wait'
  | 'price_high'
  | 'insufficient_data';

export interface PriceSummary {
  currentPrice: number;
  originalPrice?: number;
  discount?: number;
  currency: CurrencyCode;
  advice: PriceAdvice;
  advisoryText: string;
  percentBelowAvg?: number;
  trueCost?: TrueCost;
}

export interface TrueCost {
  listedPrice: number;
  shipping: number;
  tax: number;
  importDuty: number;
  couponDiscount: number;
  cashback: number;
  estimatedTotal: number;
  isEstimate: boolean;
}

// --- Recommendation ---
export interface RecommendationScore {
  overall: number;
  breakdown: RecommendationBreakdown[];
  reasons: string[];
  drawbacks: string[];
  whyNotHigher?: string[];
}

export interface RecommendationBreakdown {
  attribute: string;
  score: number;
  weight: number;
  label: string;
}

// --- Category ---
export interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string;
  parentId?: string;
  attributes: CategoryAttribute[];
}

export interface CategoryAttribute {
  key: string;
  label: string;
  weight: number;
  type: 'number' | 'text' | 'boolean' | 'enum';
}

// --- Reviews ---
export interface ReviewAnalysis {
  productId: string;
  totalReviewed: number;
  dateRange: string;
  sourceCoverage: string[];
  confidence: number;
  themes: ReviewTheme[];
  suspiciousPatterns?: string[];
}

export interface ReviewTheme {
  topic: string;
  sentiment: 'positive' | 'negative' | 'mixed';
  mentions: number;
  summary: string;
}

// --- Search ---
export interface SearchIntent {
  query: string;
  category?: string;
  budget?: number;
  currency: CurrencyCode;
  useCase?: string;
  requirements: string[];
  constraints: string[];
  preferences: string[];
  exclusions: string[];
  location?: string;
}

export interface SearchResult {
  product: Product;
  variant: ProductVariant;
  bestOffer: Offer;
  recommendation: RecommendationScore;
  priceSummary: PriceSummary;
  retailerCount: number;
}

export interface WishlistItem {
  id: string;
  productId: string;
  product?: Product;
  variant?: ProductVariant;
  bestOffer?: Offer;
  addedAt: string;
  targetPrice?: number;
  currency?: CurrencyCode;
  priceWhenAdded?: number;
  recommendation?: RecommendationScore;
  historicalAvg?: number;
  historicalLow?: number;
  priceMovement?: 'up' | 'down' | 'stable';
}

// --- Alerts ---
export interface PriceAlert {
  id: string;
  productId: string;
  product: Product;
  type: AlertType;
  targetPrice?: number;
  percentageDrop?: number;
  isActive: boolean;
  createdAt: string;
  lastTriggered?: string;
}

export type AlertType =
  | 'target_price'
  | 'historical_low'
  | 'percentage_drop'
  | 'back_in_stock'
  | 'coupon_available'
  | 'better_alternative'
  | 'price_recovery';

// --- Shopping Mission ---
export interface ShoppingMission {
  id: string;
  title: string;
  description: string;
  totalBudget: number;
  currency: CurrencyCode;
  items: ShoppingMissionItem[];
  createdAt: string;
  status: 'active' | 'completed' | 'paused';
}

export interface ShoppingMissionItem {
  id: string;
  category: string;
  allocatedBudget: number;
  selectedProduct?: Product;
  selectedOffer?: Offer;
  status: 'searching' | 'selected' | 'purchased';
}

// --- Currency ---
export type CurrencyCode =
  | 'INR'
  | 'USD'
  | 'EUR'
  | 'GBP'
  | 'AED'
  | 'CAD'
  | 'AUD'
  | 'JPY'
  | 'SGD';

export interface Currency {
  code: CurrencyCode;
  symbol: string;
  name: string;
  rate: number; // relative to USD
}

// --- AI ---
export interface AIResearchStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete' | 'error';
  detail?: string;
}

export interface AIActivityItem {
  id: string;
  action: string;
  detail?: string;
  timestamp: string;
}

export interface AIChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

// --- Comparison ---
export interface ComparisonItem {
  product: Product;
  variant: ProductVariant;
  bestOffer: Offer;
  recommendation: RecommendationScore;
  priceSummary: PriceSummary;
  specs: Record<string, string | number | boolean>;
}

export interface ComparisonSummary {
  analysis: string;
  bestFor: Record<string, string>;
  keyTradeoff: string;
}

// --- Notifications ---
export interface Notification {
  id: string;
  type: 'price_drop' | 'back_in_stock' | 'target_reached' | 'better_alternative' | 'info';
  title: string;
  message: string;
  productId?: string;
  read: boolean;
  createdAt: string;
}

// --- User ---
export interface UserPreferences {
  budgetRange?: [number, number];
  preferredBrands: string[];
  dislikedBrands: string[];
  qualityPriority: 'high' | 'medium' | 'low';
  priceSensitivity: 'high' | 'medium' | 'low';
  deliveryPriority: 'high' | 'medium' | 'low';
  warrantyPriority: 'high' | 'medium' | 'low';
  sustainabilityPreference: boolean;
  country: string;
  currency: CurrencyCode;
}

// --- Return Policy ---
export interface ReturnPolicy {
  id: string;
  retailerId: string;
  returnWindow: number; // days
  conditions: string;
  freeReturn: boolean;
}

// --- Warranty ---
export interface Warranty {
  id: string;
  duration: string;
  type: 'manufacturer' | 'retailer' | 'extended';
  coverage: string;
}

// --- Filter ---
export interface FilterState {
  budget: [number, number];
  brands: string[];
  rating: number;
  availability: AvailabilityStatus[];
  retailers: string[];
  features: string[];
  shipping: 'free' | 'any';
  returnPolicy: 'any' | '7_day' | '14_day' | '30_day';
  sellerType: 'any' | 'first_party' | 'marketplace';
  condition: 'any' | 'new' | 'refurbished';
  discount: number;
  recommendationConfidence: number;
}

// --- Dashboard ---
export interface DashboardMetrics {
  wishlistItems: number;
  priceDrops: number;
  backInStock: number;
  potentialSavings: number;
}
