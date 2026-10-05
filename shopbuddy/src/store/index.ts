// ============================================
// SHOPBUDDY AI — Global Store (Zustand)
// ============================================

import { create } from 'zustand';
import type {
  CurrencyCode,
  WishlistItem,
  PriceAlert,
  Notification,
  SearchResult,
  SearchIntent,
  AIChatMessage,
  ShoppingMission,
} from '@/types';

interface ShopBuddyStore {
  // Navigation
  activeTab: number;
  setActiveTab: (index: number) => void;

  // Currency
  currency: CurrencyCode;
  setCurrency: (code: CurrencyCode) => void;

  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchIntent: SearchIntent | null;
  setSearchIntent: (intent: SearchIntent | null) => void;
  searchResults: SearchResult[];
  setSearchResults: (results: SearchResult[]) => void;
  isSearching: boolean;
  setIsSearching: (val: boolean) => void;

  // Wishlist
  wishlist: WishlistItem[];
  wishlistItems: WishlistItem[];
  addToWishlist: (item: WishlistItem) => void;
  removeFromWishlist: (productIdOrId: string) => void;
  isInWishlist: (productId: string) => boolean;

  // Alerts
  alerts: PriceAlert[];
  priceAlerts: PriceAlert[];
  addAlert: (alert: PriceAlert) => void;
  removeAlert: (id: string) => void;

  // Shopping Missions
  shoppingMissions: ShoppingMission[];

  // Notifications
  notifications: Notification[];
  markNotificationRead: (id: string) => void;
  unreadCount: () => number;

  // Comparison
  comparisonItems: string[]; // product IDs
  addToComparison: (productId: string) => void;
  removeFromComparison: (productId: string) => void;
  toggleComparison: (productId: string) => void;
  clearComparison: () => void;
  isInComparison: (productId: string) => boolean;

  // AI Chat
  chatMessages: AIChatMessage[];
  addChatMessage: (msg: AIChatMessage) => void;
  isChatOpen: boolean;
  setIsChatOpen: (val: boolean) => void;

  // UI
  isSearchFocused: boolean;
  setIsSearchFocused: (val: boolean) => void;
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (val: boolean) => void;
}

export const useStore = create<ShopBuddyStore>((set, get) => ({
  // Navigation
  activeTab: 0,
  setActiveTab: (index) => set({ activeTab: index }),

  // Currency
  currency: 'INR',
  setCurrency: (code) => set({ currency: code }),

  // Search
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),
  searchIntent: null,
  setSearchIntent: (intent) => set({ searchIntent: intent }),
  searchResults: [],
  setSearchResults: (results) => set({ searchResults: results }),
  isSearching: false,
  setIsSearching: (val) => set({ isSearching: val }),

  // Wishlist
  wishlist: [],
  wishlistItems: [],
  addToWishlist: (item) =>
    set((state) => {
      const next = [...state.wishlist, item];
      return { wishlist: next, wishlistItems: next };
    }),
  removeFromWishlist: (productIdOrId) =>
    set((state) => {
      const next = state.wishlist.filter(
        (it) => it.productId !== productIdOrId && it.id !== productIdOrId
      );
      return { wishlist: next, wishlistItems: next };
    }),
  isInWishlist: (productId) =>
    get().wishlist.some((item) => item.productId === productId),

  // Alerts
  alerts: [],
  priceAlerts: [],
  addAlert: (alert) =>
    set((state) => {
      const next = [...state.alerts, alert];
      return { alerts: next, priceAlerts: next };
    }),
  removeAlert: (id) =>
    set((state) => {
      const next = state.alerts.filter((a) => a.id !== id);
      return { alerts: next, priceAlerts: next };
    }),

  // Missions
  shoppingMissions: [],

  // Notifications
  notifications: [],
  markNotificationRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    })),
  unreadCount: () => get().notifications.filter((n) => !n.read).length,

  // Comparison
  comparisonItems: [],
  addToComparison: (productId) =>
    set((state) => {
      if (state.comparisonItems.length >= 4) return state;
      if (state.comparisonItems.includes(productId)) return state;
      return { comparisonItems: [...state.comparisonItems, productId] };
    }),
  removeFromComparison: (productId) =>
    set((state) => ({
      comparisonItems: state.comparisonItems.filter((id) => id !== productId),
    })),
  toggleComparison: (productId) =>
    set((state) => {
      if (state.comparisonItems.includes(productId)) {
        return { comparisonItems: state.comparisonItems.filter((id) => id !== productId) };
      }
      if (state.comparisonItems.length >= 4) return state;
      return { comparisonItems: [...state.comparisonItems, productId] };
    }),
  clearComparison: () => set({ comparisonItems: [] }),
  isInComparison: (productId) =>
    get().comparisonItems.includes(productId),

  // AI Chat
  chatMessages: [],
  addChatMessage: (msg) =>
    set((state) => ({ chatMessages: [...state.chatMessages, msg] })),
  isChatOpen: false,
  setIsChatOpen: (val) => set({ isChatOpen: val }),

  // UI
  isSearchFocused: false,
  setIsSearchFocused: (val) => set({ isSearchFocused: val }),
  isMobileMenuOpen: false,
  setIsMobileMenuOpen: (val) => set({ isMobileMenuOpen: val }),
}));
