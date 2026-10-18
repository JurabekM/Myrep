import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfOverviewDto, type MfSettingsDto, type MoneyDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";
import { MfEntryDialog, type MfEntryMode } from "./MfEntryDialog";
import { MfTermsCard } from "./MfTermsCard";
import { PurposesTable } from "./TwoShoresScreen";

const ACTIONS: MfEntryMode[] = ["SALARY", "EXPENSE", "SENT_HOME", "FUND_IN", "FUND_OUT", "OTHER_INCOME", "OPENING", "FUND_OPENING"];
const CURRENCIES = ["KRW", "RUB", "KZT", "TRY", "USD", "EUR", "GBP", "UZS"] as const;

/**
 * Musofir bosh sahifasi (musofir/SPEC 1–4): 1-raqam — «Qaytish jamg'armasi» (ish valyutasida va kurs
 * bilan uy valyutasida), 2-raqam — «Shu oy o'z ulushi». Hamma summa va prognoz yadrodan tayyor.
 */
export function MfHomeScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const o = useQuery({ queryKey: keys.mf(spaceId), queryFn: () => call(commands.mfOverview(spaceId, null)) });
  const d = o.error ? undefined : o.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("space.MUSOFIR")}</h1>
      <ErrorText error={o.error} />
      {d && !d.settings && <SetupCard spaceId={spaceId} overview={d} />}
      {d?.settings && <Dashboard spaceId={spaceId} d={d} s={d.settings} />}
    </section>
  );
}

function SetupCard({ spaceId, overview, current, onDone }: { spaceId: string; overview: MfOverviewDto; current?: MfSettingsDto; onDone?: () => void }) {
  const { t } = useTranslation();
  const [country, setCountry] = useState(current?.country ?? "");
  const [currency, setCurrency] = useState(current?.workCurrency ?? "KRW");
  const [share, setShare] = useState(current?.sharePercent ?? overview.defaultSharePercent);
  const [target, setTarget] = useState(current?.target?.plain ?? "");
  const [returnOn, setReturnOn] = useState(current?.returnOn ?? "");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.mfSetSettings(spaceId, {
          country: country.trim() || null,
          workCurrency: currency,
          sharePercent: share,
          target: target.trim() || null,
          returnOn: returnOn || null,
        }),
      ),
    onSuccess: () => onDone?.(),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={t("mf.setup.title")} onSubmit={submit}>
      <div className="md:col-span-2">
        <h2 className="text-lg font-semibold">{t("mf.setup.title")}</h2>
        {!current && <p className="text-sm text-ink-muted">{t("mf.setup.intro")}</p>}
      </div>
      <label>
        <span className="label">{t("mf.setup.country")}</span>
        <input className="field" value={country} onChange={(e) => setCountry(e.target.value)} />
      </label>
      <label>
        <span className="label">{t("mf.setup.currency")}</span>
        <select className="field" value={currency} disabled={current?.currencyLocked} onChange={(e) => setCurrency(e.target.value)}>
          {CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {t(`mf.currency.${c}`)}
            </option>
          ))}
        </select>
      </label>
      <div>
        <label>
          <span className="label">{t("mf.setup.share")}</span>
          <input className="field tabular-nums" inputMode="decimal" value={share} onChange={(e) => setShare(e.target.value)} aria-describedby="mf-share-hint" required />
        </label>
        <p id="mf-share-hint" className="mt-1 text-xs text-ink-muted">
          {t("mf.setup.shareHint")}
        </p>
      </div>
      <div>
        <label>
          <span className="label">{t("mf.setup.target")}</span>
          <AmountInput value={target} onChange={(e) => setTarget(e.target.value)} aria-describedby="mf-target-hint" />
        </label>
        <p id="mf-target-hint" className="mt-1 text-xs text-ink-muted">
          {t("mf.setup.targetHint")}
        </p>
      </div>
      <label>
        <span className="label">{t("mf.setup.returnOn")}</span>
        <input type="date" className="field" value={returnOn} onChange={(e) => setReturnOn(e.target.value)} />
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <div className="flex gap-2 md:col-span-2">
        <button className="btn-primary" disabled={save.isPending}>
          {t("common.save")}
        </button>
        {onDone && current && (
          <button type="button" className="btn-ghost" onClick={onDone}>
            {t("common.cancel")}
          </button>
        )}
      </div>
    </form>
  );
}

function Line({ label, value, hint, testId, strong }: { label: string; value: string; hint?: string | null; testId?: string; strong?: boolean }) {
  return (
    <tr className={`border-t border-line ${strong ? "font-semibold" : ""}`}>
      <th scope="row" className="py-1 pr-3 text-left font-normal">
        {strong ? <span className="font-semibold">{label}</span> : label}
      </th>
      <td className="py-1 pr-3 text-right text-xs text-ink-muted tabular-nums">{hint ?? ""}</td>
      <td data-testid={testId} className="py-1 text-right tabular-nums">
        {value}
      </td>
    </tr>
  );
}

