// ============================================
// SHOPBUDDY AI — Mock Data: Products
// ============================================

import type {
  Product,
  ProductVariant,
  Offer,
  Retailer,
  Seller,
  PriceHistory,
  PricePoint,
  RecommendationScore,
  PriceSummary,
  ReviewAnalysis,
  SearchResult,
  Category,
  WishlistItem,
  PriceAlert,
  Notification,
  ComparisonSummary,
  Currency,
  CurrencyCode,
  ShoppingMission,
  DashboardMetrics,
} from '@/types';

// --- Retailers ---
export const mockRetailers: Retailer[] = [
  { id: 'amazon-in', name: 'Amazon', logoUrl: '/retailers/amazon.svg', website: 'https://amazon.in', trustScore: 92 },
  { id: 'flipkart', name: 'Flipkart', logoUrl: '/retailers/flipkart.svg', website: 'https://flipkart.com', trustScore: 90 },
  { id: 'croma', name: 'Croma', logoUrl: '/retailers/croma.svg', website: 'https://croma.com', trustScore: 88 },
  { id: 'reliance-digital', name: 'Reliance Digital', logoUrl: '/retailers/reliance.svg', website: 'https://reliancedigital.in', trustScore: 85 },
  { id: 'vijay-sales', name: 'Vijay Sales', logoUrl: '/retailers/vijay.svg', website: 'https://vijaysales.com', trustScore: 83 },
];

// --- Sellers ---
export const mockSellers: Seller[] = [
  { id: 'seller-1', name: 'Appario Retail', retailerId: 'amazon-in', rating: 4.3, tenure: '7 years', fulfillment: 'fulfilled_by_retailer' },
  { id: 'seller-2', name: 'RetailNet', retailerId: 'flipkart', rating: 4.5, tenure: '5 years', fulfillment: 'first_party' },
  { id: 'seller-3', name: 'TrueComRetail', retailerId: 'amazon-in', rating: 4.1, tenure: '3 years', fulfillment: 'marketplace' },
];

// --- Categories ---
export const mockCategories: Category[] = [
  {
    id: 'headphones',
    name: 'Headphones',
    slug: 'headphones',
    icon: 'Headphones',
    attributes: [
      { key: 'performance', label: 'Performance', weight: 0.25, type: 'number' },
      { key: 'features', label: 'Features', weight: 0.20, type: 'number' },
      { key: 'price', label: 'Price', weight: 0.20, type: 'number' },
      { key: 'reliability', label: 'Reliability', weight: 0.15, type: 'number' },
      { key: 'reviews', label: 'Reviews', weight: 0.10, type: 'number' },
      { key: 'warranty', label: 'Warranty', weight: 0.05, type: 'number' },
      { key: 'priceHistory', label: 'Price History', weight: 0.05, type: 'number' },
    ],
  },
  {
    id: 'laptops',
    name: 'Laptops',
    slug: 'laptops',
    icon: 'Laptop',
    attributes: [
      { key: 'performance', label: 'Performance', weight: 0.25, type: 'number' },
      { key: 'display', label: 'Display', weight: 0.15, type: 'number' },
      { key: 'portability', label: 'Portability', weight: 0.15, type: 'number' },
      { key: 'price', label: 'Price', weight: 0.15, type: 'number' },
      { key: 'battery', label: 'Battery', weight: 0.10, type: 'number' },
      { key: 'reviews', label: 'Reviews', weight: 0.10, type: 'number' },
      { key: 'warranty', label: 'Warranty', weight: 0.05, type: 'number' },
      { key: 'priceHistory', label: 'Price History', weight: 0.05, type: 'number' },
    ],
  },
  {
    id: 'mobile-phones',
    name: 'Mobile Phones',
    slug: 'mobile-phones',
    icon: 'Smartphone',
    attributes: [
      { key: 'performance', label: 'Performance', weight: 0.20, type: 'number' },
      { key: 'camera', label: 'Camera', weight: 0.20, type: 'number' },
      { key: 'display', label: 'Display', weight: 0.15, type: 'number' },
      { key: 'battery', label: 'Battery', weight: 0.15, type: 'number' },
      { key: 'price', label: 'Price', weight: 0.15, type: 'number' },
      { key: 'reviews', label: 'Reviews', weight: 0.10, type: 'number' },
      { key: 'priceHistory', label: 'Price History', weight: 0.05, type: 'number' },
    ],
  },
  { id: 'electronics', name: 'Electronics', slug: 'electronics', icon: 'Cpu', attributes: [] },
  { id: 'tvs', name: 'TVs', slug: 'tvs', icon: 'Tv', attributes: [] },
  { id: 'cameras', name: 'Cameras', slug: 'cameras', icon: 'Camera', attributes: [] },
  { id: 'gaming', name: 'Gaming', slug: 'gaming', icon: 'Gamepad2', attributes: [] },
  { id: 'footwear', name: 'Footwear', slug: 'footwear', icon: 'Footprints', attributes: [] },
  { id: 'furniture', name: 'Furniture', slug: 'furniture', icon: 'Armchair', attributes: [] },
  { id: 'kitchen', name: 'Kitchen', slug: 'kitchen', icon: 'CookingPot', attributes: [] },
  { id: 'fitness', name: 'Fitness', slug: 'fitness', icon: 'Dumbbell', attributes: [] },
  { id: 'skincare', name: 'Skincare', slug: 'skincare', icon: 'Sparkles', attributes: [] },
];

