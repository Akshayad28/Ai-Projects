'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Heart, Scale, ChevronDown, ChevronUp, Star } from 'lucide-react';
import { ProductCardDTO } from '@/lib/api';
import { useStore } from '@/store';
import { formatPrice } from '@/lib/utils';
import type { CurrencyCode } from '@/types';
import styles from './ProductCard.module.scss';

interface ProductCardProps {
  product: ProductCardDTO;
  onCompareToggle?: (product: ProductCardDTO) => void;
  isCompared?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onCompareToggle,
  isCompared = false,
}) => {
  const [showBreakdown, setShowBreakdown] = useState(false);
  const { wishlist, addToWishlist, removeFromWishlist } = useStore();

  const isWishlisted = wishlist.some(item => item.productId === product.id);

  const handleWishlistClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (isWishlisted) {
      removeFromWishlist(product.id);
    } else {
      addToWishlist({
        id: `w-${product.id}`,
        productId: product.id,
        targetPrice: product.best_price,
        currency: (product.currency || 'INR') as CurrencyCode,
        priceWhenAdded: product.best_price,
        addedAt: new Date().toISOString(),
      });
    }
  };

  const matchScore = product.recommendation?.match_score || 85;

  return (
    <article className={styles.card}>
      {/* Top Bar: Match Score & Action Badges */}
      <div className={styles.cardHeader}>
        <div className={styles.matchScoreBadge}>
          <span className={styles.matchScoreVal}>{matchScore}%</span>
          <span className={styles.matchScoreLabel}>Match</span>
        </div>

        <div className={styles.topActions}>
          <button
            type="button"
            onClick={handleWishlistClick}
            className={`${styles.actionIconBtn} ${isWishlisted ? styles.wishlisted : ''}`}
            aria-label={isWishlisted ? 'Remove from Wishlist' : 'Add to Wishlist'}
            title="Wishlist"
          >
            <Heart size={16} fill={isWishlisted ? 'currentColor' : 'none'} />
          </button>

          {onCompareToggle && (
            <button
              type="button"
              onClick={() => onCompareToggle(product)}
              className={`${styles.actionIconBtn} ${isCompared ? styles.compared : ''}`}
              aria-label="Compare Product"
              title="Compare side by side"
            >
              <Scale size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Product Image */}
      <Link href={`/product/${product.id}`} className={styles.imageContainer}>
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.title}
            className={styles.image}
            loading="lazy"
          />
        ) : (
          <div className={styles.imagePlaceholder}>
            <span>Image unavailable</span>
          </div>
        )}
      </Link>

      {/* Main Content */}
      <div className={styles.cardBody}>
        {/* Brand & Category hint */}
        <div className={styles.metaRow}>
          {product.brand && <span className={styles.brand}>{product.brand}</span>}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {product.is_quick_commerce && (
              <span className={styles.qcBadge}>
                ⚡ {product.quick_commerce_eta || '10-20 mins'}
              </span>
            )}
            {product.offers_count > 1 && (
              <span className={styles.offersCount}>
                {product.offers_count} offers
              </span>
            )}
          </div>
        </div>

        {/* Title */}
        <h3 className={styles.title}>
          <Link href={`/product/${product.id}`} className={styles.titleLink}>
            {product.title}
          </Link>
        </h3>

        {/* Dynamic Category Attributes (Adaptable) */}
        {product.card_attributes && product.card_attributes.length > 0 && (
          <div className={styles.attributesList}>
            {product.card_attributes.map((attr) => (
              <div key={attr.key} className={styles.attributeTag}>
                <span className={styles.attrLabel}>{attr.label}:</span>
                <span className={styles.attrValue}>
                  {String(attr.value)}{attr.unit ? ` ${attr.unit}` : ''}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Ratings & Reliability */}
        <div className={styles.ratingRow}>
          {product.rating ? (
            <div className={styles.ratingBadge}>
              <Star size={13} fill="#C58A32" color="#C58A32" />
              <span>{product.rating.toFixed(1)}</span>
              {product.review_count && (
                <span className={styles.reviewCount}>({product.review_count.toLocaleString()})</span>
              )}
            </div>
          ) : (
            <span className={styles.unratedText}>Verified product</span>
          )}

          {product.availability === 'in_stock' && (
            <span className={styles.inStockBadge}>In Stock</span>
          )}
        </div>

        {/* Price & Primary Retailer */}
        <div className={styles.priceRow}>
          <div className={styles.priceInfo}>
            <span className={styles.bestPrice}>
              {product.best_price ? formatPrice(product.best_price, (product.currency || 'INR') as CurrencyCode) : 'Check availability'}
            </span>
            {product.best_unit_price && (
              <span className={styles.unitPrice}>({product.best_unit_price})</span>
            )}
            {product.original_price && product.original_price > (product.best_price || 0) && (
              <span className={styles.originalPrice}>
                {formatPrice(product.original_price, (product.currency || 'INR') as CurrencyCode)}
              </span>
            )}
            {product.discount_percent && (
              <span className={styles.discountBadge}>
                {product.discount_percent}% OFF
              </span>
            )}
          </div>
          <span className={styles.retailerLabel}>via {product.primary_retailer}</span>
        </div>

        {/* Contributing Retailers row if multiple */}
        {product.sources && product.sources.length > 1 && (
          <div className={styles.retailersRow}>
            <span>Also at:</span>
            {product.sources.slice(0, 4).map((src) => (
              <span key={src} className={styles.retailerChip}>
                {src.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
            ))}
            {product.sources.length > 4 && (
              <span>+{product.sources.length - 4} more</span>
            )}
          </div>
        )}

        {/* "Why this?" Progressive Disclosure */}
        <div className={styles.whyThisArea}>
          <button
            type="button"
            onClick={() => setShowBreakdown(!showBreakdown)}
            className={styles.whyThisBtn}
            aria-expanded={showBreakdown}
          >
            <span>Why ShopBuddy picked this</span>
            {showBreakdown ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showBreakdown && product.recommendation && (
            <div className={styles.breakdownDetails}>
              {product.recommendation.reasons.length > 0 && (
                <div className={styles.reasonGroup}>
                  <div className={styles.groupHeading}>Positive matches:</div>
                  <ul className={styles.reasonList}>
                    {product.recommendation.reasons.map((r, i) => (
                      <li key={i} className={styles.positiveItem}>✓ {r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {product.recommendation.drawbacks.length > 0 && (
                <div className={styles.drawbackGroup}>
                  <div className={styles.groupHeading}>Considerations:</div>
                  <ul className={styles.reasonList}>
                    {product.recommendation.drawbacks.map((d, i) => (
                      <li key={i} className={styles.drawbackItem}>⚠ {d}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className={styles.footerActions}>
          <Link href={`/product/${product.id}`} className={styles.viewDealBtn}>
            <span>View Full Analysis & Offers</span>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#2ba0ff',
              display: 'inline-block',
              marginLeft: '4px'
            }} />
          </Link>
        </div>
      </div>
    </article>
  );
};
