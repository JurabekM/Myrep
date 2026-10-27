import { create } from "zustand";

import type { RepaymentResultDto } from "../bindings";
import type { EntryMode } from "../features/kasbkor/KkEntryDialog";
import type { MfEntryMode } from "../features/musofir/MfEntryDialog";

export type Screen = "home" | "vault" | "expenses" | "audit" | "inventory" | "debts" | "ceremonies" | "partnerships" | "ideas" | "agreements" | "receipt" | "kkEquipment" | "kkLabor" | "kkQuote" | "kkClose" | "kkCash" | "kkCredit" | "kkStock" | "kkStaff" | "kkSuppliers" | "kkGate" | "kkZakat" | "kkMeasure" | "kkLearning" | "kkSellerCredit" | "kkShift" | "twoShores" | "learning" | "sync" | "settings";

export type OfferMode = "OFFER" | "COURSE";

type UiState = {
  screen: Screen;
  spaceId: string | null;
  incomeOpen: boolean;
  /** Kasb-kor yozuvi oynasi (Ctrl+N — tushum). */
  kkEntry: EntryMode | null;
  /** Musofir yozuvi oynasi (Ctrl+N — maosh). */
  mfEntry: MfEntryMode | null;
  /** «Taklifni tekshirish» oynasi — ilovaning istalgan joyidan (uy/SPEC 2E.5). */
  offerOpen: boolean;
  /** Oyna qaysi turda ochiladi: sarmoya taklifi yoki kurs/ustoz (uy/SPEC 2G.4). */
  offerMode: OfferMode;
  /** Qarz yopilganda nishonlash oynasi (uy/SPEC 2D.9). */
  celebration: RepaymentResultDto | null;
  /** Eslatma yoki kelishuvlar markazidan ochiladigan sheriklik (va uning bo'limi). */
  partnershipFocus: { id: string; tab: "contract" | "ledger" | "governance" } | null;
  setScreen: (screen: Screen) => void;
  setSpace: (spaceId: string) => void;
  openIncome: () => void;
  closeIncome: () => void;
  openKkEntry: (mode: EntryMode) => void;
  closeKkEntry: () => void;
  openMfEntry: (mode: MfEntryMode) => void;
  closeMfEntry: () => void;
  openOffer: () => void;
  /** «Taklifni tekshirish» — darhol kurs turi bilan (bilim rejasidan). */
  openCourseCheck: () => void;
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
  kkEntry: null,
  mfEntry: null,
  offerOpen: false,
  offerMode: "OFFER",
  celebration: null,
  partnershipFocus: null,
  setScreen: (screen) => set({ screen }),
  setSpace: (spaceId) => set({ spaceId }),
  openIncome: () => set({ incomeOpen: true }),
  closeIncome: () => set({ incomeOpen: false }),
  openKkEntry: (mode) => set({ kkEntry: mode }),
  closeKkEntry: () => set({ kkEntry: null }),
  openMfEntry: (mode) => set({ mfEntry: mode }),
  closeMfEntry: () => set({ mfEntry: null }),
  openOffer: () => set({ offerOpen: true, offerMode: "OFFER" }),
  openCourseCheck: () => set({ offerOpen: true, offerMode: "COURSE" }),
  closeOffer: () => set({ offerOpen: false }),
  afterRepayment: (r) => set(r.closed ? { celebration: r } : {}),
  closeCelebration: () => set({ celebration: null }),
  openPartnership: (id, tab) => set({ screen: "partnerships", partnershipFocus: { id, tab } }),
  clearPartnershipFocus: () => set({ partnershipFocus: null }),
}));