// --- Products ---
export const mockProducts: Product[] = [
  {
    id: 'sony-wh1000xm5',
    brand: 'Sony',
    name: 'WH-1000XM5',
    description: 'Industry-leading noise cancelling wireless headphones with Auto NC Optimizer, crystal clear hands-free calling, and up to 30-hour battery life.',
    categoryId: 'headphones',
    canonicalUrl: '/product/sony-wh1000xm5',
    imageUrls: ['/products/sony-xm5-1.jpg', '/products/sony-xm5-2.jpg'],
    attributes: {
      type: 'Over-ear',
      connectivity: 'Bluetooth 5.2',
      anc: true,
      batteryLife: '30 hours',
      weight: '250g',
      codec: 'LDAC, AAC, SBC',
      microphone: true,
      multipoint: true,
      foldable: false,
      waterResistance: 'None',
      driverSize: '30mm',
      frequencyResponse: '4Hz - 40,000Hz',
    },
    rating: 4.6,
    reviewCount: 12847,
    createdAt: '2024-01-15T00:00:00Z',
    updatedAt: '2024-09-28T12:00:00Z',
  },
  {
    id: 'bose-qc-ultra',
    brand: 'Bose',
    name: 'QuietComfort Ultra Headphones',
    description: 'Spatial audio and world-class noise cancellation. Immersive audio experience with CustomTune technology.',
    categoryId: 'headphones',
    canonicalUrl: '/product/bose-qc-ultra',
    imageUrls: ['/products/bose-qc-ultra-1.jpg'],
    attributes: {
      type: 'Over-ear',
      connectivity: 'Bluetooth 5.3',
      anc: true,
      batteryLife: '24 hours',
      weight: '250g',
      codec: 'aptX Adaptive, AAC, SBC',
      microphone: true,
      multipoint: true,
      foldable: true,
      waterResistance: 'None',
      driverSize: '35mm',
    },
    rating: 4.5,
    reviewCount: 8934,
    createdAt: '2024-02-10T00:00:00Z',
    updatedAt: '2024-09-27T12:00:00Z',
  },
  {
    id: 'sennheiser-momentum4',
    brand: 'Sennheiser',
    name: 'Momentum 4 Wireless',
    description: 'Audiophile-grade wireless headphones with adaptive noise cancellation, 60-hour battery, and premium materials.',
    categoryId: 'headphones',
    canonicalUrl: '/product/sennheiser-momentum4',
    imageUrls: ['/products/sennheiser-m4-1.jpg'],
    attributes: {
      type: 'Over-ear',
      connectivity: 'Bluetooth 5.2',
      anc: true,
      batteryLife: '60 hours',
      weight: '293g',
      codec: 'aptX, aptX Adaptive, AAC, SBC',
      microphone: true,
      multipoint: true,
      foldable: true,
      waterResistance: 'None',
      driverSize: '42mm',
    },
    rating: 4.4,
    reviewCount: 5621,
    createdAt: '2024-01-20T00:00:00Z',
    updatedAt: '2024-09-25T12:00:00Z',
  },
  {
    id: 'apple-airpods-max',
    brand: 'Apple',
    name: 'AirPods Max',
    description: 'High-fidelity audio with Active Noise Cancellation, Transparency mode, and spatial audio with dynamic head tracking.',
    categoryId: 'headphones',
    canonicalUrl: '/product/apple-airpods-max',
    imageUrls: ['/products/airpods-max-1.jpg'],
    attributes: {
      type: 'Over-ear',
      connectivity: 'Bluetooth 5.0',
      anc: true,
      batteryLife: '20 hours',
      weight: '384g',
      codec: 'AAC',
      microphone: true,
      multipoint: false,
      foldable: false,
      waterResistance: 'None',
      driverSize: '40mm',
    },
    rating: 4.7,
    reviewCount: 21340,
    createdAt: '2023-06-15T00:00:00Z',
    updatedAt: '2024-09-26T12:00:00Z',
  },
  {
    id: 'jbl-tour-one-m2',
    brand: 'JBL',
    name: 'Tour One M2',
    description: 'Premium wireless headphones with True Adaptive Noise Cancelling, Hi-Res Audio, and 50-hour battery life.',
    categoryId: 'headphones',
    canonicalUrl: '/product/jbl-tour-one-m2',
    imageUrls: ['/products/jbl-tour-1.jpg'],
    attributes: {
      type: 'Over-ear',
      connectivity: 'Bluetooth 5.3',
      anc: true,
      batteryLife: '50 hours',
      weight: '268g',
      codec: 'LDAC, AAC, SBC',
      microphone: true,
      multipoint: true,
      foldable: true,
      waterResistance: 'None',
      driverSize: '40mm',
    },
    rating: 4.3,
    reviewCount: 3456,
    createdAt: '2024-03-01T00:00:00Z',
    updatedAt: '2024-09-24T12:00:00Z',
  },
  {
    id: 'samsung-galaxy-s24-ultra',
    brand: 'Samsung',
    name: 'Galaxy S24 Ultra',
    description: 'The ultimate Galaxy experience with built-in AI, a 200MP camera, titanium frame, and S Pen.',
    categoryId: 'mobile-phones',
    canonicalUrl: '/product/samsung-galaxy-s24-ultra',
    imageUrls: ['/products/s24-ultra-1.jpg'],
    attributes: {
      display: '6.8" Dynamic AMOLED 2X',
      processor: 'Snapdragon 8 Gen 3',
      ram: '12GB',
      storage: '256GB',
      camera: '200MP + 50MP + 12MP + 10MP',
      battery: '5000mAh',
      os: 'Android 14 / One UI 6.1',
    },
    rating: 4.5,
    reviewCount: 18234,
    createdAt: '2024-01-17T00:00:00Z',
    updatedAt: '2024-09-28T12:00:00Z',
  },
];

