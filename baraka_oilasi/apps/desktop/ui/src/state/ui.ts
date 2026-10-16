import { create } from "zustand";

import type { RepaymentResultDto } from "../bindings";

export type Screen = "home" | "vault" | "expenses" | "audit" | "inventory" | "debts" | "ceremonies" | "partnerships" | "ideas" | "agreements" | "receipt" | "sync" | "settings";

type UiState = {
  screen: Screen;
  spaceId: string | null;
  incomeOpen: boolean;
  /** «Taklifni tekshirish» oynasi — ilovaning istalgan joyidan (uy/SPEC 2E.5). */
  offerOpen: boolean;
  /** Qarz yopilganda nishonlash oynasi (uy/SPEC 2D.9). */
  celebration: RepaymentResultDto | null;
  /** Eslatma yoki kelishuvlar markazidan ochiladigan sheriklik (va uning bo'limi). */
  partnershipFocus: { id: string; tab: "contract" | "ledger" | "governance" } | null;
  setScreen: (screen: Screen) => void;
  setSpace: (spaceId: string) => void;
  openIncome: () => void;
  closeIncome: () => void;
  openOffer: () => void;
  closeOffer: () => void;
  /** Toʻlov natijasi: qarz yopilgan boʻlsa, nishonlash oynasi ochiladi. */
  afterRepayment: (r: RepaymentResultDto) => void;
  closeCelebration: () => void;
  openPartnership: (id: string, tab: "contract" | "ledger" | "governance") => void;
  clearPartnershipFocus: () => void;
};

/** Faqat UI holati (ma'lumot — TanStack Query'da). */
export const useUi = create<UiState>((set) => ({
  screen: "home",
  spaceId: null,
  incomeOpen: false,
  offerOpen: false,
  celebration: null,
  partnershipFocus: null,
  setScreen: (screen) => set({ screen }),
  setSpace: (spaceId) => set({ spaceId }),
  openIncome: () => set({ incomeOpen: true }),
  closeIncome: () => set({ incomeOpen: false }),
  openOffer: () => set({ offerOpen: true }),
  closeOffer: () => set({ offerOpen: false }),
  afterRepayment: (r) => set(r.closed ? { celebration: r } : {}),
  closeCelebration: () => set({ celebration: null }),
  openPartnership: (id, tab) => set({ screen: "partnerships", partnershipFocus: { id, tab } }),
  clearPartnershipFocus: () => set({ partnershipFocus: null }),
}));
