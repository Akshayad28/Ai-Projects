'use client';

import React, { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft, 
  ExternalLink, 
  Heart, 
  Scale, 
  Star, 
  ShieldCheck, 
  Truck, 
  RotateCcw, 
  Clock, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import { getProductDetail } from '@/lib/api';
import { PriceHistoryChart } from '@/components/price/PriceHistoryChart';
import { useStore } from '@/store';
import { formatPrice } from '@/lib/utils';
import styles from './product.module.scss';

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { wishlist, addToWishlist, removeFromWishlist, comparisonItems, toggleComparison } = useStore();

  useEffect(() => {
    setLoading(true);
    getProductDetail(id)
      .then((data) => {
        setProduct(data);
      })
      .catch((err) => {
        console.error('Fetch product detail failed:', err);
        setError('Could not load product details.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner} />
        <p>Loading canonical product offers &amp; specs...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className={styles.errorContainer}>
        <h2>Product Not Found</h2>
        <p>{error || 'This product does not exist in the catalog.'}</p>
        <Link href="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          <span>Back to Discover</span>
        </Link>
      </div>
    );
  }

  const isWishlisted = wishlist.some((item) => item.productId === product.id);
  const isCompared = comparisonItems.includes(product.id);

  const bestOffer = product.offers && product.offers.length > 0
    ? product.offers.reduce((prev: any, curr: any) =>
        (curr.price_amount || Infinity) < (prev.price_amount || Infinity) ? curr : prev
      )
    : null;

  const handleWishlistToggle = () => {
    if (isWishlisted) {
      removeFromWishlist(product.id);
    } else {
      addToWishlist({
        id: `w-${product.id}`,
        productId: product.id,
        targetPrice: bestOffer?.price_amount,
        currency: (bestOffer?.currency || 'INR') as any,
        priceWhenAdded: bestOffer?.price_amount,
        addedAt: new Date().toISOString(),
      });
    }
  };

  return (
    <div className={styles.detailWrapper}>
      {/* Breadcrumb / Back button */}
      <div className={styles.navRow}>
        <Link href="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          <span>Back to Search</span>
        </Link>
      </div>

      <div className={styles.mainGrid}>
        {/* Left Column: Image */}
        <div className={styles.leftCol}>
          <div className={styles.imageCard}>
            {product.image_urls && product.image_urls.length > 0 ? (
              <img
                src={product.image_urls[0]}
                alt={product.title}
                className={styles.mainImage}
              />
            ) : (
              <div className={styles.noImage}>No image available</div>
            )}
          </div>

          {/* Price History Observations */}
          <div className={styles.historyCard}>
            <h3 className={styles.cardSectionTitle}>Verified Price History</h3>
            <p className={styles.cardSectionSubtitle}>
              Plotted strictly from verified historical observations. Synthetic dates and numbers are never generated.
            </p>
            <PriceHistoryChart
              observations={product.price_observations || []}
              currency={bestOffer?.currency || 'INR'}
              height={180}
            />
          </div>
        </div>

        {/* Right Column: Title, Specs, Retailers Table */}
        <div className={styles.rightCol}>
          <div className={styles.productMeta}>
            {product.brand && <span className={styles.brandBadge}>{product.brand}</span>}
            {product.category_id && <span className={styles.categoryBadge}>{product.category_id}</span>}
          </div>

          <h1 className={styles.title}>{product.title}</h1>

          {/* Rating */}
          <div className={styles.ratingRow}>
            {product.rating ? (
              <div className={styles.stars}>
                <Star size={16} fill="#C58A32" color="#C58A32" />
                <span className={styles.ratingNum}>{product.rating.toFixed(1)}</span>
                {product.review_count && (
                  <span className={styles.revCount}>({product.review_count.toLocaleString()} customer reviews)</span>
                )}
              </div>
            ) : (
              <span className={styles.unrated}>Verified product identity</span>
            )}
          </div>

          {/* Best Price Header */}
          <div className={styles.bestPriceBox}>
            <div className={styles.priceColumn}>
              <span className={styles.bestPriceLabel}>Best Verified Price</span>
              <div className={styles.bestPriceVal}>
                {bestOffer?.price_amount
                  ? formatPrice(bestOffer.price_amount, bestOffer.currency)
                  : 'Check retailer link'}
              </div>
              {bestOffer?.original_price && bestOffer.original_price > bestOffer.price_amount && (
                <div className={styles.strikethroughPrice}>
                  List price: {formatPrice(bestOffer.original_price, bestOffer.currency)}
                </div>
              )}
            </div>

            <div className={styles.actionBtns}>
              <button
                type="button"
                onClick={handleWishlistToggle}
                className={`${styles.secondaryBtn} ${isWishlisted ? styles.activeWish : ''}`}
              >
                <Heart size={16} fill={isWishlisted ? 'currentColor' : 'none'} />
                <span>{isWishlisted ? 'Saved' : 'Wishlist'}</span>
              </button>

              <button
                type="button"
                onClick={() => toggleComparison(product.id)}
                className={`${styles.secondaryBtn} ${isCompared ? styles.activeCompare : ''}`}
              >
                <Scale size={16} />
                <span>{isCompared ? 'Comparing' : 'Compare'}</span>
              </button>
            </div>
          </div>

          {/* Retailer Offers Comparison Table */}
          <div className={styles.offersSection}>
            <h2 className={styles.sectionTitle}>
              Compare Retailer Offers ({product.offers?.length || 0})
            </h2>
            <div className={styles.offersTable}>
              {product.offers?.map((offer: any, idx: number) => (
                <div key={idx} className={styles.offerRow}>
                  <div className={styles.retailerCol}>
                    <strong className={styles.retailerName}>{offer.retailer_name}</strong>
                    <div className={styles.verifiedTag}>
                      <ShieldCheck size={12} />
                      <span>Verified Provider</span>
                    </div>
                  </div>

                  <div className={styles.offerMetaCol}>
                    <div className={styles.deliveryText}>
                      <Truck size={12} />
                      <span>{offer.shipping_text || 'Standard delivery'}</span>
                    </div>
                    {offer.warranty && (
                      <div className={styles.warrantyText}>{offer.warranty}</div>
                    )}
                  </div>

                  <div className={styles.offerPriceCol}>
                    <span className={styles.rowPrice}>
                      {offer.price_amount
                        ? formatPrice(offer.price_amount, offer.currency)
                        : 'Unavailable'}
                    </span>
                  </div>

                  <div className={styles.offerCtaCol}>
                    {offer.url ? (
                      <a
                        href={offer.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.viewDealBtn}
                      >
                        <span>View Deal</span>
                        <ExternalLink size={13} />
                      </a>
                    ) : (
                      <span className={styles.noUrl}>No direct link</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Description */}
          {product.description && (
            <div className={styles.descSection}>
              <h3 className={styles.cardSectionTitle}>Product Overview</h3>
              <p className={styles.descText}>{product.description}</p>
            </div>
          )}

          {/* Specifications Table */}
          {product.specs && Object.keys(product.specs).length > 0 && (
            <div className={styles.specsSection}>
              <h3 className={styles.cardSectionTitle}>Normalized Specifications</h3>
              <dl className={styles.specsGrid}>
                {Object.entries(product.specs).map(([key, val]) => (
                  <div key={key} className={styles.specItem}>
                    <dt className={styles.specKey}>{key.replace(/_/g, ' ')}</dt>
                    <dd className={styles.specVal}>{String(val)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