// --- Product Variants ---
export const mockVariants: ProductVariant[] = [
  { id: 'sony-xm5-black', productId: 'sony-wh1000xm5', sku: 'WH1000XM5/B', gtin: '4548736143364', color: 'Black', condition: 'new' },
  { id: 'sony-xm5-silver', productId: 'sony-wh1000xm5', sku: 'WH1000XM5/S', gtin: '4548736143371', color: 'Silver', condition: 'new' },
  { id: 'bose-qc-ultra-black', productId: 'bose-qc-ultra', sku: 'BQCUH-BLK', color: 'Black', condition: 'new' },
  { id: 'senn-m4-black', productId: 'sennheiser-momentum4', sku: 'M4AEBT-BLK', color: 'Black', condition: 'new' },
  { id: 'airpods-max-silver', productId: 'apple-airpods-max', sku: 'MGYJ3ZM/A', color: 'Silver', condition: 'new' },
  { id: 'jbl-tour-black', productId: 'jbl-tour-one-m2', sku: 'JBLTOURON2BLK', color: 'Black', condition: 'new' },
  { id: 's24-ultra-256', productId: 'samsung-galaxy-s24-ultra', sku: 'SM-S928B/DS', storage: '256GB', color: 'Titanium Black', condition: 'new' },
];

