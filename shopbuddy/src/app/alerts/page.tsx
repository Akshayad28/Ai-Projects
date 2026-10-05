'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Bell, BellRing, Plus, ArrowRight, ShieldCheck } from 'lucide-react';
import { useStore } from '@/store';
import { formatPrice } from '@/lib/utils';
import styles from './alerts.module.scss';

export default function AlertsPage() {
  const { priceAlerts, currency } = useStore();

  return (
    <div className={styles.alertsContainer}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.pageTitle}>Price Drop Alerts</h1>
          <p className={styles.pageSubtitle}>
            ShopBuddy continuously monitors retailer prices and alerts you when your target price is reached.
          </p>
        </div>
      </div>

      {priceAlerts.length === 0 ? (
        <div className={styles.emptyContainer}>
          <Bell size={48} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>No active price alerts</h2>
          <p className={styles.emptySubtitle}>
            When researching any product, you can set a target price or percentage drop. We will notify you as soon as verified retailer prices drop.
          </p>
          <Link href="/" className={styles.browseBtn}>
            Discover Products
          </Link>
        </div>
      ) : (
        <div className={styles.alertsList}>
          {priceAlerts.map((alert) => (
            <div key={alert.id} className={styles.alertCard}>
              <div className={styles.alertIconCol}>
                <BellRing size={20} className={styles.bellIcon} />
              </div>
              <div className={styles.alertDetails}>
                <h3 className={styles.prodId}>Product ID: {alert.productId}</h3>
                <span className={styles.alertType}>
                  Alert Type: {(alert.type || (alert as any).alertType || 'target_price').replace('_', ' ')}
                </span>
              </div>
              <div className={styles.targetCol}>
                <span className={styles.targetLabel}>Target Price</span>
                <span className={styles.targetVal}>
                  {alert.targetPrice ? formatPrice(alert.targetPrice, currency) : 'Any Drop'}
                </span>
              </div>
              <div className={styles.statusCol}>
                <span className={styles.statusBadge}>Monitoring Live</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
