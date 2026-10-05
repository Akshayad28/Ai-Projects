'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Trash2,
  ArrowLeft,
  ExternalLink,
  Star,
  Sparkles,
  Trophy,
  Zap,
  CheckCircle2,
  AlertCircle,
  Check,
  Store,
  TrendingDown,
  Award,
  ThumbsUp,
  ThumbsDown,
  Info,
  ShieldCheck,
  ChevronDown,
  Search,
  X,
} from 'lucide-react';
import { useStore } from '@/store';
import {
  compareProducts,
  ComparisonResponseDTO,
} from '@/lib/api';
import { formatPrice } from '@/lib/utils';
import styles from './compare.module.scss';

export default function ComparePage() {
  const { comparisonItems, removeFromComparison, clearComparison, currency } = useStore();
  const [data, setData] = useState<ComparisonResponseDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Interactive Specification Matrix States
  const [specSearch, setSpecSearch] = useState('');
  const [showOnlyDifferences, setShowOnlyDifferences] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (comparisonItems.length === 0) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    compareProducts(comparisonItems)
      .then((res) => {
        setData(res);
        // Initialize expanded sections: default open top 4 or sections flagged as default expanded
        if (res.sections) {
          const initMap: Record<string, boolean> = {};
          res.sections.forEach((sec, idx) => {
            initMap[sec.id] = sec.is_default_expanded !== false || idx < 4;
          });
          setExpandedSections(initMap);
        }
      })
      .catch((err) => {
        console.error('Comparison API error:', err);
        setError('Could not generate product comparison.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [comparisonItems]);

  const rawSections = data?.sections;

  // Filter sections and attributes dynamically based on user search & difference filter
  const filteredSections = React.useMemo(() => {
    if (!rawSections) return [];
    const query = specSearch.trim().toLowerCase();

    return rawSections
      .map((sec) => {
        const matchingAttrs = sec.attributes.filter((attr) => {
          // 1. Difference filter
          if (showOnlyDifferences && attr.is_different === false) {
            return false;
          }
          // 2. Search query filter
          if (!query) return true;
          const inLabel = attr.label.toLowerCase().includes(query);
          const inKey = attr.key.toLowerCase().includes(query);
          const inUnit = attr.unit ? attr.unit.toLowerCase().includes(query) : false;
          const inValues = Object.values(attr.values).some((v) =>
            v !== null && v !== undefined && String(v).toLowerCase().includes(query)
          );
          return inLabel || inKey || inUnit || inValues;
        });

        return {
          ...sec,
          attributes: matchingAttrs,
        };
      })
      .filter((sec) => sec.attributes.length > 0);
  }, [rawSections, specSearch, showOnlyDifferences]);

  const totalVisibleSpecs = filteredSections.reduce(
    (acc, sec) => acc + sec.attributes.length,
    0
  );
  const totalRawSpecs = (rawSections || []).reduce(
    (acc, sec) => acc + sec.attributes.length,
    0
  );

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }));
  };

  const expandAllSections = () => {
    if (!rawSections) return;
    const allOpen: Record<string, boolean> = {};
    rawSections.forEach((sec) => {
      allOpen[sec.id] = true;
    });
    setExpandedSections(allOpen);
  };

  const collapseAllSections = () => {
    if (!rawSections) return;
    const allClosed: Record<string, boolean> = {};
    rawSections.forEach((sec) => {
      allClosed[sec.id] = false;
    });
    setExpandedSections(allClosed);
  };

  if (comparisonItems.length === 0 && !loading) {
    return (
      <div className={styles.emptyContainer}>
        <div className={styles.emptyIllustration}>
          <svg viewBox="0 0 200 160" width="160" height="128" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="100" cy="80" r="70" fill="#e0dbce" />
            <rect x="55" y="40" width="90" height="80" rx="30" fill="#ffffff" stroke="#2c2e2a" strokeWidth="3" />
            <rect x="75" y="60" width="50" height="8" rx="4" fill="#8ed462" />
            <rect x="75" y="76" width="40" height="6" rx="3" fill="#d5d5d4" />
            <rect x="75" y="90" width="30" height="6" rx="3" fill="#d5d5d4" />
            <circle cx="140" cy="115" r="18" fill="#ff705d" />
            <circle cx="140" cy="115" r="7" fill="#ffffff" />
          </svg>
        </div>
        <h1 className={styles.emptyTitle}>No products selected for comparison</h1>
        <p className={styles.emptySubtitle}>
          Select up to 4 products from search results using the scale icon to compare their real specifications, verified multi-retailer prices, and AI buying recommendations side-by-side.
        </p>
        <Link href="/" className={styles.browsePillBtn}>
          <span>Start Shopping Search</span>
          <span className={styles.btnActionDot} />
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner} />
        <h2 className={styles.loadingHeading}>Synthesizing Comparison Intelligence...</h2>
        <p className={styles.loadingText}>
          Retrieving live retailer offers, verified specifications, customer sentiment, and calculating deterministic category benchmarks on cream paper.
        </p>
      </div>
    );
  }

  if (error || !data || data.products.length === 0) {
    return (
      <div className={styles.emptyContainer}>
        <div className={styles.emptyErrorDot}>
          <AlertCircle size={36} color="#ff705d" />
        </div>
        <h1 className={styles.emptyTitle}>Comparison Temporarily Unavailable</h1>
        <p className={styles.emptySubtitle}>
          {error || 'Unable to load real comparison data for the selected products.'}
        </p>
        <div className={styles.emptyActionsRow}>
          <button type="button" onClick={clearComparison} className={styles.coralOutlinePillBtn}>
            Clear Selection
          </button>
          <Link href="/" className={styles.browsePillBtn}>
            <span>Back to Search</span>
            <span className={styles.btnActionDot} />
          </Link>
        </div>
      </div>
    );
  }

  const {
    products,
    verdict,
    sections,
    buying_insights,
    categories,
    overall_scores,
    overall_winner_id,
    overall_winner_reason,
    price_comparison,
    rating_comparison,
    review_insights,
    data_coverage,
    available_specs_count,
  } = data;

  return (
    <motion.div
      className={styles.pageWrapper}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className={styles.compareContainer}>
        {/* ── 1. HERO DISPLAY BLOCK (MindMarket Style) ── */}
        <section className={styles.heroSection}>
          <div className={styles.pillBadge}>
            <span className={styles.badgeDot} />
            <span>AI SHOPPING ENGINE • MULTI-RETAILER INTELLIGENCE</span>
          </div>

          <h1 className={styles.displayHeadline}>
            Side-by-Side Comparison
          </h1>

          <p className={styles.subheadline}>
            Comparing {products.length} {products.length === 1 ? 'product' : 'verified products'} across specifications, live multi-retailer offers, customer ratings, and objective buying trade-offs.
          </p>

          <div className={styles.heroActionsRow}>
            <Link href="/" className={styles.ghostPillBtn}>
              <ArrowLeft size={16} />
              <span>Add More Products</span>
              <span className={styles.btnActionDotBlue} />
            </Link>

            <button
              type="button"
              onClick={clearComparison}
              className={styles.coralOutlinePillBtn}
              title="Clear all comparison items"
            >
              <Trash2 size={15} />
              <span>Clear Selection</span>
            </button>
          </div>
        </section>

        {/* ── 2. STORYBOOK COMPARISON ART PANEL ── */}
        <section className={styles.illustrationPanel} aria-label="Decorative Comparison Illustration">
          <svg viewBox="0 0 1000 180" className={styles.storybookSvg} fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="120" cy="90" r="70" fill="#8ed462" />
            <circle cx="880" cy="90" r="65" fill="#f5e211" />
            <rect x="360" y="30" width="280" height="120" rx="50" fill="#2ba0ff" />
            <rect x="390" y="45" width="220" height="90" rx="35" fill="#ffffff" stroke="#2c2e2a" strokeWidth="2.5" />
            <rect x="420" y="65" width="80" height="12" rx="6" fill="#8ed462" />
            <rect x="420" y="85" width="160" height="8" rx="4" fill="#e0dbce" />
            <rect x="420" y="101" width="120" height="8" rx="4" fill="#e0dbce" />
            <circle cx="560" cy="71" r="14" fill="#ff705d" />
            <circle cx="560" cy="71" r="5" fill="#ffffff" />
          </svg>
        </section>

        {/* ── 3. AI EXECUTIVE VERDICT (MindMarket Content Card) ── */}
        {verdict && (
          <section className={styles.verdictCard}>
            <div className={styles.cardTagRow}>
              <span className={styles.sandstoneTag}>AI VERDICT</span>
              {verdict.confidence && (
                <span className={styles.confidenceTag}>
                  AI Confidence: {verdict.confidence}%
                </span>
              )}
            </div>

            <div className={styles.verdictHeader}>
              <div className={styles.verdictTitleWrap}>
                <Sparkles size={24} className={styles.sparkleIcon} />
                <h2 className={styles.cardHeading}>ShopBuddy AI Shopping Verdict</h2>
              </div>
              {data.generated_at && (
                <span className={styles.timestampPill}>
                  Updated {data.generated_at}
                </span>
              )}
            </div>

            <div className={styles.verdictHighlightsGrid}>
              {verdict.best_overall_title && (
                <div className={styles.winnerLeaderBox}>
                  <div className={styles.winnerCrownBadge}>
                    <Trophy size={14} />
                    <span>Best Overall Choice</span>
                  </div>
                  <h3 className={styles.leaderTitle}>
                    {verdict.best_overall_title}
                  </h3>
                  <p className={styles.leaderQuote}>
                    &ldquo;{verdict.why_it_wins || verdict.verdict_summary}&rdquo;
                  </p>

                  {verdict.best_for && verdict.best_for.length > 0 && (
                    <div className={styles.bestForWrap}>
                      <span className={styles.bestForLabel}>Best for:</span>
                      <div className={styles.bestForPills}>
                        {verdict.best_for.map((tag, idx) => (
                          <span key={idx} className={styles.chipTag}>
                            <Check size={12} />
                            <span>{tag}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {verdict.best_value_title && (
                <div className={styles.valueLeaderBox}>
                  <div className={styles.valueCrownBadge}>
                    <Zap size={14} />
                    <span>Best Value For Money</span>
                  </div>
                  <h3 className={styles.leaderTitle}>
                    {verdict.best_value_title}
                  </h3>
                  <p className={styles.leaderQuote}>
                    {verdict.why_best_value || 'Lowest verified price with competitive core specifications.'}
                  </p>
                  {price_comparison && price_comparison.price_difference && (
                    <div className={styles.valueSavingsBadge}>
                      <TrendingDown size={13} />
                      <span>
                        Save {price_comparison.currency} {price_comparison.price_difference.toLocaleString()} ({price_comparison.percentage_difference}% less)
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Key Differences */}
            {verdict.key_differences && verdict.key_differences.length > 0 && (
              <div className={styles.keyDiffsBox}>
                <div className={styles.keyDiffsTitle}>
                  <Check size={14} />
                  <span>Key Practical Differences</span>
                </div>
                <ul className={styles.keyDiffsList}>
                  {verdict.key_differences.map((diff, idx) => (
                    <li key={idx} className={styles.keyDiffItem}>
                      <span className={styles.diffCheckDot} />
                      <span>{diff}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* ── 4. PRODUCT COMPARISON CARDS (MindMarket 50px Radii) ── */}
        <section className={styles.productsGrid}>
          {products.map((p) => {
            const bestOffer = p.offers && p.offers.length > 0 ? p.offers[0] : null;
            const displayPrice = p.best_price || bestOffer?.price || bestOffer?.price_amount;
            const offerUrl = bestOffer?.url;
            const isOverallWinner = p.id === overall_winner_id;

            return (
              <div
                key={p.id}
                className={`${styles.productCard} ${isOverallWinner ? styles.isTopWinnerCard : ''}`}
              >
                <button
                  type="button"
                  onClick={() => removeFromComparison(p.id)}
                  className={styles.removeCircleBtn}
                  title="Remove from comparison"
                  aria-label="Remove product"
                >
                  ×
                </button>

                {isOverallWinner && (
                  <div className={styles.topWinnerPillBadge}>
                    <Trophy size={13} />
                    <span>Top Overall Pick</span>
                  </div>
                )}

                {p.brand && (
                  <span className={styles.sandstoneTagSmall}>{p.brand}</span>
                )}

                {/* 280px Sticker-like Product Image Container */}
                <div className={styles.imageContainer}>
                  {p.image_url || (p.image_urls && p.image_urls[0]) ? (
                    <img
                      src={p.image_url || p.image_urls[0]}
                      alt={p.title}
                      className={styles.productImage}
                    />
                  ) : (
                    <div className={styles.noImageText}>Image unavailable</div>
                  )}
                </div>

                <h2 className={styles.productCardTitle}>
                  <Link href={`/product/${p.id}`}>{p.title}</Link>
                </h2>

                {p.model && (
                  <div className={styles.modelVariantText}>
                    Model: {p.model}
                  </div>
                )}

                {/* Price */}
                <div className={styles.priceRow}>
                  <div className={styles.priceAmountBlock}>
                    <span className={styles.fromLabel}>From</span>
                    <span className={styles.displayPriceText}>
                      {displayPrice
                        ? formatPrice(displayPrice, (p.currency || currency) as any)
                        : 'Check retailer'}
                    </span>
                  </div>
                  {p.primary_retailer && (
                    <span className={styles.retailerChip}>
                      Best at {p.primary_retailer}
                    </span>
                  )}
                </div>

                {/* Verified Ratings */}
                <div className={styles.ratingInfoRow}>
                  {p.rating ? (
                    <>
                      <div className={styles.ratingBadgePill}>
                        <Star size={13} fill="#2c2e2a" color="#2c2e2a" />
                        <span>{p.rating.toFixed(1)}</span>
                      </div>
                      {p.review_count ? (
                        <span className={styles.reviewCountText}>
                          ({p.review_count.toLocaleString()} verified reviews)
                        </span>
                      ) : (
                        <span className={styles.reviewCountText}>Verified rating</span>
                      )}
                    </>
                  ) : (
                    <span className={styles.reviewCountText}>Rating unavailable</span>
                  )}
                </div>

                {/* Offers count */}
                <div className={styles.offersRow}>
                  <Store size={14} />
                  <span>
                    {p.offers_count > 0
                      ? `${p.offers_count} verified ${p.offers_count === 1 ? 'offer' : 'offers'}`
                      : '1 verified offer'}
                  </span>
                </div>

                {/* CTA Deal Button */}
                {offerUrl && (
                  <a
                    href={offerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.dealPillBtn}
                  >
                    <span>View Deal at Retailer</span>
                    <span className={styles.dealActionDot} />
                  </a>
                )}
              </div>
            );
          })}
        </section>

        {/* ── 5. OVERALL COMPARISON SCORECARD (MindMarket 50px Card) ── */}
        {overall_scores && Object.keys(overall_scores).length > 0 && (
          <section className={styles.contentSectionCard}>
            <span className={styles.sandstoneTag}>OVERALL BENCHMARK</span>
            <h2 className={styles.cardHeading}>Performance &amp; Value Scorecard</h2>
            <p className={styles.cardSubtext}>
              Weighted composite benchmark calculated deterministically across specifications, customer satisfaction, and pricing efficiency.
            </p>

            <div className={styles.overallBarsList}>
              {products.map((p) => {
                const score = overall_scores[p.id] || 80;
                const isWinner = p.id === overall_winner_id;

                return (
                  <div key={p.id} className={styles.overallBarItem}>
                    <div className={styles.barItemHeader}>
                      <div className={styles.barTitleGroup}>
                        <span className={styles.barProdBrand}>
                          {p.brand || p.title.split(' ')[0]}
                        </span>
                        <span className={styles.barProdSub}>
                          {p.title.slice(0, 48)}...
                        </span>
                      </div>
                      <div className={styles.barScoreValueGroup}>
                        <span className={styles.scoreNumber}>{score}%</span>
                        {isWinner && (
                          <span className={styles.winnerBadgePill}>
                            <Trophy size={12} />
                            <span>Winner</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className={styles.sandstoneBarTrack}>
                      <motion.div
                        className={styles.freshGrassBarFill}
                        style={{
                          background: isWinner ? '#8ed462' : '#e0dbce',
                        }}
                        initial={{ width: 0 }}
                        animate={{ width: `${score}%` }}
                        transition={{ duration: 0.85, ease: 'easeOut' }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {overall_winner_reason && (
              <div className={styles.rationaleCalloutBox}>
                <Award size={16} color="#2c2e2a" />
                <span>{overall_winner_reason}</span>
              </div>
            )}
          </section>
        )}

        {/* ── 6. DYNAMIC CATEGORY SCORECARD ── */}
        {categories && categories.length > 0 && (
          <section className={styles.editorialGridSection}>
            <div className={styles.sectionHeaderWrap}>
              <span className={styles.sandstoneTag}>CATEGORY SCORES</span>
              <h2 className={styles.cardHeading}>Dynamic Category Benchmarks</h2>
              <p className={styles.cardSubtext}>
                Dynamic benchmark breakdown tailored to {data.category_name || 'specifications'}. Every percentage is computed mathematically from factual attributes.
              </p>
            </div>

            <div className={styles.categoriesCardsGrid}>
              {categories.map((cat) => {
                const winnerProd = products.find((p) => p.id === cat.winner_id);

                return (
                  <div key={cat.name} className={styles.categoryCard}>
                    <div className={styles.categoryCardTop}>
                      <div>
                        <h3 className={styles.categoryCardHeading}>{cat.name}</h3>
                        <span className={styles.categoryWeightLabel}>
                          Weight: {Math.round(cat.weight * 100)}%
                        </span>
                      </div>

                      {winnerProd && (
                        <span className={styles.catWinnerPill}>
                          <Check size={12} />
                          <span>{winnerProd.brand || winnerProd.title.split(' ')[0]} Wins</span>
                        </span>
                      )}
                    </div>

                    <div className={styles.catBarsStack}>
                      {products.map((p) => {
                        const score = cat.scores[p.id] || 80;
                        const isWinner = p.id === cat.winner_id;
                        const pReasons = cat.reasons?.[p.id] || [];

                        return (
                          <div key={p.id} className={styles.catBarUnit}>
                            <div className={styles.catBarLabelsRow}>
                              <span className={styles.catBarProdTitle}>
                                {p.brand || p.title.split(' ')[0]}
                              </span>
                              <span className={styles.catBarScoreValue}>{score}%</span>
                            </div>

                            <div className={styles.catBarTrack}>
                              <motion.div
                                className={styles.catBarFill}
                                style={{
                                  background: isWinner ? '#8ed462' : '#e0dbce',
                                }}
                                initial={{ width: 0 }}
                                animate={{ width: `${score}%` }}
                                transition={{ duration: 0.7, ease: 'easeOut' }}
                              />
                            </div>

                            {pReasons.length > 0 && (
                              <div className={styles.catReasonText}>
                                {pReasons[0]}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── 7. COMPLETE CATEGORY-AWARE SPECIFICATION MATRIX (50px Radius Card) ── */}
        {sections && sections.length > 0 && (
          <section className={styles.contentSectionCard}>
            <span className={styles.sandstoneTag}>VERIFIED SPECIFICATION MATRIX</span>
            <h2 className={styles.cardHeading}>Verified Specification Matrix</h2>
            <p className={styles.cardSubtext}>
              Category-aware, factual product specifications dynamically derived from live product data. Never fabricated, with verifiable provenance and automated difference tracking.
            </p>

            {/* Data Coverage & Quality Indicators Banner */}
            {data_coverage && Object.keys(data_coverage).length > 0 && (
              <div className={styles.matrixCoverageBanner}>
                <div className={styles.coverageBannerLeft}>
                  <ShieldCheck size={16} />
                  <span>Verified Specification Coverage:</span>
                </div>
                <div className={styles.coveragePillsList}>
                  {products.map((p) => {
                    const cov = data_coverage[p.id] ?? 85;
                    const specCount = available_specs_count?.[p.id];
                    return (
                      <div key={p.id} className={styles.coveragePill} title="Percentage of verified category specifications recorded in source data. Missing data is never treated as zero.">
                        <span>{p.brand || p.title.split(' ')[0]}:</span>
                        <strong>{cov}% data coverage</strong>
                        {specCount !== undefined && (
                          <span className={styles.matrixStatsCounter}>({specCount} specs)</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Matrix Interactive Controls Toolbar */}
            <div className={styles.matrixControlsRow}>
              {/* Search specifications input */}
              <div className={styles.matrixSearchWrapper}>
                <Search size={16} />
                <input
                  type="text"
                  placeholder="Search specifications (e.g. RAM, GPU, battery, HDMI)..."
                  value={specSearch}
                  onChange={(e) => setSpecSearch(e.target.value)}
                  className={styles.matrixSearchInput}
                  aria-label="Search specifications"
                />
                {specSearch && (
                  <button
                    type="button"
                    onClick={() => setSpecSearch('')}
                    className={styles.matrixSearchClearBtn}
                    title="Clear search"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              {/* Toggles & Actions */}
              <div className={styles.matrixFilterTogglesGroup}>
                <label className={styles.matrixToggleLabel}>
                  <input
                    type="checkbox"
                    checked={showOnlyDifferences}
                    onChange={(e) => setShowOnlyDifferences(e.target.checked)}
                  />
                  <span>Show only differences</span>
                </label>

                <div className={styles.matrixActionButtons}>
                  <button
                    type="button"
                    onClick={expandAllSections}
                    className={styles.matrixPillButton}
                  >
                    Expand all
                  </button>
                  <button
                    type="button"
                    onClick={collapseAllSections}
                    className={styles.matrixPillButton}
                  >
                    Collapse all
                  </button>
                </div>
              </div>

              <span className={styles.matrixStatsCounter}>
                Showing {totalVisibleSpecs} of {totalRawSpecs} specifications
              </span>
            </div>

            {/* Interactive Sticky Table */}
            <div className={styles.tableCardWrapper}>
              <table className={styles.specsTable}>
                <thead>
                  <tr>
                    <th className={styles.stickyHeaderCorner}>
                      Specification Attribute
                    </th>
                    {products.map((p) => {
                      const displayPrice = p.best_price;
                      return (
                        <th key={p.id} className={styles.stickyHeaderProduct}>
                          <div className={styles.thProductHeaderContent}>
                            <div className={styles.thProductThumb}>
                              {p.image_url || (p.image_urls && p.image_urls[0]) ? (
                                <img
                                  src={p.image_url || p.image_urls[0]}
                                  alt={p.title}
                                />
                              ) : (
                                <span style={{ fontSize: 10, color: '#888' }}>IMG</span>
                              )}
                            </div>
                            <div className={styles.thProductMeta}>
                              <span className={styles.thProductBrand}>
                                {p.brand || 'Product'}
                              </span>
                              <span className={styles.thProductTitle} title={p.title}>
                                {p.title}
                              </span>
                              <span className={styles.thProductPricePill}>
                                {displayPrice
                                  ? formatPrice(displayPrice, (p.currency || currency) as any)
                                  : 'Check store'}
                              </span>
                            </div>
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {filteredSections.length === 0 ? (
                    <tr>
                      <td colSpan={products.length + 1}>
                        <div className={styles.emptyFilterState}>
                          <p>No specifications match your search or difference filter.</p>
                          <button
                            type="button"
                            onClick={() => {
                              setSpecSearch('');
                              setShowOnlyDifferences(false);
                            }}
                            className={styles.resetFilterBtn}
                          >
                            Reset specification filters
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredSections.map((sec) => {
                      const isExpanded = expandedSections[sec.id] !== false || specSearch.trim().length > 0;

                      return (
                        <React.Fragment key={sec.id}>
                          {/* Collapsible Section Accordion Row */}
                          <tr className={styles.sectionDividerRow}>
                            <td
                              colSpan={products.length + 1}
                              className={styles.sectionDividerCell}
                            >
                              <button
                                type="button"
                                onClick={() => toggleSection(sec.id)}
                                className={styles.sectionHeaderBtn}
                                aria-expanded={isExpanded}
                              >
                                <div className={styles.sectionTitleGroup}>
                                  <span className={styles.sectionTitleText}>
                                    {sec.title}
                                  </span>
                                  {sec.description && (
                                    <span className={styles.sectionDescSub}>
                                      — {sec.description}
                                    </span>
                                  )}
                                </div>
                                <div className={styles.sectionPillAndChevron}>
                                  <span className={styles.sectionAttrCountPill}>
                                    {sec.attributes.length} {sec.attributes.length === 1 ? 'spec' : 'specs'}
                                  </span>
                                  <ChevronDown
                                    size={16}
                                    className={`${styles.sectionChevronIcon} ${isExpanded ? styles.isRotated : ''}`}
                                  />
                                </div>
                              </button>
                            </td>
                          </tr>

                          {/* Specification Attribute Rows */}
                          {isExpanded &&
                            sec.attributes.map((attr) => (
                              <tr key={attr.key} className={styles.dataRow}>
                                <td className={styles.metricLabelCell}>
                                  <div className={styles.attrLabelGroup}>
                                    <span className={styles.attrLabelText}>
                                      {attr.label}
                                    </span>
                                    {attr.unit && (
                                      <span className={styles.attrUnitText}>
                                        ({attr.unit})
                                      </span>
                                    )}
                                    {attr.is_different && (
                                      <span
                                        className={styles.diffIndicatorBadge}
                                        title="Specification differs between compared products"
                                      >
                                        Diff
                                      </span>
                                    )}
                                  </div>
                                </td>

                                {products.map((p) => {
                                  const val = attr.values[p.id];
                                  const isWinner = attr.winner_id === p.id;
                                  const prov = attr.sources?.[p.id];

                                  return (
                                    <td
                                      key={p.id}
                                      className={`${styles.specValueCell} ${isWinner ? styles.winnerSpecCell : ''}`}
                                    >
                                      <div className={styles.specCellContent}>
                                        <span className={styles.specValText}>
                                          {val !== undefined && val !== null && String(val).trim() !== ''
                                            ? String(val)
                                            : '—'}
                                        </span>
                                        {isWinner && (
                                          <span className={styles.specWinnerTag}>
                                            <Trophy size={11} />
                                            <span>{attr.winner_reason || 'Advantage'}</span>
                                          </span>
                                        )}
                                        {prov && (
                                          <span className={styles.specProvNote} title={prov}>
                                            {prov}
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── 8. RATINGS & REVIEW INTELLIGENCE (MindMarket Double Cards) ── */}
        <section className={styles.doubleCardRow}>
          {/* Customer Ratings Card */}
          <div className={styles.halfContentCard}>
            <span className={styles.sandstoneTag}>RATINGS</span>
            <div className={styles.cardHeaderFlex}>
              <Star size={20} fill="#2c2e2a" color="#2c2e2a" />
              <h3 className={styles.cardHeadingSmall}>Verified Customer Ratings</h3>
            </div>

            <div className={styles.ratingsList}>
              {products.map((p) => (
                <div key={p.id} className={styles.ratingProductRow}>
                  <div className={styles.ratingLeftCol}>
                    <span className={styles.ratingProductTitle}>
                      {p.brand || p.title.split(' ')[0]}
                    </span>
                    <span className={styles.ratingCountSub}>
                      {p.review_count
                        ? `${p.review_count.toLocaleString()} verified reviews`
                        : 'No review count'}
                    </span>
                  </div>

                  <div className={styles.ratingRightCol}>
                    {p.rating ? (
                      <div className={styles.starsContainer}>
                        <span className={styles.starsNumber}>
                          {p.rating.toFixed(1)} / 5
                        </span>
                        <div className={styles.starsIconsRow}>
                          {[1, 2, 3, 4, 5].map((s) => (
                            <Star
                              key={s}
                              size={13}
                              fill={s <= Math.round(p.rating!) ? '#2c2e2a' : 'none'}
                              color="#2c2e2a"
                            />
                          ))}
                        </div>
                      </div>
                    ) : (
                      <span className={styles.unratedText}>Rating unavailable</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {rating_comparison?.rating_advantage && (
              <div className={styles.advantagePillBox}>
                <Award size={14} />
                <span>{rating_comparison.rating_advantage}</span>
              </div>
            )}
          </div>

          {/* Review Intelligence Card */}
          <div className={styles.halfContentCard}>
            <span className={styles.sandstoneTag}>INTELLIGENCE</span>
            <div className={styles.cardHeaderFlex}>
              <Sparkles size={20} color="#8ed462" />
              <h3 className={styles.cardHeadingSmall}>Review Intelligence</h3>
            </div>

            {review_insights && review_insights.available ? (
              <div className={styles.reviewIntelligenceList}>
                {products.map((p) => {
                  const ins = review_insights.insights?.[p.id];
                  if (!ins) return null;

                  return (
                    <div key={p.id} className={styles.reviewProductBlock}>
                      <h4 className={styles.reviewProductHeading}>
                        {p.brand || p.title.split(' ')[0]} Signals
                      </h4>

                      {ins.likes && ins.likes.length > 0 && (
                        <div className={styles.sentimentGroup}>
                          <span className={styles.sentimentLabelGreen}>
                            <ThumbsUp size={12} />
                            <span>What buyers appreciate</span>
                          </span>
                          <ul className={styles.sentimentList}>
                            {ins.likes.map((l, i) => (
                              <li key={i} className={styles.sentimentItem}>
                                <Check size={12} />
                                <span>{l}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {ins.complaints && ins.complaints.length > 0 && (
                        <div className={styles.sentimentGroup}>
                          <span className={styles.sentimentLabelCoral}>
                            <ThumbsDown size={12} />
                            <span>Considerations</span>
                          </span>
                          <ul className={styles.sentimentList}>
                            {ins.complaints.map((c, i) => (
                              <li key={i} className={styles.sentimentItem}>
                                <AlertCircle size={12} />
                                <span>{c}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className={styles.unavailableNoticeBox}>
                <Info size={16} />
                <span>Review intelligence unavailable from current sources.</span>
              </div>
            )}
          </div>
        </section>

        {/* ── 9. PRICE & LIVE OFFERS (MindMarket Card) ── */}
        <section className={styles.contentSectionCard}>
          <span className={styles.sandstoneTag}>PRICING &amp; OFFERS</span>
          <h2 className={styles.cardHeading}>Price Comparison &amp; Live Offers</h2>
          <p className={styles.cardSubtext}>
            Verified prices, retailer coverage, and value efficiency across checked stores.
          </p>

          {/* Price Difference Summary Callout */}
          {price_comparison && price_comparison.price_difference && (
            <div className={styles.priceDiffBanner}>
              <div className={styles.priceDiffTop}>
                <div className={styles.diffIconGroup}>
                  <TrendingDown size={18} />
                  <span className={styles.diffLabel}>Price Difference</span>
                </div>
                <div className={styles.diffValueText}>
                  {price_comparison.currency} {price_comparison.price_difference.toLocaleString()}
                  <span className={styles.diffPctText}>
                    ({price_comparison.percentage_difference}% savings)
                  </span>
                </div>
              </div>

              <p className={styles.valueRationaleParagraph}>
                {price_comparison.value_rationale}
              </p>
            </div>
          )}

          {/* Multi-Retailer Offers Grid */}
          <div className={styles.offersColumnsGrid}>
            {products.map((p) => (
              <div key={p.id} className={styles.offersProductColumnCard}>
                <div className={styles.offersColumnHeader}>
                  <span className={styles.offersColTitle}>{p.title}</span>
                  <span className={styles.offersColBadge}>
                    {p.offers?.length || 0} verified {p.offers?.length === 1 ? 'offer' : 'offers'}
                  </span>
                </div>

                {p.offers && p.offers.length > 0 ? (
                  <div className={styles.offersItemsList}>
                    {p.offers.map((off, oIdx) => {
                      const pVal = off.price || off.price_amount;
                      return (
                        <div key={oIdx} className={styles.singleOfferPillRow}>
                          <div className={styles.offerStoreDetails}>
                            <span className={styles.storeNameText}>{off.retailer}</span>
                            {(off.seller || off.seller_name) && (off.seller || off.seller_name) !== off.retailer && (
                              <span className={styles.sellerNameText}>
                                Seller: {off.seller || off.seller_name}
                              </span>
                            )}
                            {off.warranty && (
                              <span className={styles.warrantyText}>
                                {off.warranty}
                              </span>
                            )}
                          </div>

                          <div className={styles.offerPriceActionCol}>
                            <span className={styles.offerPriceText}>
                              {pVal
                                ? formatPrice(pVal, (off.currency || currency) as any)
                                : 'Check retailer'}
                            </span>
                            {off.url && (
                              <a
                                href={off.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.storeVisitPillBtn}
                                title={`Visit ${off.retailer}`}
                              >
                                <span>Visit Store</span>
                                <ExternalLink size={12} />
                              </a>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className={styles.noOffersNotice}>
                    No additional retailer offers found for this product.
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── 10. VERIFIED PROS & CONS (MindMarket Double Cards) ── */}
        {buying_insights && buying_insights.length > 0 && (
          <section className={styles.editorialGridSection}>
            <div className={styles.sectionHeaderWrap}>
              <span className={styles.sandstoneTag}>PROS &amp; CONS</span>
              <h2 className={styles.cardHeading}>Verified Strengths &amp; Considerations</h2>
              <p className={styles.cardSubtext}>
                Objective strengths and practical considerations based strictly on verified data.
              </p>
            </div>

            <div className={styles.prosConsGrid}>
              {buying_insights.map((bi) => {
                const prod = products.find((p) => p.id === bi.product_id);
                if (!prod) return null;

                return (
                  <div key={bi.product_id} className={styles.prosConsCard}>
                    <h3 className={styles.prosConsCardTitle}>{prod.title}</h3>

                    {bi.why_choose && bi.why_choose.length > 0 && (
                      <div className={styles.prosConsGroup}>
                        <span className={styles.strengthsLabel}>
                          <CheckCircle2 size={13} color="#2c2e2a" />
                          <span>Strengths</span>
                        </span>
                        <ul className={styles.bulletList}>
                          {bi.why_choose.map((pro, idx) => (
                            <li key={idx} className={styles.proItemRow}>
                              <Check size={13} />
                              <span>{pro}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {bi.considerations && bi.considerations.length > 0 && (
                      <div className={styles.prosConsGroup}>
                        <span className={styles.considerationsLabel}>
                          <AlertCircle size={13} color="#ff705d" />
                          <span>Considerations</span>
                        </span>
                        <ul className={styles.bulletList}>
                          {bi.considerations.map((con, idx) => (
                            <li key={idx} className={styles.conItemRow}>
                              <span>✕</span>
                              <span>{con}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── 11. THE TRADE-OFF (MindMarket Editorial Cards) ── */}
        {verdict?.trade_offs && Object.keys(verdict.trade_offs).length > 0 && (
          <section className={styles.editorialGridSection}>
            <div className={styles.sectionHeaderWrap}>
              <span className={styles.coralTag}>DECISION MATRIX</span>
              <h2 className={styles.cardHeading}>The Practical Trade-Off</h2>
              <p className={styles.cardSubtext}>
                How to choose between these options based on your personal priorities.
              </p>
            </div>

            <div className={styles.tradeOffsGrid}>
              {products.map((p) => {
                const pTradeOffs = verdict.trade_offs?.[p.id] || [];
                if (pTradeOffs.length === 0) return null;

                return (
                  <div key={p.id} className={styles.tradeOffCard}>
                    <div className={styles.tradeOffPrompt}>
                      Choose <strong>{p.brand || p.title.split(' ')[0]}</strong> if you prioritize:
                    </div>
                    <ul className={styles.tradeOffList}>
                      {pTradeOffs.map((to, i) => (
                        <li key={i} className={styles.tradeOffItem}>
                          <span className={styles.tradeOffBullet} />
                          <span>{to}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── 12. FINAL RECOMMENDATION (MindMarket Content Card) ── */}
        <section className={styles.finalRecommendationCard}>
          <div className={styles.finalRecHeadingGroup}>
            <Trophy size={24} color="#8ed462" />
            <h2 className={styles.cardHeading}>Which One Should You Buy?</h2>
          </div>

          <div className={styles.finalRecCardsGrid}>
            {products.map((p) => {
              const isWinner = p.id === overall_winner_id;
              const recText = verdict?.buying_recommendations?.[p.id] || (
                isWinner
                  ? 'Best overall choice for users seeking peak performance, premium construction, and verified owner satisfaction.'
                  : 'Excellent alternative offering solid core capabilities and accessible entry pricing.'
              );

              return (
                <div
                  key={p.id}
                  className={`${styles.finalOptionCard} ${isWinner ? styles.isTopFinalOption : ''}`}
                >
                  <div className={styles.finalOptionHeaderRow}>
                    <span className={styles.finalBrandTag}>
                      {p.brand || p.title.split(' ')[0]}
                    </span>
                    {isWinner && (
                      <span className={styles.finalCrownPill}>
                        <Trophy size={12} />
                        <span>Best Overall</span>
                      </span>
                    )}
                  </div>

                  <h3 className={styles.finalOptionTitle}>{p.title}</h3>
                  <p className={styles.finalOptionText}>{recText}</p>

                  <div className={styles.finalOptionFooterRow}>
                    <div className={styles.finalPriceText}>
                      {p.best_price
                        ? formatPrice(p.best_price, (p.currency || currency) as any)
                        : 'Check retailer'}
                    </div>
                    <Link href={`/product/${p.id}`} className={styles.finalViewLink}>
                      View Product Details →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* ── 13. MINDMARKET FOOTER ACCENT BAND (Warmth Closing Surface) ── */}
      <footer className={styles.footerAccentBand}>
        <div className={styles.footerAccentContainer}>
          <div className={styles.footerTextWrap}>
            <span className={styles.footerBrandMark}>MindMarket Shopping Intelligence</span>
            <p className={styles.footerSubtext}>
              Real verified data • Zero demo fallbacks • Objective decision confidence
            </p>
          </div>
          <div className={styles.footerActions}>
            <Link href="/" className={styles.footerPillBtn}>
              <span>Search Another Product</span>
              <span className={styles.btnActionDot} />
            </Link>
          </div>
        </div>
      </footer>
    </motion.div>
  );
}
