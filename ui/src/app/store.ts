import { create } from "zustand";
import type { PageId } from "./navigation";

/** Onboarding holati kaliti (UI afzalligi, moliyaviy ma'lumot emas). */
const ONBOARDING_KEY = "baraka.onboarding";

function readOnboardingDone(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_KEY) === "done";
  } catch {
    return false;
  }
}

interface UiState {
  /** Hozir ochiq sahifa. Bu faqat UI holati — moliyaviy ma'lumot emas (DESKTOP_PROMPT.md 2-bo'lim: Zustand). */
  page: PageId;
  setPage: (page: PageId) => void;
  /** Tez daromad kiritish oynasi ochiqmi (Ctrl+N). */
  quickEntryOpen: boolean;
  setQuickEntryOpen: (open: boolean) => void;
  /** Birinchi ishga tushirish qadamlari o'tilganmi (D15). */
  onboardingDone: boolean;
  setOnboardingDone: () => void;
}

export const useUiStore = create<UiState>()((set) => ({
  page: "home",
  setPage: (page) => {
    set({ page });
  },
  quickEntryOpen: false,
  setQuickEntryOpen: (open) => {
    set({ quickEntryOpen: open });
  },
  onboardingDone: readOnboardingDone(),
  setOnboardingDone: () => {
    try {
      localStorage.setItem(ONBOARDING_KEY, "done");
    } catch {
      // Brauzer xotirasi yopiq bo'lsa ham dialog yopiladi; keyingi safar yana ko'rsatiladi.
    }
    set({ onboardingDone: true });
  },
}));
