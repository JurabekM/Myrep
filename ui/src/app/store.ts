import { create } from "zustand";
import type { PageId } from "./navigation";

interface UiState {
  /** Hozir ochiq sahifa. Bu faqat UI holati — moliyaviy ma'lumot emas (DESKTOP_PROMPT.md 2-bo'lim: Zustand). */
  page: PageId;
  setPage: (page: PageId) => void;
}

export const useUiStore = create<UiState>()((set) => ({
  page: "home",
  setPage: (page) => {
    set({ page });
  },
}));
