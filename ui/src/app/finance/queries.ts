import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { commands } from "../../bindings/bindings";
import { unwrap } from "./command-error";

/** Moliya keshlari uchun kalitlar. Barchasi `finance` prefiksi bilan: yozuv o'zgarsa, hammasi yangilanadi. */
export const financeKeys = {
  all: ["finance"] as const,
  home: ["finance", "home"] as const,
  incomes: ["finance", "incomes"] as const,
  recent: ["finance", "recent"] as const,
  vault: ["finance", "vault"] as const,
  audit: ["finance", "audit"] as const,
  whose: (monthsBack: number) => ["finance", "whose", monthsBack] as const,
  categories: ["finance", "categories"] as const,
  obligations: ["finance", "obligations"] as const,
  debts: ["finance", "debts"] as const,
  reserve: ["finance", "reserve"] as const,
  prices: ["finance", "prices"] as const,
};

/** Moliyaviy yozuv o'zgarganda barcha moliya keshlarini qayta yuklaydi. */
export function useInvalidateFinance(): () => Promise<void> {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: financeKeys.all });
  }, [queryClient]);
}

/** Har bir so'rov uchun bir xil: IPC natijasi qiymatga aylanadi, xato — `CommandError`. */
export const fetchers = {
  home: () => commands.getHome().then(unwrap),
  incomes: () => commands.listIncomesThisMonth().then(unwrap),
  recent: () => commands.listRecentIncomes().then(unwrap),
  vault: () => commands.getVault().then(unwrap),
  audit: () => commands.getAudit().then(unwrap),
  whose: (monthsBack: number) => commands.getWhoseMoney(monthsBack).then(unwrap),
  categories: () => commands.listCategories().then(unwrap),
  obligations: () => commands.listObligations().then(unwrap),
  debts: () => commands.listDebts().then(unwrap),
};
