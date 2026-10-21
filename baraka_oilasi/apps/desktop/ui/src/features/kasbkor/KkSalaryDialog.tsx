import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkOverviewDto, type KkSalaryPaidDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { useDialog } from "../../lib/useDialog";

/**
 * Egasi maoshini Uy makoniga o'tkazish (BARAKA_OILASI 4.6): bitta atomar yozuv — Kasb-kor'da chiqim
 * («maosh»), Uy'da daromad. Keyin Uy'dagi odatiy 1-qonun ulushi taklifi.
 */
export function KkSalaryDialog({ spaceId, overview, onClose }: { spaceId: string; overview: KkOverviewDto; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [amount, setAmount] = useState(overview.salaryRemaining?.plain ?? "");
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CARD");
  const [paid, setPaid] = useState<KkSalaryPaidDto | null>(null);

  const pay = useMutation({
    mutationFn: () => call(commands.kkPayOwnerSalary(spaceId, { amount: amount.trim() || null, wallet, occurredOn: null, note: null })),
    onSuccess: setPaid,
  });
  const allocate = useMutation({
    mutationFn: (p: KkSalaryPaidDto) => call(commands.allocateToVault(p.uySpaceId, p.uyIncome.income.id, p.uyIncome.suggestedShare.plain)),
    onSuccess: onClose,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    pay.mutate();
  };

  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="kk-salary-title" className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4">
      <div className="card w-full max-w-md">
        <h2 id="kk-salary-title" className="mb-4 text-xl font-semibold">
          {t("kk.paySalary")}
        </h2>
        {!paid ? (
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <p className="text-sm text-ink-muted">{t("kk.paySalaryHint")}</p>
            <label>
              <span className="label">{t("common.amount")}</span>
              <AmountInput autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} />
            </label>
            <fieldset>
              <legend className="label">{t("kk.fromWallet")}</legend>
              <div className="flex gap-2">
                {(["CASH", "CARD"] as const).map((w) => (
                  <button key={w} type="button" aria-pressed={wallet === w} className={wallet === w ? "btn-primary" : "btn-ghost"} onClick={() => setWallet(w)}>
                    {t(`kk.wallet.${w}`)}
                  </button>
                ))}
              </div>
            </fieldset>
            <ErrorText error={pay.error} />
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={onClose}>
                {t("common.cancel")}
              </button>
              <button className="btn-primary" disabled={pay.isPending}>
                {t("kk.transfer")}
              </button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-4">
            <p role="status">{t("kk.salaryPaid", { amount: paid.uyIncome.income.amount.formatted })}</p>
            <p className="text-lg">{t("income.shareOffer", { amount: paid.uyIncome.suggestedShare.formatted })}</p>
            <ErrorText error={allocate.error} />
            <div className="flex flex-wrap justify-end gap-2">
              <button className="btn-ghost" onClick={onClose}>
                {t("income.notNow")}
              </button>
              <button autoFocus className="btn-primary" disabled={allocate.isPending} onClick={() => allocate.mutate(paid)}>
                {t("income.allocate")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
