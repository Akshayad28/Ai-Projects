'use client';

import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import styles from './ExclusionTabs.module.scss';

export interface TabItem {
  id: string;
  label: string;
  href?: string;
  badge?: number;
}

interface ExclusionTabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const ExclusionTabs: React.FC<ExclusionTabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}) => {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let nextIndex = index;
    if (e.key === 'ArrowRight') {
      nextIndex = (index + 1) % tabs.length;
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (index - 1 + tabs.length) % tabs.length;
    } else if (e.key === 'Home') {
      nextIndex = 0;
    } else if (e.key === 'End') {
      nextIndex = tabs.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    tabRefs.current[nextIndex]?.focus();
    onChange(tabs[nextIndex].id);
  };

  return (
    <div
      role="tablist"
      aria-label="Navigation Tabs"
      className={`${styles.container} ${className}`}
    >
      {tabs.map((tab, idx) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            ref={(el) => { tabRefs.current[idx] = el; }}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, idx)}
            className={`${styles.tab} ${isActive ? styles.active : ''}`}
          >
            {isActive && (
              <motion.div
                layoutId="exclusionIndicator"
                className={styles.indicator}
                transition={{ type: 'spring', stiffness: 450, damping: 35 }}
              />
            )}
            <span className={styles.label}>{tab.label}</span>
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className={styles.badge}>{tab.badge}</span>
            )}
          </button>
        );
      })}
    </div>
  );
};
