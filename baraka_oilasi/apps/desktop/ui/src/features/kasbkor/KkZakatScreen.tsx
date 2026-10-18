import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkGrowthSettingsDto, type KkZakatDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

/** `1448-06-09` → «9 jumodul oxir 1448». */
function useHijri() {
  const { t } = useTranslation();
  return (s: string) => {
    const [y, m, d] = s.split("-").map((x) => Number.parseInt(x, 10));
    return t("kk.hijri.date", { day: d, month: t(`kk.hijri.m${m}`), year: y });
  };
}

/**
 * Zakot hisobi (kasbkor/SPEC 8.3) — **hisob, fatvo emas**. Diniy izoh faqat ulamo tasdiqlagan bo'lsa
 * (yadro `religiousNote` beradi). «Zakot kuni» — hijriy sana, jadvalli kalendar (±1–2 kun).
 */
export function KkZakatScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const settings = useQuery({ queryKey: keys.kkGrowthSettings(spaceId), queryFn: () => call(commands.kkGrowthSettings(spaceId)) });
  const [hopeless, setHopeless] = useState<string[]>([]);
  const [hawl, setHawl] = useState<boolean | null>(null);
  const input = { goldPrice: null, nisabGrams: null, valuation: null, hopelessSaleIds: hopeless, hawlComplete: hawl };
  const draft = useQuery({ queryKey: keys.kkZakat(spaceId, JSON.stringify(input)), queryFn: () => call(commands.kkZakatDraft(spaceId, input)) });
  const history = useQuery({ queryKey: keys.kkZakatHistory(spaceId), queryFn: () => call(commands.kkZakatHistory(spaceId)) });
  const save = useMutation({ mutationFn: () => call(commands.kkSaveZakat(spaceId, input)) });
  const hijri = useHijri();
  const z = draft.error ? undefined : draft.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.zakat.title")}</h1>
      <p role="note" className="card border-warn py-3 text-sm text-warn">
        {t("kk.zakat.disclaimer")}
      </p>
      {z?.religiousNote && <p className="text-sm text-ink-muted">{t(z.religiousNote)}</p>}
      {settings.data && <ZakatSettings spaceId={spaceId} s={settings.data} />}
      <ErrorText error={draft.error} />
      {z && (
        <>
          <Calculation z={z} hijri={hijri} />
          <section className="card flex flex-col gap-3" aria-label={t("kk.zakat.adjust")}>
            <h2 className="text-lg font-semibold">{t("kk.zakat.adjust")}</h2>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={z.hawlComplete} onChange={(e) => setHawl(e.target.checked)} />
              <span>
                {t("kk.zakat.hawl")}
                <span className="block text-xs text-ink-muted">
                  {z.hawlSince ? t(z.hawlSuggested ? "kk.zakat.hawlYes" : "kk.zakat.hawlNo", { date: showDate(z.hawlSince) }) : t("kk.zakat.hawlNoData")}
                </span>
              </span>
            </label>
            {z.receivableLines.some((r) => r.d90Plus) && (
              <fieldset className="flex flex-col gap-1">
                <legend className="label">{t("kk.zakat.hopeless")}</legend>
                {z.receivableLines
                  .filter((r) => r.d90Plus)
                  .map((r) => (
                    <label key={r.saleId} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={hopeless.includes(r.saleId)}
                        onChange={(e) => setHopeless(e.target.checked ? [...hopeless, r.saleId] : hopeless.filter((x) => x !== r.saleId))}
                      />
                      {t("kk.zakat.hopelessLine", { customer: r.customer, item: r.item, amount: r.outstanding.formatted, days: r.overdueDays })}
                    </label>
                  ))}
              </fieldset>
            )}
            <div>
              <button className="btn-primary" disabled={save.isPending || !z.goldPrice} onClick={() => save.mutate()}>
                {t("kk.zakat.save")}
              </button>
              <ErrorText error={save.error} />
            </div>
          </section>
        </>
      )}
      {history.data && history.data.length > 0 && (
        <section className="card flex flex-col gap-2" aria-label={t("kk.zakat.history")}>
          <h2 className="text-lg font-semibold">{t("kk.zakat.history")}</h2>
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.zakat.base")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.zakat.nisab")}</th>
                <th className="py-1 text-right font-normal">{t("kk.zakat.amount")}</th>
              </tr>
            </thead>
            <tbody>
              {history.data.map((h) => (
                <tr key={h.id} className="border-t border-line">
                  <td className="py-1 pr-3">
                    {showDate(h.calculatedOn)} <span className="text-ink-muted">({hijri(h.hijriDate)})</span>
                  </td>
                  <td className="py-1 pr-3 text-right tabular-nums">{h.base.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{h.nisab.formatted}</td>
                  <td className="py-1 text-right tabular-nums">{h.reason ? t(`kk.zakat.reason.${h.reason}`) : h.zakat.formatted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
}

function Calculation({ z, hijri }: { z: KkZakatDto; hijri: (s: string) => string }) {
  const { t } = useTranslation();
  const rows: [string, string][] = [
    [t(`kk.zakat.stock.${z.valuation}`), z.stock.formatted],
    [t("kk.zakat.cash"), `+ ${z.cash.formatted}`],
    [t("kk.zakat.receivables"), `+ ${z.receivables.formatted}`],
    [t("kk.zakat.payables"), `− ${z.payables.formatted}`],
    [t("kk.zakat.wages"), `− ${z.wagesDue.formatted}`],
  ];
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.zakat.calc")}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("kk.zakat.calc")}</h2>
        <p className="text-sm text-ink-muted">
          {showDate(z.calculatedOn)} · {hijri(z.hijriDate)}
        </p>
      </div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label} className="border-t border-line">
              <th scope="row" className="py-1 pr-3 text-left font-normal">
                {label}
              </th>
              <td className="py-1 text-right tabular-nums">{value}</td>
            </tr>
          ))}
          <tr className="border-t border-line font-semibold">
            <th scope="row" className="py-1 pr-3 text-left">
              {t("kk.zakat.base")}
            </th>
            <td data-testid="kk-zakat-base" className="py-1 text-right tabular-nums">
              {z.base.formatted}
            </td>
          </tr>
          <tr className="border-t border-line">
            <th scope="row" className="py-1 pr-3 text-left font-normal">
              {t("kk.zakat.nisabLine", { grams: z.nisabGrams, price: z.goldPrice?.formatted ?? "—" })}
            </th>
            <td className="py-1 text-right tabular-nums">{z.nisab?.formatted ?? "—"}</td>
          </tr>
        </tbody>
      </table>
      <div className="rounded-md border border-line p-3">
        <p className="text-sm text-ink-muted">{t("kk.zakat.amountLong")}</p>
        <p data-testid="kk-zakat-amount" className="kpi text-accent">
          {z.zakat.formatted}
        </p>
        {z.reason && (
          <p role="note" className="text-sm text-warn">
            {t(`kk.zakat.reason.${z.reason}`)}
          </p>
        )}
      </div>
    </section>
  );
}

