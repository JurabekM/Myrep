import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type IncomeRecordedDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { useDialog } from "../../lib/useDialog";

/**
 * Tez daromad kiritish (Ctrl+N) va ulush taklifi: [Ajratish] [Boshqa summa] [Bu safar emas].
 * Taklif qilingan summa yadrodan `plain` ko'rinishida olinadi va o'zgarishsiz qaytariladi.
 */
export function IncomeDialog({ spaceId, onClose }: { spaceId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [amount, setAmount] = useState("");
  const [source, setSource] = useState("");
  const [channel, setChannel] = useState<"CASH" | "CARD">("CASH");
  const [recorded, setRecorded] = useState<IncomeRecordedDto | null>(null);
  const [custom, setCustom] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      call(commands.recordIncome(spaceId, { amount, source, channel, memberId: null, occurredOn: null, sourceType: null, note: null })),
    onSuccess: setRecorded,
  });
  const allocate = useMutation({
    mutationFn: (share: string) => call(commands.allocateToVault(spaceId, recorded?.income.id ?? "", share)),
    onSuccess: onClose,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="income-title" className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4">
      <div className="card w-full max-w-md">
        <h2 id="income-title" className="mb-4 text-xl font-semibold">{t("income.title")}</h2>
        {!recorded ? (
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <label>
              <span className="label">{t("common.amount")}</span>
              <AmountInput autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} required />
            </label>
            <label>
              <span className="label">{t("income.source")}</span>
              <input className="field" value={source} onChange={(e) => setSource(e.target.value)} required />
            </label>
            <div className="flex gap-2">
              {(["CASH", "CARD"] as const).map((c) => (
                <button key={c} type="button" aria-pressed={channel === c} className={channel === c ? "btn-primary" : "btn-ghost"} onClick={() => setChannel(c)}>
                  {t(`income.channel.${c}`)}
                </button>
              ))}
            </div>
            <ErrorText error={save.error} />
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-ghost" onClick={onClose}>{t("common.cancel")}</button>
              <button className="btn-primary" disabled={save.isPending}>{t("common.save")}</button>
            </div>
          </form>
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-lg">{t("income.shareOffer", { amount: recorded.suggestedShare.formatted })}</p>
            {recorded.progressiveSuggestionPercent !== null && (
              <p className="text-sm text-accent-text">{t("income.progressive", { percent: recorded.progressiveSuggestionPercent })}</p>
            )}
            {custom !== null && (
              <label>
                <span className="label">{t("income.otherAmount")}</span>
                <AmountInput autoFocus value={custom} onChange={(e) => setCustom(e.target.value)} />
              </label>
            )}
            <ErrorText error={allocate.error} />
            <div className="flex flex-wrap justify-end gap-2">
              <button className="btn-ghost" onClick={onClose}>{t("income.notNow")}</button>
              {custom === null ? (
                <>
                  <button className="btn-ghost" onClick={() => setCustom(recorded.suggestedShare.plain)}>{t("income.otherAmount")}</button>
                  {/* Fokus «Ajratish»da: daromad → Enter → Enter (≤ 3 bosish, uy/SPEC 2.1). */}
                  <button autoFocus className="btn-primary" onClick={() => allocate.mutate(recorded.suggestedShare.plain)}>{t("income.allocate")}</button>
                </>
              ) : (
                <button className="btn-primary" onClick={() => allocate.mutate(custom)}>{t("income.allocate")}</button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
