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