function ZakatSettings({ spaceId, s }: { spaceId: string; s: KkGrowthSettingsDto }) {
  const { t } = useTranslation();
  const hint = useId();
  const hijri = useHijri();
  const [f, setF] = useState({
    month: s.zakatMonth ? String(s.zakatMonth) : "",
    day: s.zakatDay ? String(s.zakatDay) : "",
    gold: s.goldPrice?.plain ?? "",
    grams: String(s.nisabGrams),
    valuation: s.stockValuation,
  });
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkSetGrowthSettings(spaceId, {
          reserveMonths: s.reserveMonths,
          maxBadPercent: s.maxBadPercent,
          zakatMonth: f.month ? Number.parseInt(f.month, 10) : null,
          zakatDay: f.month ? Number.parseInt(f.day, 10) || 1 : null,
          goldPrice: f.gold.trim() || null,
          nisabGrams: Number.parseInt(f.grams, 10) || 0,
          stockValuation: f.valuation,
          scaleReminder: s.scaleReminder,
        }),
      ),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={t("kk.zakat.settings")} onSubmit={submit}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 md:col-span-2">
        <h2 className="text-lg font-semibold">{t("kk.zakat.settings")}</h2>
        <p className="text-sm text-ink-muted">{t("kk.zakat.today", { date: hijri(s.todayHijri) })}</p>
      </div>
      <fieldset className="flex flex-wrap items-end gap-3 md:col-span-2" aria-describedby={hint}>
        <legend className="label">{t("kk.zakat.day")}</legend>
        <label>
          <span className="label">{t("kk.zakat.month")}</span>
          <select className="field" value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })}>
            <option value="">{t("kk.zakat.notSet")}</option>
            {MONTHS.map((m) => (
              <option key={m} value={String(m)}>
                {t(`kk.hijri.m${m}`)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">{t("kk.zakat.dayOfMonth")}</span>
          <input className="field w-24 tabular-nums" inputMode="numeric" value={f.day} onChange={(e) => setF({ ...f, day: e.target.value })} />
        </label>
        <p id={hint} className="w-full text-xs text-ink-muted">
          {s.nextZakatDay ? t("kk.zakat.next", { date: showDate(s.nextZakatDay) }) : t("kk.zakat.dayHint")}
        </p>
      </fieldset>
      <label>
        <span className="label">{t("kk.zakat.gold")}</span>
        <AmountInput value={f.gold} onChange={(e) => setF({ ...f, gold: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("kk.zakat.grams")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.grams} onChange={(e) => setF({ ...f, grams: e.target.value })} />
      </label>
      <label className="md:col-span-2">
        <span className="label">{t("kk.zakat.valuation")}</span>
        <select className="field" value={f.valuation} onChange={(e) => setF({ ...f, valuation: e.target.value })}>
          <option value="REPLACEMENT">{t("kk.zakat.stock.REPLACEMENT")}</option>
          <option value="BOOK">{t("kk.zakat.stock.BOOK")}</option>
        </select>
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={save.isPending}>
        {t("common.save")}
      </button>
    </form>
  );
}
