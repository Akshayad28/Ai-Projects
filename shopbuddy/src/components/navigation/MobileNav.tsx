'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Compass, Scale, Heart, Bell, Target } from 'lucide-react';
import { useStore } from '@/store';
import styles from './MobileNav.module.scss';

export const MobileNav: React.FC = () => {
  const pathname = usePathname();
  const { wishlist, comparisonItems } = useStore();

  const navItems = [
    { label: 'Discover', href: '/', icon: Compass },
    { label: 'Compare', href: '/compare', icon: Scale, badge: comparisonItems.length },
    { label: 'Wishlist', href: '/wishlist', icon: Heart, badge: wishlist.length },
    { label: 'Alerts', href: '/alerts', icon: Bell },
    { label: 'Missions', href: '/missions', icon: Target },
  ];

  return (
    <nav className={styles.bottomNav} aria-label="Mobile Navigation">
      <div className={styles.navGrid}>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              <div className={styles.iconWrapper}>
                <Icon size={20} />
                {item.badge !== undefined && item.badge > 0 && (
                  <span className={styles.badge}>{item.badge}</span>
                )}
              </div>
              <span className={styles.label}>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};
