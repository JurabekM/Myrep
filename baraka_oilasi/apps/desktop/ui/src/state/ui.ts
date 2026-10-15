import { create } from "zustand";

export type Screen = "home" | "vault" | "expenses" | "audit" | "inventory" | "debts" | "receipt";

type UiState = {
  screen: Screen;
  spaceId: string | null;
  incomeOpen: boolean;
  setScreen: (screen: Screen) => void;
  setSpace: (spaceId: string) => void;
  openIncome: () => void;
  closeIncome: () => void;
};

/** Faqat UI holati (ma'lumot — TanStack Query'da). */
export const useUi = create<UiState>((set) => ({
  screen: "home",
  spaceId: null,
  incomeOpen: false,
  setScreen: (screen) => set({ screen }),
  setSpace: (spaceId) => set({ spaceId }),
  openIncome: () => set({ incomeOpen: true }),
  closeIncome: () => set({ incomeOpen: false }),
}));
