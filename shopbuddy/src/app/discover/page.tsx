'use client';

import React, { Suspense, useEffect, useState, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Sparkles, ArrowUpDown, AlertCircle, RefreshCw } from 'lucide-react';
import { SearchBar } from '@/components/search/SearchBar';
import { ProductCard } from '@/components/product/ProductCard';
import { AIActivityPanel } from '@/components/ai/AIActivityPanel';
import { searchProducts, ProductCardDTO, SearchResponseDTO, clearClientSearchCache } from '@/lib/api';
import { useStore } from '@/store';
import styles from './discover.module.scss';

function DiscoverContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawQuery = searchParams.get('q') || '';

  const { currency, comparisonItems, toggleComparison } = useStore();
  const [data, setData] = useState<SearchResponseDTO | null>(null);
  const [productsList, setProductsList] = useState<ProductCardDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('recommended');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedMarketplace, setSelectedMarketplace] = useState<string>('all');
  const [searchNonce, setSearchNonce] = useState(0);

  const revalidateTimerRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const searchRequestIdRef = useRef<number>(0);
  const activeQueryRef = useRef<string>('');

  useEffect(() => {
    const trimmedQuery = rawQuery.trim();

    // 1. Cancel previous in-flight network request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // 2. Clear background revalidation timer
    if (revalidateTimerRef.current) {
      clearTimeout(revalidateTimerRef.current);
      revalidateTimerRef.current = null;
    }

    // 3. Monotonic request ID to ignore stale responses from slower/earlier searches
    const requestId = ++searchRequestIdRef.current;
    const isNewQuery = activeQueryRef.current !== trimmedQuery;
    activeQueryRef.current = trimmedQuery;

    // 4. Invalidate / reset filter, pagination, error, and refreshing states
    setCurrentPage(1);
    setSelectedMarketplace('all');
    setError(null);
    setIsRefreshing(false);

    if (isNewQuery) {
      setSortBy('recommended');
    }

    // 5. Handle empty / cleared query
    if (!trimmedQuery) {
      setData(null);
      setProductsList([]);
      setLoading(false);
      return;
    }

    // 6. IMMEDIATELY clear previous search results from the UI and show loading
    setData(null);
    setProductsList([]);
    setLoading(true);

    const activeSort = isNewQuery ? 'recommended' : sortBy;

    // 7. Dispatch search with AbortSignal
    searchProducts(trimmedQuery, 'IN', currency, activeSort, 1, 24, controller.signal)
      .then((res) => {
        // Discard if this is not the latest active request
        if (requestId !== searchRequestIdRef.current) return;

        setData(res);
        // Completely replace product results — never merge with previous query
        setProductsList(res.products);
        setLoading(false);

        // Background revalidation for the SAME query only
        if (res.search_metadata?.is_revalidating) {
          setIsRefreshing(true);
          revalidateTimerRef.current = setTimeout(() => {
            if (requestId !== searchRequestIdRef.current) return;
            searchProducts(trimmedQuery, 'IN', currency, activeSort, 1, 24, controller.signal)
              .then((refreshed) => {
                if (requestId !== searchRequestIdRef.current) return;
                setData(refreshed);
                setProductsList((prev) => {
                  if (requestId !== searchRequestIdRef.current) return prev;
                  const incomingMap = new Map(refreshed.products.map((p) => [p.id, p]));
                  const merged = prev.map((p) => incomingMap.get(p.id) || p);
                  refreshed.products.forEach((p) => {
                    if (!merged.some((existing) => existing.id === p.id)) {
                      merged.push(p);
                    }
                  });
                  return merged;
                });
              })
              .catch(() => {})
              .finally(() => {
                if (requestId === searchRequestIdRef.current) {
                  setIsRefreshing(false);
                }
              });
          }, 3000);
        } else {
          setIsRefreshing(false);
        }
      })
      .catch((err) => {
        if (requestId !== searchRequestIdRef.current || err.name === 'AbortError') return;
        console.error('Search error:', err);
        setError('Could not retrieve search results. Please check your network or try again.');
        setLoading(false);
      });

    return () => {
      controller.abort();
      if (revalidateTimerRef.current) {
        clearTimeout(revalidateTimerRef.current);
      }
    };
  }, [rawQuery, currency, sortBy, searchNonce]);

  const handleSortChange = (newSort: string) => {
    setSortBy(newSort);
    // Instant optimistic client-side re-sort
    setProductsList((prev) => {
      const copy = [...prev];
      if (newSort === 'price_asc') {
        copy.sort((a, b) => (a.best_price ?? Infinity) - (b.best_price ?? Infinity));
      } else if (newSort === 'price_desc') {
        copy.sort((a, b) => (b.best_price ?? 0) - (a.best_price ?? 0));
      } else if (newSort === 'rating') {
        copy.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
      } else {
        copy.sort((a, b) => (b.recommendation?.match_score ?? 0) - (a.recommendation?.match_score ?? 0));
      }
      return copy;
    });
  };

  const handleLoadMore = () => {
    if (!rawQuery.trim() || loadingMore || !data?.search_metadata?.pagination?.has_next) return;

    const nextPage = currentPage + 1;
    setLoadingMore(true);

    searchProducts(rawQuery.trim(), 'IN', currency, sortBy, nextPage, 24)
      .then((res) => {
        setCurrentPage(nextPage);
        setProductsList((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const newUnique = res.products.filter((p) => !existingIds.has(p.id));
          return [...prev, ...newUnique];
        });
        setData(res);
      })
      .catch((err) => {
        console.error('Load more error:', err);
      })
      .finally(() => {
        setLoadingMore(false);
      });
  };

  const handleSearchSubmit = (newQuery: string) => {
    const trimmed = newQuery.trim();

    // Abort pending fetch immediately on submit
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (revalidateTimerRef.current) {
      clearTimeout(revalidateTimerRef.current);
      revalidateTimerRef.current = null;
    }

    // Immediately clear previous search results from the UI
    setProductsList([]);
    setData(null);
    setError(null);
    setCurrentPage(1);
    setSelectedMarketplace('all');
    setSortBy('recommended');
    setIsRefreshing(false);

    if (trimmed) {
      setLoading(true);
      if (trimmed === rawQuery.trim()) {
        // Same query re-submitted: clear cache and trigger re-search
        clearClientSearchCache(trimmed);
        setSearchNonce((n) => n + 1);
      } else {
        router.push(`/discover?q=${encodeURIComponent(trimmed)}`);
      }
    } else {
      setLoading(false);
      router.push('/discover');
    }
  };

  const pagination = data?.search_metadata.pagination;
  const totalCanonical = pagination?.total || data?.search_metadata.products_found || productsList.length;
  const totalOffers = pagination?.total_offers || data?.search_metadata.total_offers || productsList.reduce((acc, p) => acc + (p.offers_count || 1), 0);
  const providersContributing = pagination?.providers_contributing || data?.search_metadata.providers_contributing || 0;

  const availableMarketplaces = React.useMemo(() => {
    const set = new Set<string>();
    let hasQC = false;
    productsList.forEach((p) => {
      if (p.is_quick_commerce) hasQC = true;
      (p.sources || []).forEach((s) => set.add(s.toLowerCase().replace(/\s+/g, '_')));
      (p.offers || []).forEach((o) => {
        if (o.retailer) set.add(o.retailer.toLowerCase().replace(/\s+/g, '_'));
        if (o.is_quick_commerce) hasQC = true;
      });
    });
    return { list: Array.from(set).sort(), hasQC };
  }, [productsList]);

  const filteredProducts = React.useMemo(() => {
    if (selectedMarketplace === 'all') return productsList;
    if (selectedMarketplace === 'quick_commerce') {
      return productsList.filter(
        (p) => p.is_quick_commerce || (p.offers || []).some((o) => o.is_quick_commerce)
      );
    }
    const target = selectedMarketplace.toLowerCase().replace(/\s+/g, '_');
    return productsList.filter(
      (p) =>
        (p.sources || []).some((s) => s.toLowerCase().replace(/\s+/g, '_') === target) ||
        (p.offers || []).some((o) => (o.retailer || '').toLowerCase().replace(/\s+/g, '_') === target) ||
        (p.primary_retailer || '').toLowerCase().replace(/\s+/g, '_') === target
    );
  }, [productsList, selectedMarketplace]);

  return (
    <div className={styles.discoverContainer}>
      {/* Top Search Controls */}
      <div className={styles.topBar}>
        <div className={styles.searchWrap}>
          <SearchBar initialQuery={rawQuery} onSearch={handleSearchSubmit} size="compact" />
        </div>
      </div>

      {/* Loading State: shown while results are being fetched */}
      {loading && (
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          <h2 className={styles.loadingTitle}>ShopBuddy is researching &ldquo;{rawQuery.trim()}&rdquo;...</h2>
          <p className={styles.loadingSubtitle}>
            Querying Google Scraper, Amazon, Flipkart, eBay, Quick Commerce, and Firecrawl in parallel, normalizing specs, and evaluating unbiased match scores.
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className={styles.errorState}>
          <AlertCircle size={28} className={styles.errorIcon} />
          <h3>Search Error</h3>
          <p>{error}</p>
          <button
            type="button"
            onClick={() => handleSearchSubmit(rawQuery)}
            className={styles.retryBtn}
          >
            <RefreshCw size={14} />
            <span>Retry Search</span>
          </button>
        </div>
      )}

      {/* Empty Query Prompt */}
      {!rawQuery.trim() && !loading && !error && (
        <div className={styles.loadingState} style={{ padding: '64px 0' }}>
          <Sparkles size={36} style={{ color: '#88d840', marginBottom: '16px' }} />
          <h2 className={styles.loadingTitle}>Universal Product Intelligence</h2>
          <p className={styles.loadingSubtitle}>
            Search for any product to discover live prices and compare deals across Amazon, Flipkart, Blinkit, Zepto, and more.
          </p>
        </div>
      )}

      {/* Search Results Display */}
      {(productsList.length > 0 || (data && !loading)) && (
        <>
          {/* AI Activity Panel */}
          {data && (
            <AIActivityPanel
              query={data.query}
              providersUsed={data.search_metadata.providers_used}
              productsFound={totalCanonical}
              durationMs={data.search_metadata.search_duration_ms}
              isDemo={data.search_metadata.is_demo}
              isLive={data.search_metadata.is_live}
              freshnessLabel={data.search_metadata.freshness_label}
              liveProvidersConfigured={data.search_metadata.live_providers_configured}
            />
          )}

          {/* Results Header */}
          <div className={styles.resultsHeader}>
            <div>
              <h1 className={styles.resultsTitle}>
                {productsList.length > 0 ? (
                  <>Best matches for "{rawQuery}"</>
                ) : (
                  <>No live matches for "{rawQuery}"</>
                )}
              </h1>
              <div className={styles.resultsCountGroup}>
                <p className={styles.resultsCount}>
                  <strong>{totalCanonical}</strong> canonical products · <strong>{totalOffers}</strong> live offers across{' '}
                  {data?.search_metadata.providers_used.length
                    ? data.search_metadata.providers_used.map((p) => p.replace('_', ' ')).join(', ')
                    : 'connected retailers'}
                </p>
                {data?.search_metadata.is_live && productsList.length > 0 && (
                  <div className={styles.freshnessBadge}>
                    <span>●</span>
                    <span>{data.search_metadata.freshness_label}</span>
                  </div>
                )}
                {isRefreshing && (
                  <div className={styles.refreshingBadge}>
                    <RefreshCw size={11} className={styles.spinIcon} />
                    <span>Updating live store data...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Sorting */}
            {productsList.length > 0 && (
              <div className={styles.sortWrapper}>
                <ArrowUpDown size={14} className={styles.sortIcon} />
                <label htmlFor="sort-select" className="sr-only">Sort products</label>
                <select
                  id="sort-select"
                  value={sortBy}
                  onChange={(e) => handleSortChange(e.target.value)}
                  className={styles.sortSelect}
                >
                  <option value="recommended">ShopBuddy Recommendation</option>
                  <option value="price_asc">Lowest Price</option>
                  <option value="price_desc">Highest Price</option>
                  <option value="rating">Highest Customer Rating</option>
                </select>
              </div>
            )}
          </div>

          {/* Provider Matrix Status Bar */}
          {data?.search_metadata.live_providers && data.search_metadata.live_providers.length > 0 && (
            <div className={styles.providerStatusBar}>
              <span className={styles.providerStatusTitle}>Sources & Providers:</span>
              <div className={styles.providerPillsRow}>
                {data.search_metadata.live_providers.map((p) => {
                  let pillClass = styles.pillUnavailable;
                  let icon = '○';
                  let label = 'Unavailable';

                  if (p.status === 'healthy') {
                    pillClass = styles.pillHealthy;
                    icon = '●';
                    label = p.products_found ? `${p.products_found} offers` : 'Healthy';
                  } else if (p.status === 'degraded') {
                    pillClass = styles.pillDegraded;
                    icon = '▲';
                    label = 'Degraded';
                  } else if (p.status === 'blocked') {
                    pillClass = styles.pillBlocked;
                    icon = '✕';
                    label = 'Blocked (Isolated)';
                  }

                  return (
                    <div
                      key={p.name}
                      className={`${styles.providerMiniCard} ${pillClass}`}
                      title={p.error || `${p.label}: ${p.products_found || 0} products found (${p.latency_ms || 0}ms)`}
                    >
                      <span className={styles.providerMiniName}>{p.label}</span>
                      <span className={styles.providerMiniStatus}>
                        {icon} {label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Empty State / Provider Diagnostics */}
          {productsList.length === 0 && (
            <div className={styles.emptyResultsCard}>
              <div className={styles.integrityBanner}>
                <span>🛡️</span>
                <span>Production Integrity: Zero Fabricated Data</span>
              </div>
              <h2>
                {data?.search_metadata.live_providers_configured === 0
                  ? 'Live Retail Data Providers Unconfigured'
                  : 'No active offers matched your constraints'}
              </h2>
              <p>
                {data?.search_metadata.unconfigured_notice ||
                  data?.search_metadata.demo_notice ||
                  'No retailer returned active offers matching this exact criteria right now.'}
              </p>

              {/* Provider Connection Matrix */}
              {data?.search_metadata.live_providers && data.search_metadata.live_providers.length > 0 && (
                <div className={styles.providerMatrix}>
                  {data.search_metadata.live_providers
                    .filter((p) => !p.is_demo)
                    .map((p) => (
                      <div key={p.name} className={styles.providerCard}>
                        <div className={styles.providerTop}>
                          <span className={styles.providerName}>{p.label}</span>
                          <span
                            className={`${styles.statusPill} ${
                              p.status === 'healthy'
                                ? styles.active
                                : p.status === 'blocked'
                                ? styles.blocked
                                : p.status === 'degraded'
                                ? styles.degraded
                                : styles.inactive
                            }`}
                          >
                            {p.status === 'healthy'
                              ? `● Healthy (${p.products_found || 0})`
                              : p.status === 'blocked'
                              ? '✕ Blocked (Isolated)'
                              : p.status === 'degraded'
                              ? '▲ Degraded'
                              : '○ Not Configured'}
                          </span>
                        </div>
                        {p.error && (
                          <div className={styles.providerErrorNote}>
                            {p.error}
                          </div>
                        )}
                        {p.required_env && p.required_env.length > 0 && !p.configured && (
                          <div className={styles.providerEnv}>
                            Env: {p.required_env.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )}

              <div className={styles.suggestionsBox}>
                <strong>Next Steps:</strong>
                <ul>
                  <li>
                    ShopBuddy dispatches parallel discovery to Google Scraper, Amazon, Flipkart, eBay, and Merchant Feeds.
                  </li>
                  <li>
                    ShopBuddy strictly refuses to show hallucinated or mock product offers in production.
                  </li>
                  <li>
                    Try broader search terms (e.g., "office chair", "air fryer", "laptop") to discover available live inventory.
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* Product Grid & Marketplace Filters */}
          {productsList.length > 0 && (
            <>
              {/* Marketplace Filter Bar */}
              {(availableMarketplaces.list.length > 1 || availableMarketplaces.hasQC) && (
                <div className={styles.marketplaceFilterBar}>
                  <span className={styles.filterLabel}>Filter Marketplace:</span>
                  <button
                    type="button"
                    onClick={() => setSelectedMarketplace('all')}
                    className={`${styles.marketplaceChip} ${selectedMarketplace === 'all' ? styles.activeChip : ''}`}
                  >
                    All ({productsList.length})
                  </button>

                  {availableMarketplaces.hasQC && (
                    <button
                      type="button"
                      onClick={() => setSelectedMarketplace('quick_commerce')}
                      className={`${styles.marketplaceChip} ${styles.qcChip} ${selectedMarketplace === 'quick_commerce' ? styles.activeChip : ''}`}
                    >
                      ⚡ Quick Commerce
                    </button>
                  )}

                  {availableMarketplaces.list.map((m) => {
                    const label = m.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                    const count = productsList.filter(
                      (p) =>
                        (p.sources || []).some((s) => s.toLowerCase().replace(/\s+/g, '_') === m) ||
                        (p.offers || []).some((o) => (o.retailer || '').toLowerCase().replace(/\s+/g, '_') === m) ||
                        (p.primary_retailer || '').toLowerCase().replace(/\s+/g, '_') === m
                    ).length;

                    return (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSelectedMarketplace(m)}
                        className={`${styles.marketplaceChip} ${selectedMarketplace === m ? styles.activeChip : ''}`}
                      >
                        {label} ({count})
                      </button>
                    );
                  })}
                </div>
              )}

              {filteredProducts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666' }}>
                  <p>No products found from {selectedMarketplace.replace(/_/g, ' ')}.</p>
                  <button
                    type="button"
                    onClick={() => setSelectedMarketplace('all')}
                    className={styles.retryBtn}
                    style={{ marginTop: '12px' }}
                  >
                    View All Products
                  </button>
                </div>
              ) : (
                <div className={styles.productGrid}>
                  {filteredProducts.map((prod, idx) => (
                    <ProductCard
                      key={`${prod.id}-${idx}`}
                      product={prod}
                      onCompareToggle={() => toggleComparison(prod.id)}
                      isCompared={comparisonItems.includes(prod.id)}
                    />
                  ))}
                </div>
              )}

              {/* Load More Button / Pagination */}
              {pagination?.has_next && (
                <div className={styles.loadMoreContainer}>
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className={styles.loadMoreBtn}
                  >
                    {loadingMore ? (
                      <>
                        <span className={styles.buttonSpinner} />
                        <span>Fetching next page of products...</span>
                      </>
                    ) : (
                      <>
                        <span>Load More Products ({productsList.length} of {totalCanonical})</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function DiscoverPage() {
  return (
    <Suspense fallback={<div style={{ padding: '60px 20px', textAlign: 'center' }}>Loading research engine...</div>}>
      <DiscoverContent />
    </Suspense>
  );
}
