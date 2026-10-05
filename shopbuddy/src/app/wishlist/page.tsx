'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Heart, Trash2, ExternalLink, ArrowRight } from 'lucide-react';
import { useStore } from '@/store';
import { getProductDetail } from '@/lib/api';
import { formatPrice } from '@/lib/utils';
import styles from './wishlist.module.scss';

export default function WishlistPage() {
  const { wishlist, removeFromWishlist, currency } = useStore();
  const [itemsWithDetails, setItemsWithDetails] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (wishlist.length === 0) {
      setItemsWithDetails([]);
      return;
    }

    setLoading(true);
    Promise.all(
      wishlist.map(async (item) => {
        try {
          const detail = await getProductDetail(item.productId);
          return { ...item, detail };
        } catch {
          return { ...item, detail: null };
        }
      })
    ).then((res) => {
      setItemsWithDetails(res);
      setLoading(false);
    });
  }, [wishlist]);

  if (wishlist.length === 0 && !loading) {
    return (
      <div className={styles.emptyContainer}>
        <Heart size={48} className={styles.emptyIcon} />
        <h1 className={styles.emptyTitle}>Your Wishlist is Empty</h1>
        <p className={styles.emptySubtitle}>
          Save products you are researching to monitor price changes, track retailer offers, and get drop alerts.
        </p>
        <Link href="/" className={styles.browseBtn}>
          Start Shopping Search
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.wishlistContainer}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.pageTitle}>Saved Products ({wishlist.length})</h1>
          <p className={styles.pageSubtitle}>
            Track real-time pricing and availability across retailers.
          </p>
        </div>
      </div>

      <div className={styles.itemsList}>
        {itemsWithDetails.map((item) => {
          const detail = item.detail;
          const bestOffer = detail?.offers?.[0];
          const currentPrice = bestOffer?.price_amount;

          return (
            <div key={item.id} className={styles.itemCard}>
              <div className={styles.thumbWrapper}>
                {detail?.image_urls?.[0] ? (
                  <img src={detail.image_urls[0]} alt={detail.title} className={styles.thumb} />
                ) : (
                  <div className={styles.noThumb}>No image</div>
                )}
              </div>

              <div className={styles.infoCol}>
                <div className={styles.brandRow}>{detail?.brand || 'Verified Product'}</div>
                <h2 className={styles.itemTitle}>
                  <Link href={`/product/${item.productId}`}>
                    {detail?.title || `Product ID: ${item.productId}`}
                  </Link>
                </h2>
                <div className={styles.addedDate}>
                  Saved on {new Date(item.addedAt).toLocaleDateString()}
                </div>
              </div>

              <div className={styles.priceCol}>
                <span className={styles.priceLabel}>Current Best Price</span>
                <span className={styles.currentPrice}>
                  {currentPrice
                    ? formatPrice(currentPrice, bestOffer.currency || currency)
                    : 'Check link'}
                </span>
                {item.priceWhenAdded && currentPrice && currentPrice < item.priceWhenAdded && (
                  <span className={styles.dropTag}>
                    Dropped {formatPrice(item.priceWhenAdded - currentPrice, currency)}
                  </span>
                )}
              </div>

              <div className={styles.actionsCol}>
                {bestOffer?.url && (
                  <a
                    href={bestOffer.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.viewDealBtn}
                  >
                    <span>View Deal</span>
                    <ExternalLink size={12} />
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => removeFromWishlist(item.productId)}
                  className={styles.deleteBtn}
                  title="Remove from wishlist"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
