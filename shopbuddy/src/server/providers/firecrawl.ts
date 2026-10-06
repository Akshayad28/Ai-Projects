import { serverConfig } from '../config';
import { LiveProviderInfoDTO, ProductOfferDTO } from '../types';

export interface FirecrawlDiscoveredProduct {
  id: string;
  title: string;
  url: string;
  brand?: string;
  image_url?: string;
  price?: number;
  currency: string;
  retailer: string;
  snippet?: string;
  offers: ProductOfferDTO[];
}

export interface FirecrawlExecutionResult {
  products: FirecrawlDiscoveredProduct[];
  providerInfo: LiveProviderInfoDTO;
}

const KNOWN_RETAILERS: Record<string, string> = {
  'amazon.in': 'Amazon India',
  'amazon.com': 'Amazon',
  'flipkart.com': 'Flipkart',
  'croma.com': 'Croma',
  'reliancedigital.in': 'Reliance Digital',
  'tatacliq.com': 'Tata CLiQ',
  'myntra.com': 'Myntra',
  'ikea.com': 'IKEA',
  'apple.com': 'Apple Store',
  'samsung.com': 'Samsung Store',
  'dell.com': 'Dell',
  'lenovo.com': 'Lenovo',
  'greensoul.online': 'Green Soul',
};

function extractRetailer(urlStr: string): { domain: string; name: string } {
  try {
    const parsed = new URL(urlStr);
    let netloc = parsed.hostname.toLowerCase();
    if (netloc.startsWith('www.')) netloc = netloc.slice(4);

    for (const [dom, name] of Object.entries(KNOWN_RETAILERS)) {
      if (netloc === dom || netloc.endsWith(`.${dom}`)) {
        return { domain: netloc, name };
      }
    }

    const parts = netloc.split('.');
    if (parts.length >= 2) {
      return { domain: netloc, name: parts[0].charAt(0).toUpperCase() + parts[0].slice(1) };
    }
    return { domain: netloc, name: 'Retailer' };
  } catch {
    return { domain: 'web', name: 'Retailer' };
  }
}

function parsePrice(text?: string): { price?: number; currency: string } {
  if (!text) return { currency: 'INR' };
  let currency = 'INR';
  if (text.includes('$')) currency = 'USD';
  else if (text.includes('£')) currency = 'GBP';
  else if (text.includes('€')) currency = 'EUR';

  const digits = text.replace(/,/g, '').match(/\d+(?:\.\d+)?/);
  if (digits) {
    return { price: parseFloat(digits[0]), currency };
  }
  return { currency };
}

export async function executeFirecrawlSearch(
  query: string,
  country: string = 'IN',
  currency: string = 'INR'
): Promise<FirecrawlExecutionResult> {
  const apiKey = serverConfig.firecrawlApiKey;

  if (!apiKey || !serverConfig.firecrawlEnabled) {
    return {
      products: [],
      providerInfo: {
        name: 'firecrawl',
        label: 'Firecrawl Web Discovery',
        configured: false,
        status: 'unavailable',
        products_found: 0,
        offers_count: 0,
        is_demo: false,
        required_env: ['FIRECRAWL_API_KEY'],
        countries: ['IN', 'US', 'GB'],
        rate_limit_per_second: 5,
        error: 'FIRECRAWL_API_KEY not configured',
      },
    };
  }

  const startTime = Date.now();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const res = await fetch('https://api.firecrawl.dev/v1/search', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: `${query} buy online ${country === 'IN' ? 'price in India' : ''}`,
        limit: 8,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeout);
    const latency = Date.now() - startTime;

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const errorMsg = errJson.error || `HTTP ${res.status}`;
      return {
        products: [],
        providerInfo: {
          name: 'firecrawl',
          label: 'Firecrawl Web Discovery',
          configured: true,
          status: 'unavailable',
          products_found: 0,
          offers_count: 0,
          latency_ms: latency,
          error: errorMsg,
          is_demo: false,
          required_env: ['FIRECRAWL_API_KEY'],
          countries: ['IN', 'US', 'GB'],
          rate_limit_per_second: 5,
        },
      };
    }

    const json = await res.json();
    if (!json.success && json.error) {
      return {
        products: [],
        providerInfo: {
          name: 'firecrawl',
          label: 'Firecrawl Web Discovery',
          configured: true,
          status: 'unavailable',
          products_found: 0,
          offers_count: 0,
          latency_ms: latency,
          error: json.error,
          is_demo: false,
          required_env: ['FIRECRAWL_API_KEY'],
          countries: ['IN', 'US', 'GB'],
          rate_limit_per_second: 5,
        },
      };
    }

    const items = json.data || [];
    const discovered: FirecrawlDiscoveredProduct[] = [];

    for (const item of items) {
      if (!item.url || !item.title) continue;
      const { domain, name } = extractRetailer(item.url);
      const parsedP = parsePrice(item.description || item.markdown || '');

      const prodId = `fc_${Math.abs(
        item.url.split('').reduce((acc: number, char: string) => ((acc << 5) - acc + char.charCodeAt(0)) | 0, 0)
      ).toString(16)}`;

      const offer: ProductOfferDTO = {
        retailer: name,
        price: parsedP.price || 0,
        currency: parsedP.currency || currency,
        url: item.url,
        availability: 'in_stock',
        seller_name: name,
        is_verified: true,
      };

      discovered.push({
        id: prodId,
        title: item.title,
        url: item.url,
        retailer: name,
        image_url: item.metadata?.image || undefined,
        price: parsedP.price,
        currency: parsedP.currency || currency,
        snippet: item.description,
        offers: [offer],
      });
    }

    return {
      products: discovered,
      providerInfo: {
        name: 'firecrawl',
        label: 'Firecrawl Web Discovery',
        configured: true,
        status: discovered.length > 0 ? 'healthy' : 'degraded',
        products_found: discovered.length,
        offers_count: discovered.length,
        latency_ms: latency,
        is_demo: false,
        required_env: ['FIRECRAWL_API_KEY'],
        countries: ['IN', 'US', 'GB'],
        rate_limit_per_second: 5,
      },
    };
  } catch (err: any) {
    const latency = Date.now() - startTime;
    return {
      products: [],
      providerInfo: {
        name: 'firecrawl',
        label: 'Firecrawl Web Discovery',
        configured: true,
        status: 'unavailable',
        products_found: 0,
        offers_count: 0,
        latency_ms: latency,
        error: err.name === 'AbortError' ? 'Search request timed out' : err.message,
        is_demo: false,
        required_env: ['FIRECRAWL_API_KEY'],
        countries: ['IN', 'US', 'GB'],
        rate_limit_per_second: 5,
      },
    };
  }
}
