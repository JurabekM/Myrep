import { create } from "zustand";

import type { RepaymentResultDto } from "../bindings";

export type Screen = "home" | "vault" | "expenses" | "audit" | "inventory" | "debts" | "ceremonies" | "partnerships" | "receipt";

type UiState = {
  screen: Screen;
  spaceId: string | null;
  incomeOpen: boolean;
  /** Qarz yopilganda nishonlash oynasi (uy/SPEC 2D.9). */
  celebration: RepaymentResultDto | null;
  setScreen: (screen: Screen) => void;
  setSpace: (spaceId: string) => void;
  openIncome: () => void;
  closeIncome: () => void;
  /** Toʻlov natijasi: qarz yopilgan boʻlsa, nishonlash oynasi ochiladi. */
  afterRepayment: (r: RepaymentResultDto) => void;
  closeCelebration: () => void;
};

/** Faqat UI holati (ma'lumot — TanStack Query'da). */
export const useUi = create<UiState>((set) => ({
  screen: "home",
  spaceId: null,
  incomeOpen: false,
  celebration: null,
  setScreen: (screen) => set({ screen }),
  setSpace: (spaceId) => set({ spaceId }),
  openIncome: () => set({ incomeOpen: true }),
  closeIncome: () => set({ incomeOpen: false }),
  afterRepayment: (r) => set(r.closed ? { celebration: r } : {}),
  closeCelebration: () => set({ celebration: null }),
}));
