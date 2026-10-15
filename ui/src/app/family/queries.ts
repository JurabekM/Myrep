import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { financeKeys } from "../finance/queries";

/** Oila va havas keshlari. Barchasi `family` prefiksi bilan. */
export const familyKeys = {
  all: ["family"] as const,
  summary: ["family", "summary"] as const,
  expenses: ["family", "expenses"] as const,
  limit: ["family", "limit"] as const,
  members: ["family", "members"] as const,
  treats: ["family", "treats"] as const,
  habits: ["family", "habits"] as const,
};

/** Xarajat, toifa, a'zo yoki rozilik o'zgarganda oila keshlari (va toifalar) yangilanadi. */
export function useInvalidateFamily(): () => Promise<void> {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: familyKeys.all });
    await queryClient.invalidateQueries({ queryKey: financeKeys.categories });
  }, [queryClient]);
}

/** Har bir so'rov uchun bir xil: IPC natijasi qiymatga aylanadi, xato — `CommandError`. */
export const familyFetchers = {
  summary: () => commands.getMonthSummary().then(unwrap),
  expenses: () => commands.listMonthExpenses().then(unwrap),
  limit: () => commands.getHavasLimit().then(unwrap),
  members: () => commands.listMembers().then(unwrap),
  treats: () => commands.listTreats().then(unwrap),
  habits: () => commands.listHabits().then(unwrap),
};

/** PIN maydoni: faqat raqamlar, 6 tagacha. */
export function sanitizePin(value: string): string {
  return value.replace(/\D/g, "").slice(0, 6);
}