// --- Offers ---
export const mockOffers: Offer[] = [
  {
    id: 'offer-1',
    productVariantId: 'sony-xm5-black',
    retailerId: 'amazon-in',
    sellerId: 'seller-1',
    price: 13499,
    currency: 'INR',
    originalPrice: 14990,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '2-3 days',
    productUrl: 'https://amazon.in/dp/B0BS3KS8BT',
    lastChecked: '2024-09-28T10:30:00Z',
  },
  {
    id: 'offer-2',
    productVariantId: 'sony-xm5-black',
    retailerId: 'flipkart',
    sellerId: 'seller-2',
    price: 13999,
    currency: 'INR',
    originalPrice: 14990,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '2-4 days',
    productUrl: 'https://flipkart.com/sony-wh1000xm5',
    lastChecked: '2024-09-28T10:25:00Z',
  },
  {
    id: 'offer-3',
    productVariantId: 'sony-xm5-black',
    retailerId: 'croma',
    price: 14490,
    currency: 'INR',
    originalPrice: 14990,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '3-5 days',
    productUrl: 'https://croma.com/sony-wh1000xm5',
    lastChecked: '2024-09-28T09:45:00Z',
  },
  {
    id: 'offer-4',
    productVariantId: 'bose-qc-ultra-black',
    retailerId: 'amazon-in',
    sellerId: 'seller-1',
    price: 24900,
    currency: 'INR',
    originalPrice: 29900,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '1-2 days',
    productUrl: 'https://amazon.in/dp/B0CDX2GN9W',
    lastChecked: '2024-09-28T10:28:00Z',
  },
  {
    id: 'offer-5',
    productVariantId: 'bose-qc-ultra-black',
    retailerId: 'flipkart',
    price: 25490,
    currency: 'INR',
    originalPrice: 29900,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '2-3 days',
    productUrl: 'https://flipkart.com/bose-qc-ultra',
    lastChecked: '2024-09-28T10:20:00Z',
  },
  {
    id: 'offer-6',
    productVariantId: 'senn-m4-black',
    retailerId: 'amazon-in',
    price: 18990,
    currency: 'INR',
    originalPrice: 24990,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '2-3 days',
    productUrl: 'https://amazon.in/sennheiser-m4',
    lastChecked: '2024-09-28T10:32:00Z',
  },
  {
    id: 'offer-7',
    productVariantId: 'airpods-max-silver',
    retailerId: 'amazon-in',
    price: 49900,
    currency: 'INR',
    originalPrice: 59900,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '1-2 days',
    productUrl: 'https://amazon.in/airpods-max',
    lastChecked: '2024-09-28T10:35:00Z',
  },
  {
    id: 'offer-8',
    productVariantId: 'jbl-tour-black',
    retailerId: 'amazon-in',
    price: 14999,
    currency: 'INR',
    originalPrice: 19999,
    shippingCost: 0,
    availability: 'in_stock',
    deliveryEstimate: '2-3 days',
    productUrl: 'https://amazon.in/jbl-tour-one',
    lastChecked: '2024-09-28T10:38:00Z',
  },
  {
    id: 'offer-9',
    productVariantId: 'jbl-tour-black',
    retailerId: 'flipkart',
    price: 14499,
    currency: 'INR',
    originalPrice: 19999,
    shippingCost: 99,
    availability: 'low_stock',
    deliveryEstimate: '3-5 days',
    productUrl: 'https://flipkart.com/jbl-tour-one',
    lastChecked: '2024-09-28T10:15:00Z',
  },
];

