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
  | 'debts';

interface NavState {
  page: Page;
  quickEntryOpen: boolean;
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
  chapterId: null,
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
