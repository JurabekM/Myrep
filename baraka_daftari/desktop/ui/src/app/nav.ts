import { create } from 'zustand';

export type Page = 'home' | 'income' | 'vault' | 'budget' | 'obligations';

interface NavState {
  page: Page;
  quickEntryOpen: boolean;
  setPage: (page: Page) => void;
  openQuickEntry: () => void;
  closeQuickEntry: () => void;
}

/** Faqat UI holati (yadrodan keladigan ma'lumotlar TanStack Query'da). */
export const useNav = create<NavState>((set) => ({
  page: 'home',
  quickEntryOpen: false,
  setPage: (page) => {
    set({ page });
  },
  openQuickEntry: () => {
    set({ quickEntryOpen: true });
  },
  closeQuickEntry: () => {
    set({ quickEntryOpen: false });
  },
}));
