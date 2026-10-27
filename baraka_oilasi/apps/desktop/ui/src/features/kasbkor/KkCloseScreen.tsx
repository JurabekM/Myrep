import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkCloseDraftDto, type KkCloseRulesDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const TAX_BASES = ["NONE", "REVENUE", "PROFIT", "FIXED"] as const;
const SPLIT = ["reserve", "working", "expansion", "sadaqa"] as const;

/**
 * «Hisob kuni» (kasbkor/SPEC 4.5): oy yakunlari → soliq zaxirasi → egasi maoshi → qolgan pul va
 * taqsimot → bayonnoma. Hamma raqam yadrodan; bayonnoma yopilgandan keyin o'zgarmaydi.
 */
export function KkCloseScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const draft = useQuery({ queryKey: keys.kkClose(spaceId), queryFn: () => call(commands.kkCloseDraft(spaceId, null)) });
  const rules = useQuery({ queryKey: keys.kkCloseRules(spaceId), queryFn: () => call(commands.kkCloseRules(spaceId)) });
  const [editingRules, setEditingRules] = useState(false);
  const closed = draft.error instanceof CoreError && draft.error.code === "ALREADY_CLOSED";
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.close.title")}</h1>
      <p className="text-ink-muted">{t("kk.close.intro")}</p>
      {closed && (
        <p role="status" className="card">
          {t("kk.close.lastClosed")}
        </p>
      )}
      {draft.error && !closed && <ErrorText error={draft.error} />}
      {rules.data && (
        <section className="card flex flex-col gap-3" aria-label={t("kk.close.rules")}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">{t("kk.close.rules")}</h2>
            <button className="btn-ghost px-3 py-1 text-sm" aria-expanded={editingRules} onClick={() => setEditingRules((v) => !v)}>
              {t("kk.close.rulesChange")}
            </button>
          </div>
          <RulesSummary rules={rules.data} />
          {editingRules && <RulesForm spaceId={spaceId} rules={rules.data} onDone={() => setEditingRules(false)} />}
        </section>
      )}
      {/* Qayta so'rov xato bersa (masalan, oy yopildi), TanStack eski qoralamani saqlaydi — ko'rsatilmaydi. */}
      {draft.data && !draft.error && <Draft spaceId={spaceId} d={draft.data} />}
      <History spaceId={spaceId} />
    </section>
  );
}

function RulesSummary({ rules }: { rules: KkCloseRulesDto }) {
  const { t } = useTranslation();
  const tax =
    rules.taxBase === "FIXED"
      ? t("kk.close.taxFixedShow", { amount: rules.taxFixed?.formatted ?? "" })
      : rules.taxBase === "NONE"
        ? t("kk.close.taxNone")
        : t(`kk.close.taxShow.${rules.taxBase}`, { percent: rules.taxPercent });
  return (
    <p className="text-sm">
      {tax} · {t("kk.close.splitShow", { reserve: rules.reservePercent, working: rules.workingPercent, expansion: rules.expansionPercent, sadaqa: rules.sadaqaPercent })}
    </p>
  );
}

