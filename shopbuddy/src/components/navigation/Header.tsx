'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter, usePathname } from 'next/navigation';
import { Globe, Menu, ChevronDown } from 'lucide-react';
import { ExclusionTabs } from './ExclusionTabs';
import { useStore } from '@/store';
import { getSystemHealth } from '@/lib/api';
import type { CurrencyCode } from '@/types';
import styles from './Header.module.scss';

const NAV_TABS = [
  { id: 'discover', label: 'Discover', href: '/' },
  { id: 'compare', label: 'Compare', href: '/compare' },
  { id: 'wishlist', label: 'Wishlist', href: '/wishlist' },
  { id: 'alerts', label: 'Price Alerts', href: '/alerts' },
  { id: 'missions', label: 'Missions', href: '/missions' },
];

export const Header: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { wishlist, comparisonItems, currency, setCurrency } = useStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    getSystemHealth().then((res) => {
      if (res?.demo_mode) {
        setIsDemoMode(true);
      }
    });
  }, []);

  const activeTab = NAV_TABS.find(t => t.href === pathname)?.id || 'discover';

  const handleTabChange = (tabId: string) => {
    const tab = NAV_TABS.find(t => t.id === tabId);
    if (tab?.href) {
      router.push(tab.href);
    }
  };

  const tabsWithBadges = NAV_TABS.map(t => {
    if (t.id === 'wishlist') return { ...t, badge: wishlist.length };
    if (t.id === 'compare') return { ...t, badge: comparisonItems.length };
    return t;
  });

  return (
    <header className={styles.headerWrapper}>
      <nav className={styles.navPill} aria-label="Main Navigation">
        {/* Brand Logo Container */}
        <Link href="/" className={styles.brand}>
          <div className={styles.logoBox}>
            <Image
              src="/logo.png"
              alt="ShopBuddy Logo"
              width={36}
              height={36}
              className={styles.logoImg}
              priority
            />
          </div>
          <span className={styles.brandName}>ShopBuddy</span>
        </Link>

        {/* Center Nav Links (Inter 15px 500) */}
        <div className={styles.centerNav}>
          <ExclusionTabs
            tabs={tabsWithBadges}
            activeTab={activeTab}
            onChange={handleTabChange}
          />
        </div>

        {/* Right Section */}
        <div className={styles.rightActions}>
          {/* Currency selector */}
          <div className={styles.currencyWrapper}>
            <label htmlFor="currency-select" className="sr-only">Currency</label>
            <Globe size={14} className={styles.globeIcon} />
            <select
              id="currency-select"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as CurrencyCode)}
              className={styles.currencySelect}
              aria-label="Currency selection"
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="AED">AED (د.إ)</option>
            </select>
            <ChevronDown size={12} className={styles.chevronIcon} />
          </div>

          {/* Menu Toggle Button: Circular #8ed462 green button with dark icon */}
          <button 
            type="button" 
            className={styles.menuToggleBtn}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            title="Navigation Menu"
          >
            <Menu size={18} color="#2c2e2a" />
          </button>

          {/* Primary CTA Button: Light pill with embedded action dot */}
          <Link href="/discover" className={styles.primaryCtaBtn}>
            <span>Research</span>
            <span className={styles.actionDot} />
          </Link>
        </div>
      </nav>

      {/* Slim Sandstone/Cream DEMO_MODE banner below nav (Step 8) */}
      {isDemoMode && (
        <aside className={styles.demoModeBanner} aria-label="Demo mode warning">
          <span className={styles.demoDot} />
          <span>DEMO MODE ACTIVE: Catalog results are for local testing only</span>
        </aside>
      )}

      {/* Dropdown Menu on mobile/toggle */}
      {menuOpen && (
        <div className={styles.menuDropdown}>
          {NAV_TABS.map(tab => (
            <Link 
              key={tab.id} 
              href={tab.href} 
              className={styles.menuItem}
              onClick={() => setMenuOpen(false)}
            >
              {tab.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
};
