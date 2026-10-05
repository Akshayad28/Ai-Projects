'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Sparkles, X } from 'lucide-react';
import styles from './SearchBar.module.scss';

const ROTATING_PLACEHOLDERS = [
  'best drill machine for home DIY',
  'best laptop under ₹1 lakh for programming',
  'running shoes under ₹10,000',
  'best office chair under ₹25,000',
  'best air fryer for a family of four',
  'Samsung phone under ₹60,000',
  'gaming monitor under ₹40,000',
  'best suitcase for international travel',
  'best skincare products for oily skin',
  'best washing machine under ₹40,000',
];

const PROMPT_CHIPS_ROW_1 = [
  'best laptop under ₹1 lakh for programming',
  'running shoes under ₹10,000',
];

const PROMPT_CHIPS_ROW_2 = [
  'best office chair under ₹25,000',
  'best air fryer for a family of four',
];

interface SearchBarProps {
  initialQuery?: string;
  onSearch?: (query: string) => void;
  size?: 'large' | 'compact';
  autoFocus?: boolean;
  onFocusChange?: (focused: boolean) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  initialQuery = '',
  onSearch,
  size = 'large',
  autoFocus = false,
  onFocusChange,
}) => {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [prevInitialQuery, setPrevInitialQuery] = useState(initialQuery);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (initialQuery !== prevInitialQuery) {
    setPrevInitialQuery(initialQuery);
    setQuery(initialQuery);
  }

  useEffect(() => {
    if (isFocused || query) return;
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % ROTATING_PLACEHOLDERS.length);
    }, 4200);
    return () => clearInterval(interval);
  }, [isFocused, query]);

  const handleFocus = () => {
    setIsFocused(true);
    if (onFocusChange) onFocusChange(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
    if (onFocusChange) onFocusChange(false);
  };

  const handleClear = () => {
    setQuery('');
    if (inputRef.current) {
      inputRef.current.focus();
    }
    if (onSearch) {
      onSearch('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    const finalQuery = trimmed || (!isFocused ? ROTATING_PLACEHOLDERS[placeholderIndex] : '');

    if (onSearch) {
      onSearch(finalQuery);
    } else {
      if (finalQuery) {
        router.push(`/discover?q=${encodeURIComponent(finalQuery)}`);
      } else {
        router.push('/discover');
      }
    }
  };

  const handleChipClick = (suggestion: string) => {
    setQuery(suggestion);
    if (onSearch) {
      onSearch(suggestion);
    } else {
      router.push(`/discover?q=${encodeURIComponent(suggestion)}`);
    }
  };

  return (
    <div className={`${styles.wrapper} ${size === 'compact' ? styles.compact : styles.large}`}>
      <form onSubmit={handleSubmit} className={`${styles.searchBox} ${isFocused ? styles.focused : ''}`}>
        <div className={styles.iconArea}>
          <Search size={size === 'compact' ? 18 : 22} className={styles.searchIcon} />
        </div>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={ROTATING_PLACEHOLDERS[placeholderIndex]}
          autoFocus={autoFocus}
          className={styles.input}
          aria-label="Search shopping query"
        />

        {query && (
          <button
            type="button"
            onClick={handleClear}
            className={styles.clearBtn}
            aria-label="Clear search input"
            title="Clear text"
          >
            <X size={16} />
          </button>
        )}

        <button type="submit" className={styles.actionBtn} aria-label="Research products">
          <Sparkles size={16} />
          <span>Research</span>
        </button>
      </form>

      {size === 'large' && (
        <div className={styles.suggestionsContainer}>
          {/* Row 1: Label + First 2 chips */}
          <div className={styles.chipRow}>
            <span className={styles.suggestionLabel}>TRY ASKING:</span>
            {PROMPT_CHIPS_ROW_1.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => handleChipClick(item)}
                className={styles.chip}
              >
                {item}
              </button>
            ))}
          </div>

          {/* Row 2: Remaining 2 chips */}
          <div className={styles.chipRow}>
            {PROMPT_CHIPS_ROW_2.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => handleChipClick(item)}
                className={styles.chip}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
