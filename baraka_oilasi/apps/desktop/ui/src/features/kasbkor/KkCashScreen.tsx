import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkCashDraftDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const REASONS = ["UNRECORDED_EXPENSE", "CHANGE_ERROR", "GIVEN_ON_CREDIT", "OWNER_TOOK", "UNKNOWN"] as const;

/**
 * Kunlik kassa yopish (kasbkor/SPEC 5.1): ochilish → naqd tushum, chiqim, «egasi oldi», kartaga
 * topshirilgan → kutilgan → sanalgan → farq. Hisob yadroda; yopilgan kun o'zgarmaydi.
 */
export function KkCashScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const draft = useQuery({ queryKey: keys.kkCash(spaceId), queryFn: () => call(commands.kkCashDraft(spaceId, null, null)) });
  const closed = draft.error instanceof CoreError && draft.error.code === "CASH_DAY_CLOSED";
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.cash.title")}</h1>
      <p className="text-ink-muted">{t("kk.cash.intro")}</p>
      {closed && (
        <p role="status" className="card">
          {t("kk.cash.todayClosed")}
        </p>
      )}
      {draft.error && !closed && <ErrorText error={draft.error} />}
      {draft.data && !draft.error && <CloseForm spaceId={spaceId} d={draft.data} />}
      <History spaceId={spaceId} />
    </section>
  );
}

function Row({ label, value, testId, strong }: { label: string; value: string; testId?: string; strong?: boolean }) {
  return (
    <tr className={`border-t border-line ${strong ? "font-semibold" : ""}`}>
      <th scope="row" className="py-1 pr-3 text-left font-normal">
        {strong ? <span className="font-semibold">{label}</span> : label}
      </th>
      <td data-testid={testId} className="py-1 text-right tabular-nums">
        {value}
      </td>
    </tr>
  );
}

function CloseForm({ spaceId, d }: { spaceId: string; d: KkCashDraftDto }) {
  const { t } = useTranslation();
  const [counted, setCounted] = useState("");
  const [reason, setReason] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const check = useMutation({ mutationFn: () => call(commands.kkCashDraft(spaceId, d.day, counted)) });
  const close = useMutation({ mutationFn: () => call(commands.kkCloseCashDay(spaceId, { day: d.day, counted, reason, note: note.trim() || null })) });
  // Sanalgan summa o'zgarsa, eski tekshiruv natijasi tashlanadi (`check.reset()`).
  const checked = check.data;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    check.mutate();
  };
  const diffStatus = checked?.status;
  return (
    <div className="flex flex-col gap-5">
      <section className="card flex flex-col gap-2" aria-labelledby="kk-cash-day">
        <h2 id="kk-cash-day" className="text-lg font-semibold">
          {t("kk.cash.day", { date: showDate(d.day) })}
        </h2>
        <table className="w-full text-sm">
          <tbody>
            <Row label={t("kk.cash.opening")} value={d.opening.formatted} testId="kk-cash-opening" />
            <Row label={t("kk.cash.sales")} value={`+ ${d.cashSales.formatted}`} />
            <Row label={t("kk.cash.expenses")} value={`− ${d.cashExpenses.formatted}`} />
            <Row label={t("kk.cash.ownerDraws")} value={`− ${d.ownerDraws.formatted}`} />
            <Row label={t("kk.cash.handedOver")} value={`− ${d.handedOver.formatted}`} />
            {d.otherIn.minor !== "0" && <Row label={t("kk.cash.otherIn")} value={`+ ${d.otherIn.formatted}`} />}
            {d.otherOut.minor !== "0" && <Row label={t("kk.cash.otherOut")} value={`− ${d.otherOut.formatted}`} />}
            <Row label={t("kk.cash.expected")} value={d.expected.formatted} testId="kk-cash-expected" strong />
          </tbody>
        </table>
      </section>

      <form className="card flex flex-col gap-4" onSubmit={submit} aria-label={t("kk.cash.countForm")}>
        <label>
          <span className="label">{t("kk.cash.counted")}</span>
          <AmountInput
            value={counted}
            onChange={(e) => {
              setCounted(e.target.value);
              check.reset();
            }}
            required
          />
        </label>
        <button className="btn-ghost self-start" disabled={check.isPending}>
          {t("kk.cash.check")}
        </button>
        <ErrorText error={check.error} />
        {checked && checked.difference && (
          <div className="flex flex-col gap-3">
            <p role="status" data-testid="kk-cash-difference" className={diffStatus === "EXACT" ? "text-lg" : "text-lg text-warn"}>
              {t(`kk.cash.status.${diffStatus}`, { amount: checked.difference.formatted })}
            </p>
            {checked.suggestSearch && (
              <p role="note" className="text-sm text-warn">
                {t("kk.cash.suggestSearch")}
              </p>
            )}
            {diffStatus !== "EXACT" && (
              <>
                <fieldset>
                  <legend className="label">{t("kk.cash.reason")}</legend>
                  <div className="flex flex-col gap-1">
                    {REASONS.map((r) => (
                      <label key={r} className="flex items-center gap-2">
                        <input type="radio" name="kk-cash-reason" checked={reason === r} onChange={() => setReason(r)} />
                        {t(`kk.cash.reasons.${r}`)}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <label>
                  <span className="label">{t("kk.note")}</span>
                  <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
                </label>
              </>
            )}
            <p className="text-sm text-ink-muted">{t("kk.cash.finalWarning")}</p>
            <ErrorText error={close.error} />
            <button type="button" className="btn-primary self-start" disabled={close.isPending} onClick={() => close.mutate()}>
              {t("kk.cash.close")}
            </button>
          </div>
        )}
      </form>
    </div>
  );
}

function History({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const days = useQuery({ queryKey: keys.kkCashDays(spaceId), queryFn: () => call(commands.kkCashDays(spaceId)) });
  if (!days.data || days.data.length === 0) return null;
  return (
    <section className="card flex flex-col gap-2" aria-label={t("kk.cash.history")}>
      <h2 className="text-lg font-semibold">{t("kk.cash.history")}</h2>
      <table className="w-full text-left text-sm">
        <thead className="text-ink-muted">
          <tr>
            <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.cash.expected")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.cash.countedShort")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.cash.difference")}</th>
            <th className="py-1 font-normal">{t("kk.cash.reason")}</th>
          </tr>
        </thead>
        <tbody>
          {days.data.slice(0, 31).map((c) => (
            <tr key={c.id} className="border-t border-line">
              <td className="py-1 pr-3 tabular-nums">{showDate(c.day)}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{c.expected.formatted}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{c.counted.formatted}</td>
              <td className={`py-1 pr-3 text-right tabular-nums ${c.status === "EXACT" ? "" : "text-warn"}`}>{c.difference.formatted}</td>
              <td className="py-1">
                {c.reason ? t(`kk.cash.reasons.${c.reason}`) : "—"}
                {c.note && <span className="block text-xs text-ink-muted">{c.note}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
