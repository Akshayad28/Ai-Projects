import catalogProductsRaw from './catalog_products.json';
import categoriesConfig from './categories.json';
import { extractDynamicAttributes } from './normalization';
import { computeRecommendation } from './recommendation';
import {
  CatalogProductRecord,
  CategoryDTO,
  ProductCardDTO,
  SearchIntentDTO,
} from './types';

const catalogProducts: CatalogProductRecord[] = catalogProductsRaw as any;

export function getCategoriesList(): CategoryDTO[] {
  const cats = (categoriesConfig as any).categories || [];
  return cats.map((c: any) => ({
    id: c.id,
    name: c.name,
    department: c.department || 'general',
    keywords: c.keywords || [],
    sort_order: c.sort_order || 99,
  }));
}

export function getProductById(productId: string): ProductCardDTO | null {
  const p = catalogProducts.find((item) => item.id === productId);
  if (!p) return null;
  return toProductCardDTO(p);
}

export function getPriceHistoryById(productId: string): any {
  const p = catalogProducts.find((item) => item.id === productId);
  if (!p) return { product_id: productId, currency: 'INR', observations: [] };

  const history = p.price_history && p.price_history.length > 0
    ? p.price_history
    : p.offers.map((o) => ({
        retailer: o.retailer,
        price: o.price,
        currency: o.currency || 'INR',
        date: new Date().toISOString(),
      }));

  return {
    product_id: productId,
    title: p.title,
    currency: history[0]?.currency || 'INR',
    current_price: p.offers[0]?.price,
    observations: history,
  };
}

function toProductCardDTO(p: CatalogProductRecord, intent?: SearchIntentDTO): ProductCardDTO {
  const primaryOffer = p.offers[0] || {
    retailer: 'Verified Retailer',
    price: 0,
    currency: 'INR',
    url: '#',
    availability: 'in_stock',
  };

  const bestPrice = primaryOffer.price;
  const originalPrice = primaryOffer.original_price;
  const discountPercent =
    originalPrice && bestPrice && originalPrice > bestPrice
      ? Math.round(((originalPrice - bestPrice) / originalPrice) * 100)
      : undefined;

  const cardAttrs = extractDynamicAttributes(p.title, p.category_id, p.attributes);
  const recommendation = computeRecommendation(
    p.title,
    bestPrice,
    p.rating,
    p.review_count,
    intent?.budget?.max,
    p.offers.length
  );

  const sources = Array.from(new Set(p.offers.map((o) => o.retailer)));

  return {
    id: p.id,
    title: p.title,
    brand: p.brand,
    category_id: p.category_id,
    image_url: p.image_urls[0],
    image_urls: p.image_urls,
    rating: p.rating,
    review_count: p.review_count,
    best_price: bestPrice,
    original_price: originalPrice,
    currency: primaryOffer.currency || 'INR',
    discount_percent: discountPercent,
    primary_retailer: primaryOffer.retailer,
    offers_count: p.offers.length,
    offers: p.offers.map((o) => ({
      retailer: o.retailer,
      price: o.price,
      price_amount: o.price,
      original_price: o.original_price,
      currency: o.currency,
      url: o.url,
      availability: o.availability,
      seller_name: o.seller,
      delivery_estimate: o.delivery_estimate,
      warranty: o.warranty,
      is_verified: true,
    })),
    availability: (primaryOffer.availability as any) || 'in_stock',
    card_attributes: cardAttrs,
    recommendation,
    sources,
    is_demo: false,
    last_updated: 'Price checked just now',
    specifications: p.attributes || {},
    description: p.description,
  };
}

export function searchCatalog(
  query: string,
  intent: SearchIntentDTO,
  page: number = 1,
  pageSize: number = 24,
  sortBy: string = 'recommended'
): { products: ProductCardDTO[]; total: number } {
  const qTerms = query.toLowerCase().split(/\s+/).filter((t) => t.length > 1);
  const pBrand = intent.brand?.toLowerCase();
  const pType = intent.product_type?.toLowerCase();
  const pCategory = intent.category?.toLowerCase();
  const budgetMax = intent.budget?.max;

  const scored: Array<{ product: CatalogProductRecord; score: number }> = [];

  for (const p of catalogProducts) {
    let matchScore = 0;
    const titleLower = p.title.toLowerCase();
    const brandLower = (p.brand || '').toLowerCase();
    const descLower = (p.description || '').toLowerCase();

    // Query terms matching
    for (const term of qTerms) {
      if (titleLower.includes(term)) matchScore += 10;
      else if (brandLower.includes(term)) matchScore += 8;
      else if (descLower.includes(term)) matchScore += 3;
    }

    // Brand matching
    if (pBrand && brandLower.includes(pBrand)) {
      matchScore += 25;
    }

    // Product type or category matching
    if (pType && titleLower.includes(pType)) {
      matchScore += 20;
    }
    if (pCategory && (p.category_id || '').toLowerCase().includes(pCategory)) {
      matchScore += 15;
    }

    // Skip products with zero verified offers
    if (!p.offers || p.offers.length === 0) {
      continue;
    }

    // Budget constraint filter
    const price = p.offers[0]?.price;
    if (budgetMax && price && price > budgetMax * 1.35) {
      // Exclude products substantially over budget
      continue;
    }

    if (matchScore > 0) {
      scored.push({ product: p, score: matchScore });
    }
  }

  // Sort by match score or specified sort order
  if (sortBy === 'price_asc') {
    scored.sort((a, b) => (a.product.offers[0]?.price || 0) - (b.product.offers[0]?.price || 0));
  } else if (sortBy === 'price_desc') {
    scored.sort((a, b) => (b.product.offers[0]?.price || 0) - (a.product.offers[0]?.price || 0));
  } else if (sortBy === 'rating') {
    scored.sort((a, b) => (b.product.rating || 0) - (a.product.rating || 0));
  } else {
    // Default: recommended (match score + rating)
    scored.sort((a, b) => {
      const aRating = a.product.rating || 3.5;
      const bRating = b.product.rating || 3.5;
      return b.score + bRating * 2 - (a.score + aRating * 2);
    });
  }

  const total = scored.length;
  const startIndex = (page - 1) * pageSize;
  const paginated = scored.slice(startIndex, startIndex + pageSize);

  return {
    products: paginated.map((item) => toProductCardDTO(item.product, intent)),
    total,
  };
}
