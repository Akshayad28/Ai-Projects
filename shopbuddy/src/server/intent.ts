import { serverConfig } from './config';
import { SearchIntentDTO } from './types';

// Currency patterns
const CURRENCY_PATTERNS: Array<{ regex: RegExp; currency: string; multiplier?: (m: RegExpMatchArray) => number }> = [
  {
    regex: /(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|k|thousand|cr|crore)?/i,
    currency: 'INR',
    multiplier: (m) => {
      const unit = (m[2] || '').toLowerCase();
      if (unit === 'lakh' || unit === 'lac') return 100000;
      if (unit === 'k' || unit === 'thousand') return 1000;
      if (unit === 'cr' || unit === 'crore') return 10000000;
      return 1;
    },
  },
  {
    regex: /\$\s*([\d,]+(?:\.\d+)?)\s*(k)?/i,
    currency: 'USD',
    multiplier: (m) => ((m[2] || '').toLowerCase() === 'k' ? 1000 : 1),
  },
  {
    regex: /£\s*([\d,]+(?:\.\d+)?)\s*(k)?/i,
    currency: 'GBP',
    multiplier: (m) => ((m[2] || '').toLowerCase() === 'k' ? 1000 : 1),
  },
  {
    regex: /€\s*([\d,]+(?:\.\d+)?)\s*(k)?/i,
    currency: 'EUR',
    multiplier: (m) => ((m[2] || '').toLowerCase() === 'k' ? 1000 : 1),
  },
  {
    regex: /under\s+([\d,]+)\s*(?:rs|rupees|inr)/i,
    currency: 'INR',
  },
  {
    regex: /under\s+([\d,]+)\s*(?:dollars|usd|\$)/i,
    currency: 'USD',
  },
];

const KNOWN_BRANDS = [
  'apple', 'samsung', 'sony', 'bose', 'sennheiser', 'jbl', 'asus', 'dell', 'hp',
  'lenovo', 'acer', 'lg', 'oneplus', 'google', 'xiaomi', 'philips', 'ninja', 'instant',
  'nike', 'adidas', 'asics', 'puma', 'new balance', 'hoka', 'saucony', 'sihoo', 'herman miller',
  'steelcase', 'featherlite', 'bosch', 'dewalt', 'stanley', 'black+decker', 'samsonite',
  'american tourister', 'delsey', 'minimalist', 'cerave', 'the ordinary', 'cetaphil'
];

export function parseIntentWithRules(query: string, country: string = 'IN', currency: string = 'INR'): SearchIntentDTO {
  const qLower = query.toLowerCase();
  let maxBudget: number | undefined;
  let minBudget: number | undefined;
  let detectedCurrency = currency;

  for (const pat of CURRENCY_PATTERNS) {
    const match = qLower.match(pat.regex);
    if (match) {
      const rawNum = match[1].replace(/,/g, '');
      const mult = pat.multiplier ? pat.multiplier(match) : 1;
      const num = parseFloat(rawNum) * mult;
      if (!isNaN(num)) {
        detectedCurrency = pat.currency;
        if (/above|over|more than|min/i.test(qLower)) {
          minBudget = num;
        } else {
          maxBudget = num;
        }
        break;
      }
    }
  }

  const foundBrands = KNOWN_BRANDS
    .filter((b) => new RegExp(`\\b${b}\\b`, 'i').test(qLower))
    .map((b) => b.charAt(0).toUpperCase() + b.slice(1));

  const useCases: string[] = [];
  const useCaseMap: Record<string, string[]> = {
    programming: ['programming', 'coding', 'developer', 'software development'],
    gaming: ['gaming', 'esports', 'games', 'playstation', 'xbox'],
    travel: ['travel', 'traveling', 'flight', 'commute', 'portable'],
    running: ['running', 'jogging', 'marathon', 'long runs'],
    office: ['office', 'wfh', 'work from home', 'desk work', 'long hours'],
    family: ['family of four', 'family of 4', 'family', 'large family'],
    photography: ['photography', 'photos', 'vlogging', 'camera'],
    diy: ['home diy', 'diy', 'woodworking', 'drilling'],
  };

  for (const [uc, triggers] of Object.entries(useCaseMap)) {
    if (triggers.some((t) => qLower.includes(t))) {
      useCases.push(uc);
    }
  }

  // Clean provider query
  let cleanQ = query
    .replace(/\b(best|cheap|top|good|recommend|for|under|below|budget)\b/gi, ' ')
    .replace(/[₹\$£€]\s*[\d,]+(?:\s*(?:lakh|lac|k|cr))?/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!cleanQ) cleanQ = query;

  return {
    raw_query: query,
    provider_query: cleanQ,
    budget: {
      min: minBudget,
      max: maxBudget,
      currency: detectedCurrency,
    },
    use_cases: useCases,
    requirements: [],
    preferred_brands: foundBrands,
    country,
    parser: 'rules',
  };
}

export async function parseIntent(query: string, country: string = 'IN', currency: string = 'INR'): Promise<SearchIntentDTO> {
  const baseIntent = parseIntentWithRules(query, country, currency);
  const apiKey = serverConfig.geminiApiKey;

  if (!apiKey) {
    return baseIntent;
  }

  try {
    const prompt = `You are a universal shopping intent parser. Analyze this user shopping query:
"${query}"
Return a valid JSON object matching this schema:
{
  "product_type": "specific product type (e.g. office chair, dining table, running shoes, air fryer, cordless drill, etc.) or null",
  "category": "broad product category (e.g. furniture, electronics, footwear, appliances, tools, skincare, clothing, luggage, etc.) or null",
  "brand": "brand name if mentioned or null",
  "model": "model name or number if mentioned (e.g. S26 Ultra, M4, WH-1000XM5) or null",
  "budget_min": number or null,
  "budget_max": number or null,
  "currency": "${currency}",
  "size": "size specification if mentioned or null",
  "color": "color preference if mentioned or null",
  "use_cases": ["intended use case, e.g. long working hours, gaming, family of four"],
  "requirements": ["specific requirements or specs, e.g. 16GB RAM, 512GB SSD, 1440p 165Hz, wooden, 6 people, cordless"],
  "preferred_brands": ["preferred brands"],
  "clean_provider_query": "concise keyword search string optimized for retail search engines without conversational noise words"
}
DO NOT invent any product models or prices not in the query. Return strictly JSON.`;

    const model = serverConfig.geminiModel;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.0,
          responseMimeType: 'application/json',
        },
      }),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (res.ok) {
      const data = await res.json();
      const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (rawText) {
        const parsed = JSON.parse(rawText);
        return {
          raw_query: query,
          provider_query: parsed.clean_provider_query || baseIntent.provider_query,
          category: parsed.category || undefined,
          product_type: parsed.product_type || undefined,
          brand: parsed.brand || baseIntent.preferred_brands[0],
          model: parsed.model || undefined,
          budget: {
            min: parsed.budget_min ?? baseIntent.budget.min,
            max: parsed.budget_max ?? baseIntent.budget.max,
            currency: parsed.currency || baseIntent.budget.currency,
          },
          use_cases: parsed.use_cases || baseIntent.use_cases,
          requirements: parsed.requirements || [],
          preferred_brands: parsed.preferred_brands?.length ? parsed.preferred_brands : baseIntent.preferred_brands,
          country,
          parser: 'llm',
        };
      }
    }
  } catch (err) {
    // Graceful fallback to rule-based parser on timeout or error
    console.warn('[INTENT] Gemini intent parsing fallback to rules:', err);
  }

  return baseIntent;
}