// --- Recommendations ---
export const mockRecommendations: Record<string, RecommendationScore> = {
  'sony-wh1000xm5': {
    overall: 94,
    breakdown: [
      { attribute: 'requirements', score: 96, weight: 0.25, label: 'Requirements Match' },
      { attribute: 'features', score: 93, weight: 0.20, label: 'Features' },
      { attribute: 'price', score: 91, weight: 0.20, label: 'Price' },
      { attribute: 'reviews', score: 95, weight: 0.15, label: 'Reviews' },
      { attribute: 'reliability', score: 94, weight: 0.10, label: 'Reliability' },
      { attribute: 'availability', score: 100, weight: 0.10, label: 'Availability' },
    ],
    reasons: [
      'Meets your ₹15,000 budget',
      'Industry-leading active noise cancellation',
      'Excellent comfort for extended wear (6+ hours)',
      '30-hour battery exceeds your requirement',
      'Current price is 8.8% below 90-day average',
      'Strong long-term review sentiment across 12,847 reviews',
    ],
    drawbacks: [
      'Microphone performance is average in noisy environments',
      'No aptX codec support',
      'Cannot fold flat for travel',
    ],
  },
  'bose-qc-ultra': {
    overall: 89,
    breakdown: [
      { attribute: 'requirements', score: 92, weight: 0.25, label: 'Requirements Match' },
      { attribute: 'features', score: 90, weight: 0.20, label: 'Features' },
      { attribute: 'price', score: 72, weight: 0.20, label: 'Price' },
      { attribute: 'reviews', score: 93, weight: 0.15, label: 'Reviews' },
      { attribute: 'reliability', score: 95, weight: 0.10, label: 'Reliability' },
      { attribute: 'availability', score: 100, weight: 0.10, label: 'Availability' },
    ],
    reasons: [
      'Premium spatial audio experience',
      'Excellent noise cancellation',
      'Very comfortable for long flights',
      'Foldable design for travel',
      'aptX Adaptive codec support',
    ],
    drawbacks: [
      'Exceeds your ₹15,000 budget by ₹9,900',
      'Shorter battery life (24 hours vs 30 hours)',
      'Premium pricing compared to competitors',
    ],
    whyNotHigher: [
      'Price exceeds stated budget significantly',
      'Battery life is below average for this segment',
    ],
  },
  'sennheiser-momentum4': {
    overall: 87,
    breakdown: [
      { attribute: 'requirements', score: 88, weight: 0.25, label: 'Requirements Match' },
      { attribute: 'features', score: 91, weight: 0.20, label: 'Features' },
      { attribute: 'price', score: 68, weight: 0.20, label: 'Price' },
      { attribute: 'reviews', score: 89, weight: 0.15, label: 'Reviews' },
      { attribute: 'reliability', score: 92, weight: 0.10, label: 'Reliability' },
      { attribute: 'availability', score: 100, weight: 0.10, label: 'Availability' },
    ],
    reasons: [
      'Exceptional 60-hour battery life',
      'Audiophile-grade sound quality',
      'Foldable design ideal for travel',
      'Multiple codec support including aptX Adaptive',
    ],
    drawbacks: [
      'Exceeds your ₹15,000 budget by ₹3,990',
      'Heavier at 293g',
      'ANC performance slightly behind Sony and Bose',
    ],
  },
  'jbl-tour-one-m2': {
    overall: 85,
    breakdown: [
      { attribute: 'requirements', score: 85, weight: 0.25, label: 'Requirements Match' },
      { attribute: 'features', score: 88, weight: 0.20, label: 'Features' },
      { attribute: 'price', score: 88, weight: 0.20, label: 'Price' },
      { attribute: 'reviews', score: 82, weight: 0.15, label: 'Reviews' },
      { attribute: 'reliability', score: 80, weight: 0.10, label: 'Reliability' },
      { attribute: 'availability', score: 85, weight: 0.10, label: 'Availability' },
    ],
    reasons: [
      'Near your ₹15,000 budget',
      'Excellent 50-hour battery life',
      'LDAC codec support for Hi-Res audio',
      'Good noise cancellation',
    ],
    drawbacks: [
      'Slightly over budget at ₹14,499',
      'Fewer reviews — long-term reliability less certain',
      'ANC not as refined as Sony or Bose',
      'Low stock at one retailer',
    ],
  },
  'apple-airpods-max': {
    overall: 72,
    breakdown: [
      { attribute: 'requirements', score: 78, weight: 0.25, label: 'Requirements Match' },
      { attribute: 'features', score: 85, weight: 0.20, label: 'Features' },
      { attribute: 'price', score: 35, weight: 0.20, label: 'Price' },
      { attribute: 'reviews', score: 94, weight: 0.15, label: 'Reviews' },
      { attribute: 'reliability', score: 92, weight: 0.10, label: 'Reliability' },
      { attribute: 'availability', score: 100, weight: 0.10, label: 'Availability' },
    ],
    reasons: [
      'Exceptional build quality and sound',
      'Best-in-class spatial audio',
      'Seamless Apple ecosystem integration',
      'Very high review scores',
    ],
    drawbacks: [
      'Far exceeds ₹15,000 budget (₹49,900)',
      'Heavy at 384g — not ideal for 6+ hours',
      'No multipoint Bluetooth',
      'Only AAC codec — limited for non-Apple devices',
      'Does not fold for travel',
    ],
    whyNotHigher: [
      'Price is 3.3x the stated budget',
      'Weight makes it unsuitable for extended travel use',
      'Limited codec support disadvantages non-Apple users',
    ],
  },
};

// --- Price History ---
function generatePriceHistory(basePrice: number, productId: string, days: number = 365): PriceHistory {
  const data: PricePoint[] = [];
  const now = new Date();
  let price = basePrice * 1.15;
  let min = price;
  let max = price;
  let sum = 0;
  let last90Sum = 0;
  let last90Min = Infinity;
  let last90Count = 0;

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const variation = (Math.random() - 0.45) * basePrice * 0.04;
    price = Math.max(basePrice * 0.88, Math.min(basePrice * 1.2, price + variation));
    price = Math.round(price);

    data.push({
      date: date.toISOString().split('T')[0],
      price,
      retailerId: 'amazon-in',
    });

    if (price < min) min = price;
    if (price > max) max = price;
    sum += price;

    if (i <= 90) {
      last90Sum += price;
      last90Count++;
      if (price < last90Min) last90Min = price;
    }
  }

  const current = data[data.length - 1].price;
  return {
    productId,
    currency: 'INR',
    data,
    currentPrice: current,
    ninetyDayLow: last90Min === Infinity ? min : last90Min,
    ninetyDayAvg: last90Count > 0 ? Math.round(last90Sum / last90Count) : Math.round(sum / data.length),
    historicalHigh: max,
    historicalLow: min,
  };
}

