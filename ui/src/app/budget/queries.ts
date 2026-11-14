import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { type BudgetDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { financeKeys } from "../finance/queries";

/** Byudjet keshi. Barchasi `budget` prefiksi bilan. */
export const budgetKeys = {
  all: ["budget"] as const,
  overview: ["budget", "overview"] as const,
};

/** Byudjet o'zgarishi natijasi (to'liq holat) keshga yoziladi; «Kelajagim» keshi ham yangilanadi. */
export function useApplyBudget(): (next: BudgetDto) => Promise<void> {
  const queryClient = useQueryClient();
  return useCallback(
    async (next: BudgetDto) => {
      queryClient.setQueryData(budgetKeys.overview, next);
      await queryClient.invalidateQueries({ queryKey: financeKeys.vault });
    },
    [queryClient],
  );
}

/** So'rov: IPC natijasi qiymatga aylanadi, xato — `CommandError`. */
export const budgetFetchers = {
  overview: () => commands.getBudget().then(unwrap),
};
