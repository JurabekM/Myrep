import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { commands, type RepaymentResultDto } from "../bindings";
import { call } from "../lib/api";
import { ErrorText } from "./ErrorText";

/**
 * Qarz yopildi (uy/SPEC 2D.9): nishonlash va boʻshagan oylik toʻlovni «Kelajagim»ga
 * yoʻnaltirish taklifi. Summa yadrodan `plain` koʻrinishida olinib, oʻzgarishsiz qaytariladi.
 */
export function CelebrationDialog({ spaceId, result, onClose }: { spaceId: string; result: RepaymentResultDto; onClose: () => void }) {
  const { t } = useTranslation();
  const freed = result.freedMonthly;
  const save = useMutation({
    mutationFn: () => call(commands.depositToVault(spaceId, freed?.plain ?? "0", t("celebrate.vaultNote"))),
    onSuccess: onClose,
  });
  return (
    <div role="dialog" aria-modal="true" aria-labelledby="celebrate-title" className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <div className="card flex w-full max-w-md flex-col gap-3">
        <h2 id="celebrate-title" className="text-xl font-semibold text-accent-text">
          {result.debtFree ? t("celebrate.debtFree") : t("celebrate.closed")}
        </h2>
        <p>{result.debtFree ? t("celebrate.debtFreeText") : t("celebrate.closedText")}</p>
        {result.modeReturned && <p className="text-sm text-ink-muted">{t("celebrate.modeReturned")}</p>}
        {freed && <p className="text-sm">{t("celebrate.freed", { amount: freed.formatted })}</p>}
        <ErrorText error={save.error} />
        <div className="flex flex-wrap gap-2">
          {freed && (
            <button className="btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>
              {t("celebrate.toVault")}
            </button>
          )}
          <button className="btn-ghost" onClick={onClose}>{t("celebrate.later")}</button>
        </div>
      </div>
    </div>
  );
}