export const mockPriceHistories: Record<string, PriceHistory> = {
  'sony-wh1000xm5': generatePriceHistory(13499, 'sony-wh1000xm5'),
  'bose-qc-ultra': generatePriceHistory(24900, 'bose-qc-ultra'),
  'sennheiser-momentum4': generatePriceHistory(18990, 'sennheiser-momentum4'),
  'jbl-tour-one-m2': generatePriceHistory(14999, 'jbl-tour-one-m2'),
  'apple-airpods-max': generatePriceHistory(49900, 'apple-airpods-max'),
};

// --- Price Summaries ---
export const mockPriceSummaries: Record<string, PriceSummary> = {
  'sony-wh1000xm5': {
    currentPrice: 13499,
    originalPrice: 14990,
    discount: 10,
    currency: 'INR',
    advice: 'good_price',
    advisoryText: 'Current price is 8.8% below its 90-day average. This is a good time to buy.',
    percentBelowAvg: 8.8,
    trueCost: {
      listedPrice: 13499,
      shipping: 0,
      tax: 0,
      importDuty: 0,
      couponDiscount: 0,
      cashback: 0,
      estimatedTotal: 13499,
      isEstimate: false,
    },
  },
  'bose-qc-ultra': {
    currentPrice: 24900,
    originalPrice: 29900,
    discount: 17,
    currency: 'INR',
    advice: 'good_price',
    advisoryText: 'Current price is near its 90-day low. Significant discount from MRP.',
    percentBelowAvg: 12.3,
  },
  'sennheiser-momentum4': {
    currentPrice: 18990,
    originalPrice: 24990,
    discount: 24,
    currency: 'INR',
    advice: 'buy_now',
    advisoryText: 'Current price is close to the historical low. Best price in 6 months.',
    percentBelowAvg: 15.2,
  },
  'jbl-tour-one-m2': {
    currentPrice: 14499,
    originalPrice: 19999,
    discount: 28,
    currency: 'INR',
    advice: 'buy_now',
    advisoryText: 'Lowest price ever recorded. Excellent deal.',
    percentBelowAvg: 18.5,
  },
  'apple-airpods-max': {
    currentPrice: 49900,
    originalPrice: 59900,
    discount: 17,
    currency: 'INR',
    advice: 'normal_price',
    advisoryText: 'Price is at its typical range. No significant discount or premium.',
    percentBelowAvg: 2.1,
  },
};

// --- Review Analysis ---
export const mockReviewAnalyses: Record<string, ReviewAnalysis> = {
  'sony-wh1000xm5': {
    productId: 'sony-wh1000xm5',
    totalReviewed: 12847,
    dateRange: 'Jan 2023 – Sep 2024',
    sourceCoverage: ['Amazon', 'Flipkart', 'Croma'],
    confidence: 92,
    themes: [
      { topic: 'Noise Cancellation', sentiment: 'positive', mentions: 4821, summary: 'Industry-leading ANC consistently praised across reviews' },
      { topic: 'Comfort', sentiment: 'positive', mentions: 3567, summary: 'Very comfortable for extended wear, lightweight design' },
      { topic: 'Battery Life', sentiment: 'positive', mentions: 2890, summary: '30-hour battery life meets or exceeds expectations' },
      { topic: 'Sound Quality', sentiment: 'positive', mentions: 3214, summary: 'Balanced, detailed sound with LDAC support' },
      { topic: 'Build Quality', sentiment: 'positive', mentions: 1876, summary: 'Premium feel, though some prefer the XM4 hinge design' },
      { topic: 'App Experience', sentiment: 'negative', mentions: 1243, summary: 'Sony Headphones Connect app criticized for occasional bugs' },
      { topic: 'Microphone', sentiment: 'negative', mentions: 987, summary: 'Call quality is average, struggles in windy/noisy environments' },
      { topic: 'Fit', sentiment: 'mixed', mentions: 654, summary: 'May feel tight for users with larger heads' },
    ],
  },
};