function RulesForm({ spaceId, rules, onDone }: { spaceId: string; rules: KkCloseRulesDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [base, setBase] = useState(rules.taxBase);
  const [f, setF] = useState({
    taxPercent: rules.taxPercent,
    taxFixed: rules.taxFixed?.plain ?? "",
    reserve: rules.reservePercent,
    working: rules.workingPercent,
    expansion: rules.expansionPercent,
    sadaqa: rules.sadaqaPercent,
  });
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkSetCloseRules(spaceId, {
          taxBase: base,
          taxPercent: base === "REVENUE" || base === "PROFIT" ? f.taxPercent : null,
          taxFixed: base === "FIXED" ? f.taxFixed : null,
          reservePercent: f.reserve,
          workingPercent: f.working,
          expansionPercent: f.expansion,
          sadaqaPercent: f.sadaqa,
        }),
      ),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-col gap-4 border-t border-line pt-3" onSubmit={submit} aria-label={t("kk.close.rulesForm")}>
      <fieldset>
        <legend className="label">{t("kk.close.taxBase")}</legend>
        <div className="flex flex-wrap gap-4">
          {TAX_BASES.map((b) => (
            <label key={b} className="flex items-center gap-2">
              <input type="radio" name="kk-tax-base" checked={base === b} onChange={() => setBase(b)} />
              {t(`kk.close.base.${b}`)}
            </label>
          ))}
        </div>
      </fieldset>
      {(base === "REVENUE" || base === "PROFIT") && (
        <label>
          <span className="label">{t("kk.close.taxPercent")}</span>
          <input className="field tabular-nums" inputMode="decimal" value={f.taxPercent} onChange={(e) => setF({ ...f, taxPercent: e.target.value })} />
        </label>
      )}
      {base === "FIXED" && (
        <label>
          <span className="label">{t("kk.close.taxFixed")}</span>
          <AmountInput value={f.taxFixed} onChange={(e) => setF({ ...f, taxFixed: e.target.value })} />
        </label>
      )}
      <p className="text-xs text-ink-muted">{t("kk.close.taxDisclaimer")}</p>
      <fieldset>
        <legend className="label">{t("kk.close.splitLegend")}</legend>
        <div className="grid gap-3 md:grid-cols-4">
          {SPLIT.map((k) => (
            <label key={k}>
              <span className="label">{t(`kk.close.part.${k}`)} (%)</span>
              <input className="field tabular-nums" inputMode="decimal" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} />
            </label>
          ))}
        </div>
      </fieldset>
      <ErrorText error={save.error} />
      <button className="btn-primary self-start" disabled={save.isPending}>
        {t("common.save")}
      </button>
    </form>
  );
}

