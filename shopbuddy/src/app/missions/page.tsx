'use client';

import React from 'react';
import Link from 'next/link';
import { Target, CheckCircle2, ArrowRight } from 'lucide-react';
import { useStore } from '@/store';
import { formatPrice } from '@/lib/utils';
import styles from './missions.module.scss';

export default function MissionsPage() {
  const { shoppingMissions, currency } = useStore();

  return (
    <div className={styles.missionsContainer}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.pageTitle}>Shopping Missions &amp; Budgets</h1>
          <p className={styles.pageSubtitle}>
            Group related products into holistic shopping goals with a target budget envelope.
          </p>
        </div>
      </div>

      {shoppingMissions.length === 0 ? (
        <div className={styles.emptyContainer}>
          <Target size={48} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>No Active Shopping Missions</h2>
          <p className={styles.emptySubtitle}>
            Shopping missions allow you to set a holistic budget envelope and coordinate multi-product setups (e.g. WFH developer desks, gaming rigs, or studio audio gear) from live scraped market products.
          </p>
          <Link href="/" className={styles.browseBtn}>
            Start Product Research
          </Link>
        </div>
      ) : (
        <div className={styles.missionsGrid}>
          {shoppingMissions.map((mission) => {
            const allocated = mission.items.reduce(
              (acc, it) => acc + (it.selectedOffer?.price || it.allocatedBudget || 0),
              0
            );
            const progress = mission.totalBudget > 0 ? Math.min(100, Math.round((allocated / mission.totalBudget) * 100)) : 0;

            return (
              <div key={mission.id} className={styles.missionCard}>
                <div className={styles.cardHeader}>
                  <div className={styles.iconCircle}>
                    <Target size={20} />
                  </div>
                  <div>
                    <h2 className={styles.missionTitle}>{mission.title}</h2>
                    <span className={styles.categoryTag}>
                      {mission.items.map((it) => it.category).join(' · ')}
                    </span>
                  </div>
                </div>

                <div className={styles.budgetRow}>
                  <div>
                    <span className={styles.budgetLabel}>Target Budget</span>
                    <div className={styles.budgetVal}>
                      {formatPrice(mission.totalBudget, mission.currency || currency)}
                    </div>
                  </div>
                  <div>
                    <span className={styles.budgetLabel}>Allocated</span>
                    <div className={styles.allocatedVal}>
                      {formatPrice(allocated, mission.currency || currency)}
                    </div>
                  </div>
                </div>

                <div className={styles.progressBarWrapper}>
                  <div className={styles.progressBar} style={{ width: `${progress}%` }} />
                </div>

                <div className={styles.itemsList}>
                  {mission.items.map((it) => (
                    <div key={it.id} className={styles.missionItem}>
                      <CheckCircle2
                        size={16}
                        className={it.status === 'selected' || it.status === 'purchased' ? styles.checkDone : ''}
                      />
                      <span>
                        {it.selectedProduct?.name || `${it.category} (Pending Selection)`}
                      </span>
                      <span className={styles.itemPrice}>
                        {formatPrice(
                          it.selectedOffer?.price || it.allocatedBudget,
                          mission.currency || currency
                        )}
                      </span>
                    </div>
                  ))}
                </div>

                <Link href="/" className={styles.addStepBtn}>
                  <span>Find Products for Mission</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
