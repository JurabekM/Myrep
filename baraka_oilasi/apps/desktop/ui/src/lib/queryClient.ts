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
