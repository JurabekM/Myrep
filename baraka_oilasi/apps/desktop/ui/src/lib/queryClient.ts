import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 30_000 },
    mutations: { retry: false },
  },
});

/** So'rov kalitlari: yadrodagi `Topic` larga mos. */
export const keys = {
  session: ["session"] as const,
  household: ["household"] as const,
  categories: (spaceId: string) => ["categories", spaceId] as const,
  vault: (spaceId: string) => ["vault", spaceId] as const,
  debts: (spaceId: string) => ["debts", spaceId] as const,
  budget: (spaceId: string) => ["budget", spaceId] as const,
  planner: (spaceId: string, extra: string | null) => ["planner", spaceId, extra] as const,
  items: (spaceId: string) => ["items", spaceId] as const,
  ceremonies: (spaceId: string) => ["ceremonies", spaceId] as const,
  ceremony: (spaceId: string, id: string) => ["ceremony", spaceId, id] as const,
  partnerships: (spaceId: string) => ["partnerships", spaceId] as const,
  partnership: (spaceId: string, id: string) => ["partnership", spaceId, id] as const,
  ledger: (spaceId: string, id: string) => ["ledger", spaceId, id] as const,
  ideas: (spaceId: string) => ["ideas", spaceId] as const,
  skills: (spaceId: string) => ["skills", spaceId] as const,
  governance: (spaceId: string, id: string) => ["governance", spaceId, id] as const,
  reminders: (spaceId: string) => ["reminders", spaceId] as const,
  agreements: (spaceId: string) => ["agreements", spaceId] as const,
  family: (spaceId: string) => ["family", spaceId] as const,
  devices: ["devices"] as const,
  deviceRole: ["deviceRole"] as const,
  settings: ["settings"] as const,
  nudges: (spaceId: string) => ["nudges", spaceId] as const,
  kk: (spaceId: string) => ["kk", spaceId] as const,
  mf: (spaceId: string) => ["mf", spaceId] as const,
  mfTerms: (spaceId: string) => ["mfTerms", spaceId] as const,
  mfTwoShores: (spaceId: string) => ["mfTwoShores", spaceId] as const,
  mfTravelDebt: (spaceId: string) => ["mfTravelDebt", spaceId] as const,
  mfDecisions: (spaceId: string) => ["mfDecisions", spaceId] as const,
  mfQuestions: (kind: string) => ["mfQuestions", kind] as const,
  kkEquipment: (spaceId: string) => ["kkEquipment", spaceId] as const,
  kkLabor: (spaceId: string) => ["kkLabor", spaceId] as const,
  kkClose: (spaceId: string) => ["kkClose", spaceId] as const,
  kkCloseRules: (spaceId: string) => ["kkCloseRules", spaceId] as const,
  kkCloses: (spaceId: string) => ["kkCloses", spaceId] as const,
  kkCash: (spaceId: string) => ["kkCash", spaceId] as const,
  kkCashDays: (spaceId: string) => ["kkCashDays", spaceId] as const,
  kkCredit: (spaceId: string) => ["kkCredit", spaceId] as const,
  kkCustomers: (spaceId: string) => ["kkCustomers", spaceId] as const,
  kkStock: (spaceId: string) => ["kkStock", spaceId] as const,
  kkStaff: (spaceId: string) => ["kkStaff", spaceId] as const,
  kkSuppliers: (spaceId: string) => ["kkSuppliers", spaceId] as const,
  kkGate: (spaceId: string) => ["kkGate", spaceId] as const,
  kkGrowthSettings: (spaceId: string) => ["kkGrowthSettings", spaceId] as const,
  kkZakat: (spaceId: string, input: string) => ["kkZakat", spaceId, input] as const,
  kkZakatHistory: (spaceId: string) => ["kkZakatHistory", spaceId] as const,
  kkScale: (spaceId: string) => ["kkScale", spaceId] as const,
  kkStockCounts: (spaceId: string) => ["kkStockCounts", spaceId] as const,
  kkCatalog: (spaceId: string) => ["kkCatalog", spaceId] as const,
  kkSellerDay: (spaceId: string) => ["kkSellerDay", spaceId] as const,
  kkShiftDraft: (spaceId: string, input: string) => ["kkShiftDraft", spaceId, input] as const,
  kkShifts: (spaceId: string) => ["kkShifts", spaceId] as const,
  learning: (spaceId: string) => ["learning", spaceId] as const,
  kkLearning: (spaceId: string) => ["kkLearning", spaceId] as const,
  kkOwnerSuggest: (spaceId: string) => ["kkOwnerSuggest", spaceId] as const,
  hourSuggest: (spaceId: string, memberId: string) => ["hourSuggest", spaceId, memberId] as const,
  summary: (spaceId: string, balanceDelta: string | null) => ["summary", spaceId, balanceDelta] as const,
};

/**
 * Qulflanganda: barcha moliyaviy ma'lumot keshdan o'chiriladi va sessiya holati qayta so'raladi —
 * shunda UI darhol qulf ekraniga o'tadi (summalar ko'rinmaydi).
 */
export function resetAfterLock(client: QueryClient): void {
  client.removeQueries({ predicate: (q) => q.queryKey[0] !== keys.session[0] });
  void client.invalidateQueries({ queryKey: keys.session });
}