// --- Search Results ---
export function getMockSearchResults(): SearchResult[] {
  return mockProducts
    .filter((p) => p.categoryId === 'headphones')
    .map((product) => {
      const variant = mockVariants.find((v) => v.productId === product.id)!;
      const offers = mockOffers.filter((o) => o.productVariantId === variant?.id);
      const bestOffer = offers.reduce(
        (best, offer) => (!best || offer.price < best.price ? offer : best),
        null as Offer | null
      ) || offers[0];

      return {
        product,
        variant,
        bestOffer,
        recommendation: mockRecommendations[product.id] || {
          overall: 75,
          breakdown: [],
          reasons: [],
          drawbacks: [],
        },
        priceSummary: mockPriceSummaries[product.id] || {
          currentPrice: bestOffer?.price || 0,
          currency: 'INR' as CurrencyCode,
          advice: 'normal_price' as const,
          advisoryText: 'Not enough data to provide price advice.',
        },
        retailerCount: offers.length,
      };
    })
    .sort((a, b) => b.recommendation.overall - a.recommendation.overall);
}

// --- Wishlist ---
export const mockWishlistItems: WishlistItem[] = [
  {
    id: 'wl-1',
    productId: 'sony-wh1000xm5',
    product: mockProducts[0],
    variant: mockVariants[0],
    bestOffer: mockOffers[0],
    addedAt: '2024-09-15T10:00:00Z',
    targetPrice: 12000,
    recommendation: mockRecommendations['sony-wh1000xm5'],
    historicalAvg: 14799,
    historicalLow: 12899,
    priceMovement: 'down',
  },
  {
    id: 'wl-2',
    productId: 'sennheiser-momentum4',
    product: mockProducts[2],
    variant: mockVariants[3],
    bestOffer: mockOffers[5],
    addedAt: '2024-09-20T14:30:00Z',
    recommendation: mockRecommendations['sennheiser-momentum4'],
    historicalAvg: 21990,
    historicalLow: 17990,
    priceMovement: 'down',
  },
];

// --- Alerts ---
export const mockAlerts: PriceAlert[] = [
  {
    id: 'alert-1',
    productId: 'sony-wh1000xm5',
    product: mockProducts[0],
    type: 'target_price',
    targetPrice: 12000,
    isActive: true,
    createdAt: '2024-09-15T10:05:00Z',
  },
  {
    id: 'alert-2',
    productId: 'bose-qc-ultra',
    product: mockProducts[1],
    type: 'percentage_drop',
    percentageDrop: 20,
    isActive: true,
    createdAt: '2024-09-18T16:20:00Z',
  },
  {
    id: 'alert-3',
    productId: 'sennheiser-momentum4',
    product: mockProducts[2],
    type: 'historical_low',
    isActive: true,
    createdAt: '2024-09-22T09:00:00Z',
  },
];

// --- Notifications ---
export const mockNotifications: Notification[] = [
  {
    id: 'notif-1',
    type: 'price_drop',
    title: 'Price Drop Alert',
    message: 'Sony WH-1000XM5 dropped ₹1,491 on Amazon — now ₹13,499',
    productId: 'sony-wh1000xm5',
    read: false,
    createdAt: '2024-09-28T08:00:00Z',
  },
  {
    id: 'notif-2',
    type: 'better_alternative',
    title: 'Better Alternative Found',
    message: 'JBL Tour One M2 is now 28% off — similar features at a lower price',
    productId: 'jbl-tour-one-m2',
    read: false,
    createdAt: '2024-09-27T14:30:00Z',
  },
  {
    id: 'notif-3',
    type: 'back_in_stock',
    title: 'Back in Stock',
    message: 'Sennheiser Momentum 4 is back in stock at Flipkart',
    productId: 'sennheiser-momentum4',
    read: true,
    createdAt: '2024-09-26T10:15:00Z',
  },
  {
    id: 'notif-4',
    type: 'info',
    title: 'ShopBuddy Insight',
    message: 'October sales are historically good for headphones — average 12% more discount',
    read: true,
    createdAt: '2024-09-25T09:00:00Z',
  },
];

// --- Currencies ---
export const mockCurrencies: Currency[] = [
  { code: 'INR', symbol: '₹', name: 'Indian Rupee', rate: 83.12 },
  { code: 'USD', symbol: '$', name: 'US Dollar', rate: 1 },
  { code: 'EUR', symbol: '€', name: 'Euro', rate: 0.92 },
  { code: 'GBP', symbol: '£', name: 'British Pound', rate: 0.79 },
  { code: 'AED', symbol: 'د.إ', name: 'UAE Dirham', rate: 3.67 },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar', rate: 1.36 },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', rate: 1.53 },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', rate: 149.50 },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar', rate: 1.35 },
];