function Dashboard({ spaceId, d, s }: { spaceId: string; d: MfOverviewDto; s: MfSettingsDto }) {
  const { t } = useTranslation();
  const mfEntry = useUi((x) => x.mfEntry);
  const openMfEntry = useUi((x) => x.openMfEntry);
  const closeMfEntry = useUi((x) => x.closeMfEntry);
  const [offer, setOffer] = useState<MoneyDto | null>(null);
  const [fundAmount, setFundAmount] = useState<string | undefined>(undefined);
  const [editing, setEditing] = useState(false);
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)) });
  const m = d.month;
  const f = d.fund;
  const pct = (p: string | null) => (p === null ? null : `${p} %`);
  const category = (id: string | null) => {
    const c = categories.data?.find((x) => x.id === id);
    return c ? (c.customName ?? t(c.nameKey)) : "";
  };
  const rateLine = d.rate && !d.rate.identity ? t("mf.rateLine", { from: d.rate.fromCurrency, rate: d.rate.rate, to: d.rate.toCurrency, date: showDate(d.rate.rateOn) }) : null;

  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <div className="card">
          <p className="text-sm text-ink-muted">{t("mf.fund.title")}</p>
          <p data-testid="mf-fund" className="kpi text-accent">
            {f?.balance.formatted ?? "…"}
          </p>
          {f?.balanceHome ? (
            <p data-testid="mf-fund-home" className="text-sm">
              ≈ {f.balanceHome.formatted}
              {rateLine && <span className="block text-xs text-ink-muted">{rateLine}</span>}
            </p>
          ) : (
            <p className="text-sm text-ink-muted">{t("mf.noRateHome")}</p>
          )}
        </div>
        <div className="card">
          <p className="text-sm text-ink-muted">{t("mf.share.title", { percent: s.sharePercent })}</p>
          <p data-testid="mf-share" className="kpi text-accent">
            {m?.fundNet.formatted ?? "…"}
          </p>
          {m && (
            <p className="text-sm text-ink-muted">
              {t("mf.share.target", { amount: m.shareTarget.formatted })}
              {m.shareGap.minor !== "0" && (
                <span data-testid="mf-share-gap" className="block text-warn">
                  {t("mf.share.gap", { amount: m.shareGap.formatted })}
                </span>
              )}
            </p>
          )}
        </div>
      </div>

      {offer && (
        <div role="status" data-testid="mf-offer" className="card flex flex-wrap items-center justify-between gap-3 border-accent/60 py-3">
          <p>{t("mf.offer", { amount: offer.formatted })}</p>
          <div className="flex gap-2">
            <button
              className="btn-primary"
              onClick={() => {
                setFundAmount(offer.plain);
                setOffer(null);
                openMfEntry("FUND_IN");
              }}
            >
              {t("mf.offerAccept")}
            </button>
            <button className="btn-ghost" onClick={() => setOffer(null)}>
              {t("mf.offerLater")}
            </button>
          </div>
        </div>
      )}

      {m && m.warnings.length > 0 && (
        <div className="flex flex-col gap-2">
          {m.warnings.map((w) => (
            <p key={w} role="note" data-testid={`mf-warning-${w}`} className="card border-warn py-3 text-sm">
              {t(`mf.warning.${w}`, { amount: m.shareGap.formatted })}
            </p>
          ))}
        </div>
      )}

      {f && (
        <section className="card flex flex-col gap-3" aria-label={t("mf.prognosis.title")}>
          <h2 className="text-lg font-semibold">{t("mf.prognosis.title")}</h2>
          <p data-testid="mf-fund-status" className={f.status === "BEHIND" || f.status === "NO_SAVING" ? "text-warn" : f.status === "REACHED" || f.status === "ON_TRACK" ? "text-accent-text" : "text-ink-muted"}>
            {t(`mf.fund.status.${f.status}`, {
              months: f.monthsToTarget ?? 0,
              shortfall: f.shortfallAtReturn?.formatted ?? "",
            })}
          </p>
          {f.target && f.progressBp !== null && (
            <div>
              <div className="h-2 w-full overflow-hidden rounded bg-line" role="progressbar" aria-label={t("mf.prognosis.progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(f.progressBp / 100)}>
                <div className="h-full bg-accent" style={{ width: `${f.progressBp / 100}%` }} />
              </div>
              <p className="mt-1 text-xs text-ink-muted">{t("mf.prognosis.progressLine", { percent: f.progressPercent, target: f.target.formatted })}</p>
            </div>
          )}
          <table className="w-full text-sm">
            <tbody>
              {f.target && <Line label={t("mf.prognosis.target")} value={f.target.formatted} />}
              {f.remainingHome && <Line label={t("mf.prognosis.remaining")} value={f.remainingHome.formatted} />}
              <Line
                label={t("mf.prognosis.avg", { count: f.monthsUsed })}
                value={f.avgMonthly ? f.avgMonthly.formatted : t("mf.prognosis.noHistory")}
                hint={f.avgMonthlyHome ? `≈ ${f.avgMonthlyHome.formatted}` : null}
              />
              {f.monthsToTarget !== null && f.monthsToTarget > 0 && <Line label={t("mf.prognosis.monthsToTarget")} value={t("mf.months", { count: f.monthsToTarget })} testId="mf-months-to-target" />}
              {s.returnOn && <Line label={t("mf.prognosis.returnOn", { date: showDate(s.returnOn) })} value={t("mf.months", { count: f.monthsUntilReturn ?? 0 })} />}
              {f.projectedHome && <Line label={t("mf.prognosis.projected")} value={f.projectedHome.formatted} testId="mf-projected" strong />}
              {f.shortfallAtReturn && f.shortfallAtReturn.minor !== "0" && <Line label={t("mf.prognosis.shortfall")} value={f.shortfallAtReturn.formatted} testId="mf-shortfall" />}
            </tbody>
          </table>
        </section>
      )}

      {m && (
        <section className="card flex flex-col gap-2" aria-label={t("mf.flow.title")}>
          <h2 className="text-lg font-semibold">
            {t("mf.flow.title")}
            <span className="ml-2 text-sm font-normal text-ink-muted">{t("kk.period", { from: showDate(d.periodStart), to: showDate(d.periodEnd) })}</span>
          </h2>
          <table className="w-full text-sm">
            <tbody>
              <Line label={t("mf.flow.income")} value={m.income.formatted} testId="mf-income" />
              <Line label={t("mf.flow.expenses")} value={`− ${m.expenses.formatted}`} hint={pct(m.expensesPercent)} />
              <Line label={t("mf.flow.sentHome")} value={`− ${m.sentHome.formatted}`} hint={pct(m.sentPercent)} testId="mf-sent" />
              {m.fees.minor !== "0" && <Line label={t("mf.flow.fees")} value={`− ${m.fees.formatted}`} />}
              <Line label={t("mf.flow.fund")} value={`− ${m.fundNet.formatted}`} hint={pct(m.fundPercent)} />
              <Line label={t("mf.flow.pocket")} value={m.pocket.formatted} testId="mf-pocket" strong />
            </tbody>
          </table>
          <p className="text-xs text-ink-muted">{t("mf.flow.hint")}</p>
        </section>
      )}

      <ShoresSummary spaceId={spaceId} />
      <MfTermsCard spaceId={spaceId} />

      <div className="grid gap-5 md:grid-cols-2">
        <RateCard spaceId={spaceId} d={d} s={s} />
        <section className="card flex flex-col gap-2" aria-label={t("mf.setup.summary")}>
          <h2 className="text-lg font-semibold">{t("mf.setup.summary")}</h2>
          {editing ? (
            <SetupCard spaceId={spaceId} overview={d} current={s} onDone={() => setEditing(false)} />
          ) : (
            <>
              <p className="text-sm">
                {[s.country, t(`mf.currency.${s.workCurrency}`)].filter(Boolean).join(" · ")}
              </p>
              <p className="text-sm text-ink-muted">{t("mf.setup.summaryLine", { percent: s.sharePercent })}</p>
              <button className="btn-ghost self-start" onClick={() => setEditing(true)}>
                {t("mf.setup.edit")}
              </button>
            </>
          )}
        </section>
      </div>

      <div role="group" aria-label={t("kk.actions")} className="flex flex-wrap gap-2">
        {ACTIONS.map((a, i) => (
          <button
            key={a}
            className={i === 0 ? "btn-primary" : "btn-ghost"}
            onClick={() => {
              setFundAmount(undefined);
              openMfEntry(a);
            }}
          >
            {t(`mf.action.${a}`)}
            {i === 0 && <kbd className="text-xs">Ctrl+N</kbd>}
          </button>
        ))}
      </div>

      <section className="card flex flex-col gap-2" aria-label={t("kk.entries")}>
        <h2 className="text-lg font-semibold">{t("kk.entries")}</h2>
        {d.entries.length === 0 && <p className="text-sm text-ink-muted">{t("kk.noEntries")}</p>}
        {d.entries.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-ink-muted">
                <tr>
                  <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                  <th className="py-1 pr-3 font-normal">{t("kk.col.kind")}</th>
                  <th className="py-1 pr-3 font-normal">{t("kk.col.note")}</th>
                  <th className="py-1 text-right font-normal">{t("kk.col.amount")}</th>
                </tr>
              </thead>
              <tbody>
                {d.entries.map((e) => (
                  <tr key={e.id} data-testid="mf-entry" className="border-t border-line">
                    <td className="py-1 pr-3 tabular-nums">{showDate(e.occurredOn)}</td>
                    <td className="py-1 pr-3">{t(`mf.kind.${e.kind}`)}</td>
                    <td className="py-1 pr-3 text-ink-muted">
                      {[
                        category(e.categoryId),
                        e.fee ? t("mf.feeShort", { amount: e.fee.formatted }) : "",
                        e.received ? t("mf.receivedShort", { amount: e.received.formatted }) : "",
                        e.note,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </td>
                    <td className={`py-1 text-right tabular-nums ${e.kind === "SALARY" || e.kind === "OTHER_INCOME" ? "text-accent-text" : ""}`}>{e.amount.formatted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {mfEntry && (
        <MfEntryDialog
          spaceId={spaceId}
          mode={mfEntry}
          workCurrency={s.workCurrency}
          homeCurrency={s.homeCurrency}
          initialAmount={mfEntry === "FUND_IN" ? fundAmount : undefined}
          onClose={closeMfEntry}
          onIncome={(r) => setOffer(r.suggestedShare.minor !== "0" ? r.suggestedShare : null)}
        />
      )}
    </>
  );
}

/** «Ikki qirg'oq» xulosasi: uyda maqsadlar qoldig'i (uy tomoni yozuvlari fayl orqali keladi). */
function ShoresSummary({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const v = useQuery({ queryKey: keys.mfTwoShores(spaceId), queryFn: () => call(commands.mfTwoShores(spaceId)) });
  const d = v.error ? undefined : v.data;
  if (!d || d.remittances.length === 0) return null;
  return (
    <section className="card flex flex-col gap-2" aria-label={t("mf.shores.summary")}>
      <h2 className="text-lg font-semibold">
        {t("mf.shores.summary")}
        {d.pending > 0 && <span className="ml-2 text-sm font-normal text-warn">{t("mf.shores.pending", { count: d.pending })}</span>}
      </h2>
      <PurposesTable v={d} />
      {d.overspent && <p className="text-sm text-warn">{t("mf.shores.overspent")}</p>}
    </section>
  );
}

function RateCard({ spaceId, d, s }: { spaceId: string; d: MfOverviewDto; s: MfSettingsDto }) {
  const { t } = useTranslation();
  const [rate, setRate] = useState("");
  const [rateOn, setRateOn] = useState("");
  const [source, setSource] = useState("");
  const save = useMutation({
    mutationFn: () => call(commands.mfSetRate(spaceId, { rate, rateOn: rateOn || null, source: source.trim() || null })),
    onSuccess: () => {
      setRate("");
      setSource("");
    },
  });
  if (d.rate?.identity) {
    return (
      <section className="card flex flex-col gap-2" aria-label={t("mf.rate.title")}>
        <h2 className="text-lg font-semibold">{t("mf.rate.title")}</h2>
        <p className="text-sm text-ink-muted">{t("mf.rate.identity")}</p>
      </section>
    );
  }
  return (
    <form
      className="card flex flex-col gap-3"
      aria-label={t("mf.rate.title")}
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <h2 className="text-lg font-semibold">{t("mf.rate.title")}</h2>
      {d.rate ? (
        <p data-testid="mf-rate" className={d.rate.stale ? "text-warn" : ""}>
          {t("mf.rateLine", { from: d.rate.fromCurrency, rate: d.rate.rate, to: d.rate.toCurrency, date: showDate(d.rate.rateOn) })}
          {d.rate.source && <span className="text-ink-muted"> · {d.rate.source}</span>}
          {d.rate.stale && <span className="block text-sm">{t("mf.rate.stale")}</span>}
        </p>
      ) : (
        <p className="text-sm text-ink-muted">{t("mf.rate.none")}</p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <label>
          <span className="label">{t("mf.rate.input", { from: s.workCurrency, to: s.homeCurrency })}</span>
          <input className="field tabular-nums" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("kk.date")}</span>
          <input type="date" className="field" value={rateOn} onChange={(e) => setRateOn(e.target.value)} />
        </label>
      </div>
      <label>
        <span className="label">{t("mf.rate.source")}</span>
        <input className="field" value={source} onChange={(e) => setSource(e.target.value)} />
      </label>
      <p className="text-xs text-ink-muted">{t("mf.rate.hint")}</p>
      <ErrorText error={save.error} />
      <button className="btn-ghost self-start" disabled={save.isPending}>
        {t("mf.rate.save")}
      </button>
    </form>
  );
}
