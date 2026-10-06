'use client';

import React, { useState } from 'react';
import { Sparkles, CheckCircle2, ChevronDown, ChevronUp, Clock, ShieldCheck } from 'lucide-react';
import styles from './AIActivityPanel.module.scss';

interface ActivityStep {
  title: string;
  detail: string;
  completed: boolean;
}

interface AIActivityPanelProps {
  query: string;
  providersUsed?: string[];
  productsFound?: number;
  durationMs?: number;
  isDemo?: boolean;
  isLive?: boolean;
  freshnessLabel?: string;
  liveProvidersConfigured?: number;
}

export const AIActivityPanel: React.FC<AIActivityPanelProps> = ({
  query,
  providersUsed = [],
  productsFound = 0,
  durationMs = 0,
  isDemo: _isDemo,
  isLive = false,
  freshnessLabel,
  liveProvidersConfigured = 0,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const steps: ActivityStep[] = [
    {
      title: 'Parsed search intent & constraints',
      detail: `Extracted category criteria, use-cases, and budget from "${query}"`,
      completed: true,
    },
    {
      title: 'Polled product providers in parallel',
      detail: `Queried ${providersUsed.length > 0 ? providersUsed.join(', ') : 'registered retail providers'}`,
      completed: true,
    },
    {
      title: 'Clustered canonical models & offers',
      detail: `Discovered and deduplicated ${productsFound} products across verified sellers`,
      completed: true,
    },
    {
      title: 'Extracted category specifications',
      detail: 'Normalized technical specs dynamically using category taxonomy',
      completed: true,
    },
    {
      title: 'Computed match scores & trade-offs',
      detail: 'Ranked results based on budget, requirement satisfaction, and reviews',
      completed: true,
    },
  ];

  return (
    <div className={styles.container}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={styles.headerBtn}
        aria-expanded={isOpen}
      >
        <div className={styles.headerContent}>
          <div className={styles.headerTopRow}>
            <div className={styles.headerTitleGroup}>
              <div className={styles.iconPulse}>
                <Sparkles size={16} />
              </div>
              <span className={styles.headerTitle}>
                ShopBuddy Research Intelligence
              </span>
            </div>

            <div className={styles.headerRightMobile}>
              <span className={styles.toggleText}>
                {isOpen ? 'Hide' : 'Details'}
              </span>
              {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </div>

          <div className={styles.metaBadgesRow}>
            {durationMs > 0 && (
              <span className={styles.metaBadge}>
                <Clock size={12} />
                <span>{durationMs}ms</span>
              </span>
            )}
            {isLive ? (
              <span className={styles.liveTag}>
                <ShieldCheck size={12} />
                <span>{freshnessLabel || 'Live Real-Time Data'}</span>
              </span>
            ) : (
              <span className={styles.unconfiguredTag}>
                <span>{liveProvidersConfigured} Live Retailers Connected</span>
              </span>
            )}
          </div>
        </div>

        <div className={styles.headerRightDesktop}>
          <span className={styles.toggleText}>
            {isOpen ? 'Hide Research Steps' : 'See what ShopBuddy researched'}
          </span>
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {isOpen && (
        <div className={styles.panelBody}>
          <ul className={styles.stepsList}>
            {steps.map((s, idx) => (
              <li key={idx} className={styles.stepItem}>
                <div className={styles.stepIcon}>
                  <CheckCircle2 size={16} className={styles.checkIcon} />
                </div>
                <div className={styles.stepContent}>
                  <div className={styles.stepTitle}>{s.title}</div>
                  <div className={styles.stepDetail}>{s.detail}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