// --- Comparison ---
export const mockComparisonSummary: ComparisonSummary = {
  analysis: 'All three headphones deliver excellent noise cancellation, but they differ significantly in price, battery life, and codec support.',
  bestFor: {
    'Sony WH-1000XM5': 'Best overall value — strong ANC, great battery, and within budget',
    'Bose QuietComfort Ultra': 'Best spatial audio and comfort for premium buyers',
    'Sennheiser Momentum 4': 'Best for audiophiles who prioritize sound quality and battery life',
  },
  keyTradeoff: 'The Sony WH-1000XM5 costs ₹11,401 less than the Bose QC Ultra while offering 25% longer battery life. However, the Bose provides superior spatial audio and a foldable design better suited for travel.',
};

// --- Shopping Missions ---
export const mockShoppingMissions: ShoppingMission[] = [
  {
    id: 'mission-1',
    title: 'Gaming Setup',
    description: 'Build a complete gaming setup under ₹1,50,000',
    totalBudget: 150000,
    currency: 'INR',
    items: [
      { id: 'mi-1', category: 'Gaming PC', allocatedBudget: 80000, status: 'searching' },
      { id: 'mi-2', category: 'Monitor', allocatedBudget: 25000, status: 'searching' },
      { id: 'mi-3', category: 'Keyboard', allocatedBudget: 5000, status: 'searching' },
      { id: 'mi-4', category: 'Mouse', allocatedBudget: 4000, status: 'searching' },
      { id: 'mi-5', category: 'Headset', allocatedBudget: 15000, status: 'selected', selectedProduct: mockProducts[0] },
      { id: 'mi-6', category: 'Chair', allocatedBudget: 21000, status: 'searching' },
    ],
    createdAt: '2024-09-20T10:00:00Z',
    status: 'active',
  },
];

// --- Dashboard ---
export const mockDashboardMetrics: DashboardMetrics = {
  wishlistItems: 2,
  priceDrops: 3,
  backInStock: 1,
  potentialSavings: 4580,
};

// --- AI Research Steps ---
export const mockResearchSteps = [
  { id: 'r1', label: 'Understanding your requirements', status: 'complete' as const, detail: 'Budget, category, and use case identified' },
  { id: 'r2', label: 'Discovering products', status: 'complete' as const, detail: 'Found 84 matching products' },
  { id: 'r3', label: 'Comparing retailer prices', status: 'complete' as const, detail: 'Checked 7 retailers' },
  { id: 'r4', label: 'Analyzing specifications', status: 'complete' as const, detail: 'Evaluated key attributes' },
  { id: 'r5', label: 'Reviewing customer feedback', status: 'complete' as const, detail: 'Analyzed 12,847 reviews' },
  { id: 'r6', label: 'Checking price history', status: 'complete' as const, detail: '365 days of data' },
  { id: 'r7', label: 'Evaluating seller reliability', status: 'complete' as const, detail: 'Verified seller ratings' },
  { id: 'r8', label: 'Calculating ownership cost', status: 'complete' as const, detail: 'Including shipping and warranty' },
];

// --- Suggested Searches ---
export const suggestedSearches = [
  'Best wireless headphones under ₹15,000 for travel',
  'Best laptop under ₹1 lakh for programming',
  'Running shoes for daily training under ₹10,000',
  'Compare iPhone alternatives under ₹70,000',
  'Build me a gaming setup under ₹1,50,000',
];

// --- Trending Categories ---
export const trendingCategories = [
  { name: 'Headphones', slug: 'headphones', icon: 'Headphones', productCount: 1284 },
  { name: 'Laptops', slug: 'laptops', icon: 'Laptop', productCount: 892 },
  { name: 'Mobile Phones', slug: 'mobile-phones', icon: 'Smartphone', productCount: 2341 },
  { name: 'Gaming', slug: 'gaming', icon: 'Gamepad2', productCount: 756 },
  { name: 'TVs', slug: 'tvs', icon: 'Tv', productCount: 534 },
  { name: 'Cameras', slug: 'cameras', icon: 'Camera', productCount: 421 },
  { name: 'Footwear', slug: 'footwear', icon: 'Footprints', productCount: 3124 },
  { name: 'Fitness', slug: 'fitness', icon: 'Dumbbell', productCount: 678 },
];
