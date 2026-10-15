import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { type AgreementDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";

/** Kelishuv keshlari. */
export const agreementKeys = {
  all: ["agreements"] as const,
  list: ["agreements", "list"] as const,
  one: (id: string) => ["agreements", "one", id] as const,
  journal: (id: string) => ["agreements", "journal", id] as const,
  partnerships: ["agreements", "partnerships"] as const,
  venture: (partnershipId: string) => ["agreements", "venture", partnershipId] as const,
};

export const agreementFetchers = {
  list: () => commands.listAgreements().then(unwrap),
  one: (id: string) => () => commands.getAgreement(id).then(unwrap),
  journal: (id: string) => () => commands.getJournal(id).then(unwrap),
};

/** Yangilangan kelishuvni keshga yozadi va ro'yxatni qayta so'raydi. */
export function useApplyAgreement(): (next: AgreementDto) => Promise<void> {
  const queryClient = useQueryClient();
  return useCallback(
    async (next: AgreementDto) => {
      queryClient.setQueryData(agreementKeys.one(next.id), next);
      await queryClient.invalidateQueries({ queryKey: agreementKeys.list });
      await queryClient.invalidateQueries({ queryKey: agreementKeys.journal(next.id) });
    },
    [queryClient],
  );
}
