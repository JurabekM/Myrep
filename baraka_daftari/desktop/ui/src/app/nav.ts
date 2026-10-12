import { create } from 'zustand';

export type Page =
  | 'home'
  | 'income'
  | 'vault'
  | 'budget'
  | 'obligations'
  | 'study'
  | 'expenses'
  | 'family'
  | 'council'
  | 'subscriptions'
  | 'envelopes'
  | 'rescue'
  | 'prices'
  | 'debts'
  | 'ceremonies'
  | 'partnerships'
  | 'crafts'
  | 'exchange';

/** Yon panel va buyruqlar palitrasi uchun sahifalar (tartib shu yerda). */
export const PAGE_LINKS: { id: Page; labelKey: string }[] = [
  { id: 'home', labelKey: 'nav.home' },
  { id: 'debts', labelKey: 'nav.debts' },
  { id: 'ceremonies', labelKey: 'nav.ceremonies' },
  { id: 'partnerships', labelKey: 'nav.partnerships' },
  { id: 'crafts', labelKey: 'nav.crafts' },
  { id: 'exchange', labelKey: 'nav.exchange' },
  { id: 'income', labelKey: 'nav.income' },
  { id: 'vault', labelKey: 'nav.vault' },
  { id: 'budget', labelKey: 'nav.budget' },
  { id: 'expenses', labelKey: 'nav.expenses' },
  { id: 'obligations', labelKey: 'nav.obligations' },
  { id: 'envelopes', labelKey: 'nav.envelopes' },
  { id: 'subscriptions', labelKey: 'nav.subscriptions' },
  { id: 'rescue', labelKey: 'nav.rescue' },
  { id: 'prices', labelKey: 'nav.prices' },
  { id: 'family', labelKey: 'nav.family' },
  { id: 'study', labelKey: 'nav.study' },
];

interface NavState {
  page: Page;
  quickEntryOpen: boolean;
  /** Buyruqlar palitrasi (Ctrl+K). */
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
  /** Boblar sahifasida ochiq bob (bosh sahifadan havola uchun). */
  chapterId: string | null;
  setPage: (page: Page) => void;
  openChapter: (id: string) => void;
  openQuickEntry: () => void;
  closeQuickEntry: () => void;
}

/** Faqat UI holati (yadrodan keladigan ma'lumotlar TanStack Query'da). */
export const useNav = create<NavState>((set) => ({
  page: 'home',
  quickEntryOpen: false,
  paletteOpen: false,
  chapterId: null,
  openPalette: () => {
    set({ paletteOpen: true });
  },
  closePalette: () => {
    set({ paletteOpen: false });
  },
  setPage: (page) => {
    set({ page });
  },
  openChapter: (id) => {
    set({ page: 'study', chapterId: id });
  },
  openQuickEntry: () => {
    set({ quickEntryOpen: true });
  },
  closeQuickEntry: () => {
    set({ quickEntryOpen: false });
  },
}));
