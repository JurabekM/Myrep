import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfIncomeRecordedDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";
import { draftFrom, PurposeShares, type SharesDraft, sharesInput } from "./PurposeShares";

export type MfEntryMode = "SALARY" | "OTHER_INCOME" | "EXPENSE" | "SENT_HOME" | "FUND_IN" | "FUND_OUT" | "OPENING" | "FUND_OPENING" | "RESERVE_IN" | "RESERVE_OUT" | "RESERVE_OPENING";
type Channel = "CASH" | "CARD";

/**
 * Musofir yozuvi (musofir/SPEC 2–3): maosh, boshqa daromad, xarajat, uyga yuborish, jamg'armaga /
 * jamg'armadan, boshlang'ich qoldiqlar. Summalar ish valyutasida, matn ko'rinishida yadroga beriladi.
 */
export function MfEntryDialog({
  spaceId,
  mode,
  workCurrency,
  homeCurrency,
  initialAmount,
  onClose,
  onIncome,
}: {
  spaceId: string;
  mode: MfEntryMode;
  workCurrency: string;
  homeCurrency: string;
  initialAmount?: string;
  onClose: () => void;
  onIncome?: (r: MfIncomeRecordedDto) => void;
}) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const income = mode === "SALARY" || mode === "OTHER_INCOME";
  const hasChannel = income || mode === "EXPENSE";
  const withdrawal = mode === "FUND_OUT" || mode === "RESERVE_OUT";
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)), enabled: mode === "EXPENSE" });
  const [amount, setAmount] = useState(initialAmount ?? "");
  const [channel, setChannel] = useState<Channel>("CARD");
  const [categoryId, setCategoryId] = useState("");
  const [fee, setFee] = useState("");
  const [received, setReceived] = useState("");
  const [occurredOn, setOccurredOn] = useState("");
  const [note, setNote] = useState("");
  // «Sarmoya» belgisi (M6): o'qish xarajati — toifa, ulush va jamg'arma o'zgarmaydi.
  const [selfInvestment, setSelfInvestment] = useState(false);
  // Uyga yuborish: maqsadlar — kelishuv shartlaridan taklif, o'zgartirish mumkin (M2).
  const terms = useQuery({ queryKey: keys.mfTerms(spaceId), queryFn: () => call(commands.mfTerms(spaceId)), enabled: mode === "SENT_HOME" });
  const [shares, setShares] = useState<SharesDraft | null>(null);
  const purposes = shares ?? draftFrom(terms.data?.shares);

  const save = useMutation({
    mutationFn: async () => {
      const date = occurredOn || null;
      const text = note.trim() || null;
      if (income) {
        const r = await call(commands.mfRecordIncome(spaceId, { kind: mode, amount, channel, occurredOn: date, note: text }));
        onIncome?.(r);
        return;
      }
      if (mode === "EXPENSE") {
        const id = categoryId || categories.data?.[0]?.id || "";
        await call(commands.mfRecordExpense(spaceId, { amount, categoryId: id, channel, occurredOn: date, note: text, selfInvestment }));
        return;
      }
      const sent = mode === "SENT_HOME";
      await call(
        commands.mfRecordMove(spaceId, {
          kind: mode,
          amount,
          fee: sent ? fee.trim() || null : null,
          received: sent ? received.trim() || null : null,
          occurredOn: date,
          note: text,
          purposes: sent ? sharesInput(purposes) : null,
        }),
      );
    },
    onSuccess: onClose,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="mf-entry-title" className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4">
      <div className="card max-h-full w-full max-w-md overflow-y-auto">
        <h2 id="mf-entry-title" className="mb-1 text-xl font-semibold">
          {t(`mf.action.${mode}`)}
        </h2>
        <p className="mb-4 text-sm text-ink-muted">{t(`mf.hint.${mode}`)}</p>
        <form className="flex flex-col gap-4" onSubmit={submit}>
          <label>
            <span className="label">{t("mf.amountIn", { currency: workCurrency })}</span>
            <AmountInput autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          {mode === "EXPENSE" && (
            <label>
              <span className="label">{t("kk.category")}</span>
              <select className="field" value={categoryId || categories.data?.[0]?.id || ""} onChange={(e) => setCategoryId(e.target.value)}>
                {categories.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.customName ?? t(c.nameKey)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {mode === "EXPENSE" && (
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={selfInvestment} onChange={(e) => setSelfInvestment(e.target.checked)} aria-describedby="mf-self-investment-hint" />
              <span>
                {t("mf.selfInvestment")}
                <span id="mf-self-investment-hint" className="block text-xs text-ink-muted">
                  {t("mf.selfInvestmentHint")}
                </span>
              </span>
            </label>
          )}
          {mode === "SENT_HOME" && (
            <>
              <label>
                <span className="label">{t("mf.fee", { currency: workCurrency })}</span>
                <AmountInput value={fee} onChange={(e) => setFee(e.target.value)} />
              </label>
              <label>
                <span className="label">{t("mf.received", { currency: homeCurrency })}</span>
                <AmountInput value={received} onChange={(e) => setReceived(e.target.value)} />
              </label>
              <PurposeShares legend={t("mf.purposesLegend")} value={purposes} onChange={setShares} />
            </>
          )}
          {hasChannel && (
            <fieldset>
              <legend className="label">{t("mf.channel")}</legend>
              <div className="flex gap-2">
                {(["CARD", "CASH"] as const).map((c) => (
                  <button key={c} type="button" aria-pressed={channel === c} className={channel === c ? "btn-primary" : "btn-ghost"} onClick={() => setChannel(c)}>
                    {t(`kk.channel.${c}`)}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          <label>
            <span className="label">{t("kk.date")}</span>
            <input type="date" className="field" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} />
          </label>
          <label>
            <span className="label">{withdrawal ? t("mf.reason") : t("kk.note")}</span>
            <input className="field" value={note} onChange={(e) => setNote(e.target.value)} required={withdrawal} />
          </label>
          <ErrorText error={save.error} />
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" disabled={save.isPending}>
              {t("common.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
