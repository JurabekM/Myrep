import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfTravelDebtDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const TONE: Record<string, string> = { CLEARED: "text-accent-text", ON_TRACK: "text-accent-text", BEHIND: "text-warn", NO_PAYMENTS: "text-ink-muted" };

function Row({ label, value, testId, strong }: { label: string; value: string; testId?: string; strong?: boolean }) {
  return (
    <tr className="border-t border-line">
      <td className="py-1 pr-3">{label}</td>
      <td data-testid={testId} className={`py-1 text-right tabular-nums ${strong ? "font-semibold" : ""}`}>
        {value}
      </td>
    </tr>
  );
}

/**
 * Yo'l qarzidan chiqish (musofir/SPEC 6.1, 4-qonun): Uy makonidagi U8 qarzi «yo'l qarzi» deb
 * belgilanadi; uyda «Qarz to'lovi» maqsadidan to'lanadi. Reja (necha oyda yopiladi) — yadrodan.
 */
export function TravelDebtCard({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: keys.mfTravelDebt(spaceId), queryFn: () => call(commands.mfTravelDebt(spaceId)) });
  const [editing, setEditing] = useState(false);
  const d = q.error ? undefined : q.data;
  return (
    <section className="card flex flex-col gap-3" aria-label={t("mf.travel.title")}>
      <h2 className="text-lg font-semibold">{t("mf.travel.title")}</h2>
      <ErrorText error={q.error} />
      {d && editing && <TravelDebtForm spaceId={spaceId} d={d} onDone={() => setEditing(false)} />}
      {d && !editing && <TravelDebtView d={d} />}
      {d && !editing && (d.debt || d.candidates.length > 0) && (
        <button className="btn-ghost self-start" onClick={() => setEditing(true)}>
          {d.debt ? t("mf.travel.change") : t("mf.travel.choose")}
        </button>
      )}
    </section>
  );
}

function TravelDebtView({ d }: { d: MfTravelDebtDto }) {
  const { t } = useTranslation();
  if (!d.debt) {
    return <p className="text-sm text-ink-muted">{d.candidates.length === 0 ? t("mf.travel.noDebts") : t("mf.travel.intro")}</p>;
  }
  const p = d.plan;
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>
        <span className="font-medium">{d.debt.creditor}</span>
        {d.debt.reason && <span className="text-ink-muted"> · {d.debt.reason}</span>}
      </p>
      {p && (
        <>
          <p data-testid="mf-travel-status" className={TONE[p.status] ?? ""}>
            {t(`mf.travel.status.${p.status}`, {
              months: p.monthsToClear ?? 0,
              date: p.clearOn ? showDate(p.clearOn) : "",
              target: d.targetMonths,
              amount: p.requiredMonthly.formatted,
            })}
          </p>
          <table className="w-full">
            <tbody>
              <Row label={t("mf.travel.outstanding")} value={d.debt.outstanding.formatted} />
              <Row label={t("mf.travel.available")} value={p.available.formatted} />
              <Row label={t("mf.travel.remaining")} value={p.remaining.formatted} testId="mf-travel-remaining" strong />
              {p.avgMonthly && <Row label={t("mf.travel.avg", { count: p.monthsUsed })} value={p.avgMonthly.formatted} />}
              <Row label={t("mf.travel.required", { count: d.targetMonths })} value={p.requiredMonthly.formatted} />
            </tbody>
          </table>
          {p.status === "BEHIND" && <p className="text-xs text-ink-muted">{t("mf.travel.raiseShare")}</p>}
        </>
      )}
      <p className="text-xs text-ink-muted">{t("mf.travel.payWhere")}</p>
    </div>
  );
}

function TravelDebtForm({ spaceId, d, onDone }: { spaceId: string; d: MfTravelDebtDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [debtId, setDebtId] = useState(d.debt?.id ?? d.candidates[0]?.id ?? "");
  const [months, setMonths] = useState(String(d.targetMonths));
  const save = useMutation({
    mutationFn: (id: string | null) => call(commands.mfSetTravelDebt(spaceId, { debtId: id, targetMonths: Number.parseInt(months, 10) || null })),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(debtId || null);
  };
  const options = d.debt && !d.candidates.some((c) => c.id === d.debt?.id) ? [d.debt, ...d.candidates] : d.candidates;
  return (
    <form className="flex flex-col gap-3" aria-label={t("mf.travel.form")} onSubmit={submit}>
      <label>
        <span className="label">{t("mf.travel.which")}</span>
        <select className="field" value={debtId} onChange={(e) => setDebtId(e.target.value)}>
          {options.map((c) => (
            <option key={c.id} value={c.id}>
              {c.creditor} · {c.outstanding.formatted}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">{t("mf.travel.targetMonths")}</span>
        <input className="field w-32" type="number" min={1} max={60} value={months} onChange={(e) => setMonths(e.target.value)} />
      </label>
      <p className="text-xs text-ink-muted">{t("mf.travel.targetHint")}</p>
      <ErrorText error={save.error} />
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={save.isPending || !debtId}>
          {t("common.save")}
        </button>
        {d.debt && (
          <button type="button" className="btn-ghost" disabled={save.isPending} onClick={() => save.mutate(null)}>
            {t("mf.travel.unmark")}
          </button>
        )}
        <button type="button" className="btn-ghost" onClick={onDone}>
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