function Row({ label, value, strong, testId }: { label: string; value: string; strong?: boolean; testId?: string }) {
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

function Draft({ spaceId, d }: { spaceId: string; d: KkCloseDraftDto }) {
  const { t } = useTranslation();
  const [carry, setCarry] = useState(false);
  const [explanation, setExplanation] = useState("");
  const close = useMutation({
    mutationFn: () => call(commands.kkCloseMonth(spaceId, { periodStart: d.periodStart, carryOverdraw: carry, explanation: explanation.trim() || null })),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    close.mutate();
  };
  const period = t("kk.period", { from: showDate(d.periodStart), to: showDate(d.periodEnd) });
  return (
    <form className="flex flex-col gap-5" onSubmit={submit} aria-label={t("kk.close.draft", { period })}>
      <section className="card flex flex-col gap-2" aria-labelledby="kk-close-step1">
        <h2 id="kk-close-step1" className="text-lg font-semibold">
          {t("kk.close.step1", { period })}
        </h2>
        <table className="w-full text-sm">
          <tbody>
            <Row label={t("kk.profit.revenue")} value={d.revenue.formatted} />
            <Row label={t("kk.close.expenses")} value={d.expenses.formatted} />
            {d.selfInvestment.minor !== "0" && <Row label={`· ${t("kk.close.selfInvestment")}`} value={d.selfInvestment.formatted} testId="kk-close-self-investment" />}
            <Row label={t("kk.trueProfitShort")} value={d.trueProfit.formatted} />
            <Row label={t("kk.profit.depreciation")} value={d.depreciation.formatted} />
          </tbody>
        </table>
      </section>

      <section className="card flex flex-col gap-2" aria-labelledby="kk-close-step2">
        <h2 id="kk-close-step2" className="text-lg font-semibold">
          {t("kk.close.step2")}
        </h2>
        <table className="w-full text-sm">
          <tbody>
            <Row label={t("kk.close.taxReserve")} value={`− ${d.tax.formatted}`} testId="kk-close-tax" />
            <Row label={t("kk.close.ownerPay")} value={`− ${d.ownerPay.formatted}`} />
          </tbody>
        </table>
        {d.ownerSalary && d.salaryRemaining && d.salaryRemaining.minor !== "0" && (
          <p role="note" className="text-sm text-warn">
            {t("kk.close.salaryNotPaid", { amount: d.salaryRemaining.formatted })}
          </p>
        )}
        {d.overdrawn && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={carry} onChange={(e) => setCarry(e.target.checked)} />
            {t("kk.close.carry", { amount: d.overdrawn.formatted })}
          </label>
        )}
      </section>

      <section className="card flex flex-col gap-2" aria-labelledby="kk-close-step3">
        <h2 id="kk-close-step3" className="text-lg font-semibold">
          {t("kk.close.step3")}
        </h2>
        <p className="text-sm text-ink-muted">{t("kk.close.remainingFormula")}</p>
        <p data-testid="kk-close-remaining" className="kpi text-accent">
          {d.remaining.formatted}
        </p>
        {d.allocation ? (
          <table className="w-full text-sm">
            <tbody>
              {SPLIT.map((k) => (
                <Row key={k} label={t(`kk.close.part.${k}`)} value={d.allocation?.[k].formatted ?? ""} testId={`kk-close-${k}`} />
              ))}
            </tbody>
          </table>
        ) : (
          <div>
            <label>
              <span className="label">{t("kk.close.explanation")}</span>
              <textarea className="field min-h-24" value={explanation} onChange={(e) => setExplanation(e.target.value)} aria-describedby="kk-close-negative" />
            </label>
            <p id="kk-close-negative" className="mt-1 text-sm text-warn">
              {t("kk.close.negative")}
            </p>
          </div>
        )}
        {d.reserveBelowDepreciation && (
          <p role="note" className="text-sm text-warn">
            {t("kk.close.reserveBelowDepreciation", { amount: d.depreciation.formatted })}
          </p>
        )}
      </section>

      <div className="card flex flex-col gap-3">
        <p className="text-sm">{t("kk.close.finalWarning")}</p>
        <ErrorText error={close.error} />
        <button className="btn-primary self-start" disabled={close.isPending}>
          {t("kk.close.submit")}
        </button>
      </div>
    </form>
  );
}

function History({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const list = useQuery({ queryKey: keys.kkCloses(spaceId), queryFn: () => call(commands.kkMonthCloses(spaceId)) });
  const pdf = useMutation({ mutationFn: (id: string) => call(commands.exportKkMonthClose(spaceId, id)) });
  if (!list.data || list.data.length === 0) return null;
  return (
    <section className="card flex flex-col gap-2" aria-label={t("kk.close.history")}>
      <h2 className="text-lg font-semibold">{t("kk.close.history")}</h2>
      <table className="w-full text-left text-sm">
        <thead className="text-ink-muted">
          <tr>
            <th className="py-1 pr-3 font-normal">{t("kk.close.col.period")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.close.col.remaining")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.close.col.reserve")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("kk.selfInvestment")}</th>
            <th className="py-1 pr-3 font-normal">{t("kk.close.col.code")}</th>
            <th className="py-1 font-normal">
              <span className="sr-only">{t("kk.eq.actions")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {list.data.map((c) => {
            const period = t("kk.period", { from: showDate(c.summary.periodStart), to: showDate(c.summary.periodEnd) });
            return (
              <tr key={c.id} className="border-t border-line">
                <td className="py-1 pr-3">{period}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{c.summary.remaining.formatted}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{c.summary.allocation?.reserve.formatted ?? "—"}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{c.summary.selfInvestment.formatted}</td>
                <td className="py-1 pr-3 font-mono text-xs">{c.shortCode}</td>
                <td className="py-1 text-right">
                  <button className="btn-ghost px-2 py-1 text-sm" aria-label={t("kk.close.pdfNamed", { period })} onClick={() => pdf.mutate(c.id)}>
                    {t("kk.close.pdf")}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ErrorText error={pdf.error} />
    </section>
  );
}
