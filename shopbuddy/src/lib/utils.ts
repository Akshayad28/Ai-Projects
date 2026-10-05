// ============================================
// SHOPBUDDY AI — Utility Functions
// ============================================

import type { CurrencyCode, PriceAdvice } from '@/types';
import { SUPPORTED_CURRENCIES } from '@/lib/currencies';

/**
 * Format price with currency symbol
 */
export function formatPrice(amount: number, currency: CurrencyCode = 'INR'): string {
  const curr = SUPPORTED_CURRENCIES.find((c) => c.code === currency);
  const symbol = curr?.symbol || '₹';

  if (currency === 'INR') {
    // Indian number formatting
    return `${symbol}${amount.toLocaleString('en-IN')}`;
  }

  if (currency === 'JPY') {
    return `${symbol}${Math.round(amount).toLocaleString()}`;
  }

  return `${symbol}${amount.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

/**
 * Convert price between currencies
 */
export function convertPrice(
  amount: number,
  from: CurrencyCode,
  to: CurrencyCode
): number {
  if (from === to) return amount;

  const fromCurr = SUPPORTED_CURRENCIES.find((c) => c.code === from);
  const toCurr = SUPPORTED_CURRENCIES.find((c) => c.code === to);

  if (!fromCurr || !toCurr) return amount;

  // Convert to USD first, then to target
  const usdAmount = amount / fromCurr.rate;
  return Math.round(usdAmount * toCurr.rate);
}

/**
 * Format relative time
 */
export function timeAgo(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;

  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
  });
}

/**
 * Get price advice label and color
 */
export function getPriceAdviceConfig(advice: PriceAdvice): {
  label: string;
  color: string;
  bgColor: string;
} {
  switch (advice) {
    case 'buy_now':
      return { label: 'Buy Now', color: '#16805A', bgColor: '#DCEDE4' };
    case 'good_price':
      return { label: 'Good Price', color: '#2F7D5A', bgColor: '#DCEDE4' };
    case 'normal_price':
      return { label: 'Normal Price', color: '#6B706D', bgColor: '#EFEEE9' };
    case 'wait':
      return { label: 'Wait', color: '#C58A32', bgColor: '#FFF3E0' };
    case 'price_high':
      return { label: 'Price High', color: '#C85C52', bgColor: '#FDE8E7' };
    case 'insufficient_data':
      return { label: 'Insufficient Data', color: '#6B706D', bgColor: '#EFEEE9' };
  }
}

/**
 * Format percentage
 */
export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

/**
 * Get rating stars array
 */
export function getRatingStars(rating: number): ('full' | 'half' | 'empty')[] {
  const stars: ('full' | 'half' | 'empty')[] = [];
  for (let i = 1; i <= 5; i++) {
    if (rating >= i) stars.push('full');
    else if (rating >= i - 0.5) stars.push('half');
    else stars.push('empty');
  }
  return stars;
}

/**
 * Get availability label
 */
export function getAvailabilityLabel(status: string): {
  label: string;
  color: string;
} {
  switch (status) {
    case 'in_stock':
      return { label: 'In Stock', color: '#16805A' };
    case 'low_stock':
      return { label: 'Low Stock', color: '#C58A32' };
    case 'out_of_stock':
      return { label: 'Out of Stock', color: '#C85C52' };
    case 'pre_order':
      return { label: 'Pre-order', color: '#6B706D' };
    case 'discontinued':
      return { label: 'Discontinued', color: '#C85C52' };
    default:
      return { label: 'Unknown', color: '#6B706D' };
  }
}

/**
 * Truncate text
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + '…';
}

/**
 * Generate unique ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Clamp value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/**
 * Validate that an external URL uses a safe HTTP or HTTPS protocol, preventing javascript: or data: pseudo-protocol XSS
 */
export function isSafeUrl(url: string | undefined | null): boolean {
  if (!url) return false;
  const clean = url.trim().toLowerCase();
  return clean.startsWith('http://') || clean.startsWith('https://');
}

