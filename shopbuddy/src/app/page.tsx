'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { 
  Laptop, 
  Smartphone, 
  Tv, 
  Footprints, 
  Armchair, 
  UtensilsCrossed, 
  Sparkles, 
  Wrench, 
  Briefcase
} from 'lucide-react';
import { SearchBar } from '@/components/search/SearchBar';
import { HeroMascots } from '@/components/hero/HeroMascots';
import { getCategories, CategoryDTO } from '@/lib/api';
import styles from './page.module.scss';

const FEATURED_CATEGORIES = [
  { id: 'laptops', name: 'Laptops', query: 'best laptop under ₹1 lakh for programming', icon: Laptop },
  { id: 'running-shoes', name: 'Running Shoes', query: 'running shoes under ₹10,000', icon: Footprints },
  { id: 'mobile-phones', name: 'Phones', query: 'Samsung phone under ₹60,000', icon: Smartphone },
  { id: 'air-fryers', name: 'Air Fryers', query: 'best air fryer for a family of four', icon: UtensilsCrossed },
  { id: 'office-chairs', name: 'Office Chairs', query: 'best office chair under ₹25,000', icon: Armchair },
  { id: 'monitors', name: 'Monitors', query: 'gaming monitor under ₹40,000', icon: Tv },
  { id: 'power-tools', name: 'Power Tools', query: 'best drill machine for home DIY', icon: Wrench },
  { id: 'luggage', name: 'Luggage', query: 'best suitcase for international travel', icon: Briefcase },
  { id: 'skincare', name: 'Skincare', query: 'best skincare products for oily skin', icon: Sparkles },
];

export default function HomePage() {
  const router = useRouter();
  const [categories, setCategories] = useState<CategoryDTO[]>([]);
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  useEffect(() => {
    getCategories().then((data) => {
      if (data && data.length > 0) {
        setCategories(data);
      }
    });
  }, []);

  const handleSearch = (query: string) => {
    router.push(`/discover?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className={styles.homeWrapper}>
      {/* ── MindMarket Hero Section ── */}
      <section className={styles.heroSection} aria-label="Hero Search Section">
        {/* Mascot Layer (5 transparent WebP 3D bots + podiums + atmosphere glow) */}
        <HeroMascots isSearchFocused={isSearchFocused} />

        {/* Center Text Column (z-index 10, max-width ~760px, never overlaps mascots) */}
        <div className={styles.heroContainer}>
          {/* Mobile Mascot: shown only on <768px above the eyebrow */}
          <div className={styles.mobileBotWrap}>
            <Image
              src="/mascots/bot-phone-airpods-sm.webp"
              alt=""
              width={408}
              height={450}
              priority
              className={styles.mobileBotImage}
            />
          </div>

          {/* Eyebrow Pill */}
          <div className={styles.eyebrowPill}>
            <span className={styles.eyebrowDot} />
            <span className={styles.eyebrowText}>MINDMARKET SHOPPING AGENT</span>
          </div>

          {/* Main Display H1 */}
          <h1 className={styles.displayHeadline}>
            Search smarter.<br />
            Buy with confidence.
          </h1>

          {/* Subtext */}
          <p className={styles.subheadline}>
            Don't just find the cheapest product. Find the product you are least likely to regret buying.
          </p>

          {/* Search Bar + 2-Row "Try asking" Chips */}
          <div className={styles.searchContainer}>
            <SearchBar
              onSearch={handleSearch}
              onFocusChange={setIsSearchFocused}
              size="large"
            />
          </div>
        </div>
      </section>

      {/* ── Feature Cards Section ("No More Chaos") ── */}
      <section className={styles.editorialSection}>
        <div className={styles.editorialGrid}>
          {/* Card 1: Cross-matching */}
          <div className={styles.contentCard}>
            <div className={styles.cardTag}>No More Chaos</div>
            <h2 className={styles.cardHeading}>All retailer offers. One canonical product.</h2>
            <p className={styles.cardBody}>
              Instead of 40 cluttered tabs comparing Amazon, Flipkart, Croma, and Reliance, ShopBuddy links verified seller offers directly to a single canonical specification.
            </p>
            <div className={styles.cardFooterStats}>
              <div className={styles.statPill}>
                <span className={styles.statVal}>100%</span>
                <span className={styles.statLbl}>Cross-matched</span>
              </div>
              <div className={styles.statPill}>
                <span className={styles.statVal}>0</span>
                <span className={styles.statLbl}>Duplicate entries</span>
              </div>
            </div>
          </div>

          {/* Card 2: Price History & Intelligence */}
          <div className={styles.contentCard}>
            <div className={styles.coralTag}>Price Intelligence</div>
            <h2 className={styles.cardHeading}>Verified price history. Real buy signals.</h2>
            <p className={styles.cardBody}>
              Algorithms check real historical prices before telling you if an offer is actually a deal, or just an inflated discount gimmick.
            </p>
            <div className={styles.serviceActionArea}>
              <button 
                type="button" 
                onClick={() => handleSearch('best laptop under ₹1 lakh for programming')}
                className={styles.coralPillButton}
              >
                <span>Launch Live Research</span>
                <span className={styles.whiteActionDot} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Category Domain Grid ── */}
      <section className={styles.categorySection}>
        <div className={styles.sectionHeader}>
          <div className={styles.smallBadge}>Explore Domains</div>
          <h2 className={styles.sectionTitle}>Deep research across categories</h2>
          <p className={styles.sectionSubtitle}>
            ShopBuddy dynamically understands attributes and specifications across diverse product domains.
          </p>
        </div>

        <div className={styles.categoryGrid}>
          {FEATURED_CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => handleSearch(cat.query)}
                className={styles.categoryCard}
              >
                <div className={styles.categoryIconWrap}>
                  <Icon size={24} />
                </div>
                <div className={styles.categoryInfo}>
                  <span className={styles.categoryName}>{cat.name}</span>
                  <span className={styles.categoryQuery}>"{cat.query}"</span>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
