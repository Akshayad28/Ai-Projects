'use client';

import React from 'react';
import Image from 'next/image';
import { Podium } from './Podium';
import styles from './HeroMascots.module.scss';

interface HeroMascotsProps {
  isSearchFocused?: boolean;
}

export const HeroMascots: React.FC<HeroMascotsProps> = ({ isSearchFocused = false }) => {
  return (
    <div
      className={`${styles.mascotLayer} ${isSearchFocused ? styles.searchFocused : ''}`}
      aria-hidden="true"
    >
      {/* ── LEFT CLUSTER BOX ── */}
      <div className={styles.leftClusterBox}>
        {/* Podium Left: left 0%, top 46%, width 82%, height 28%, z-index 1 */}
        <div className={styles.podiumLeft}>
          <Podium />
        </div>

        {/* Contact shadow on podium top face under phone bot */}
        <div className={styles.shadowPhone} />

        {/* bot-phone-airpods: left 15%, top 0%, width 80%, z-index 2 */}
        <div className={styles.botPhone}>
          <div className={styles.desktopBot}>
            <Image
              src="/mascots/bot-phone-airpods.webp"
              alt=""
              width={755}
              height={816}
              priority
              sizes="(max-width: 1024px) 15vw, (max-width: 1280px) 19vw, 24vw"
              className={styles.botImageFloat1}
            />
          </div>
          <div className={styles.tabletBot}>
            <Image
              src="/mascots/bot-phone-airpods-sm.webp"
              alt=""
              width={378}
              height={408}
              priority
              sizes="15vw"
              className={styles.botImageFloat1}
            />
          </div>
        </div>

        {/* Contact shadow on ground under beanbag */}
        <div className={styles.shadowBeanbag} />

        {/* bot-laptop-beanbag: left 3.5%, top 48.5%, width 96%, z-index 3 */}
        <div className={styles.botBeanbag}>
          <Image
            src="/mascots/bot-laptop-beanbag.webp"
            alt=""
            width={882}
            height={871}
            priority
            sizes="(max-width: 1280px) 24vw, 24vw"
            className={styles.botImageFloat2}
          />
        </div>
      </div>

      {/* ── RIGHT CLUSTER BOX ── */}
      <div className={styles.rightClusterBox}>
        {/* Contact shadow under floating shopping bot */}
        <div className={styles.shadowShopping} />

        {/* bot-shopping: left 0%, top 0%, width 94%, z-index 1 */}
        <div className={styles.botShopping}>
          <div className={styles.desktopBot}>
            <Image
              src="/mascots/bot-shopping.webp"
              alt=""
              width={1024}
              height={749}
              priority
              sizes="(max-width: 1024px) 15vw, (max-width: 1280px) 24vw, 29vw"
              className={styles.botImageFloat3}
            />
          </div>
          <div className={styles.tabletBot}>
            <Image
              src="/mascots/bot-shopping-sm.webp"
              alt=""
              width={512}
              height={374}
              priority
              sizes="15vw"
              className={styles.botImageFloat3}
            />
          </div>
        </div>

        {/* Podium Right: left 1%, top 82%, width 63%, height 15%, z-index 1 */}
        <div className={styles.podiumRight}>
          <Podium />
        </div>

        {/* Contact shadow on podium under chef bot & air fryer */}
        <div className={styles.shadowChef} />

        {/* bot-chef-airfryer: left 6.5%, top 41.5%, width 41%, z-index 2 */}
        <div className={styles.botChef}>
          <Image
            src="/mascots/bot-chef-airfryer.webp"
            alt=""
            width={706}
            height={888}
            priority
            sizes="(max-width: 1280px) 12vw, 14vw"
            className={styles.botImageFloat4}
          />
        </div>

        {/* Contact shadow on ground under drill bot */}
        <div className={styles.shadowDrill} />

        {/* bot-builder-drill: left 50.5%, top 52%, width 49.5%, z-index 3 */}
        <div className={styles.botDrill}>
          <Image
            src="/mascots/bot-builder-drill.webp"
            alt=""
            width={742}
            height={900}
            priority
            sizes="(max-width: 1280px) 14vw, 15vw"
            className={styles.botImageFloat5}
          />
        </div>
      </div>
    </div>
  );
};
