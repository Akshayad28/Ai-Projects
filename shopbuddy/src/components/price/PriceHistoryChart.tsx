'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { formatPrice } from '@/lib/utils';
import styles from './PriceHistoryChart.module.scss';

export interface PricePoint {
  observed_at: string;
  amount: number;
  currency?: string;
  retailer_name?: string;
}

interface PriceHistoryChartProps {
  observations: PricePoint[];
  currency?: string;
  height?: number;
}

export const PriceHistoryChart: React.FC<PriceHistoryChartProps> = ({
  observations = [],
  currency = 'INR',
  height = 200,
}) => {
  const [activePoint, setActivePoint] = useState<PricePoint | null>(null);

  if (!observations || observations.length < 2) {
    return (
      <div className={styles.insufficientState}>
        <span className={styles.emptyIcon}>📊</span>
        <div className={styles.emptyTitle}>Not enough price history</div>
        <div className={styles.emptyDetail}>
          ShopBuddy records verified price observations as they occur. Synthetic history is never generated.
        </div>
      </div>
    );
  }

  // Sort chronological
  const sorted = [...observations].sort(
    (a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime()
  );

  const prices = sorted.map((p) => p.amount);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;

  const width = 600;
  const paddingX = 40;
  const paddingY = 30;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  const points = sorted.map((p, idx) => {
    const x = paddingX + (idx / (sorted.length - 1)) * chartWidth;
    const y = paddingY + chartHeight - ((p.amount - minPrice) / priceRange) * chartHeight;
    return { x, y, point: p };
  });

  const pathD = points.reduce((acc, curr, idx) => {
    return idx === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  return (
    <div className={styles.chartWrapper}>
      <div className={styles.chartHeader}>
        <div className={styles.statBox}>
          <span className={styles.statLabel}>Historical Low</span>
          <span className={styles.statVal}>{formatPrice(minPrice, currency as any)}</span>
        </div>
        <div className={styles.statBox}>
          <span className={styles.statLabel}>Recent High</span>
          <span className={styles.statVal}>{formatPrice(maxPrice, currency as any)}</span>
        </div>
      </div>

      <div className={styles.svgContainer} style={{ height }}>
        <svg viewBox={`0 0 ${width} ${height}`} className={styles.svg} preserveAspectRatio="none">
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2F7D5A" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#2F7D5A" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area fill */}
          <path d={areaD} fill="url(#priceGradient)" />

          {/* Animated line */}
          <motion.path
            d={pathD}
            fill="none"
            stroke="#2F7D5A"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: 'easeInOut' }}
          />

          {/* Data Points */}
          {points.map((p, idx) => (
            <circle
              key={idx}
              cx={p.x}
              cy={p.y}
              r="4.5"
              className={styles.pointCircle}
              onMouseEnter={() => setActivePoint(p.point)}
              onMouseLeave={() => setActivePoint(null)}
            />
          ))}
        </svg>

        {activePoint && (
          <div className={styles.tooltip}>
            <div className={styles.tooltipPrice}>
              {formatPrice(activePoint.amount, currency as any)}
            </div>
            <div className={styles.tooltipDate}>
              {new Date(activePoint.observed_at).toLocaleDateString()}
              {activePoint.retailer_name ? ` · ${activePoint.retailer_name}` : ''}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
