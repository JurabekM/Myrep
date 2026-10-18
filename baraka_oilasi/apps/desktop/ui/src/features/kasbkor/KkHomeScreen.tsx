import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkOverviewDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";
import { type EntryMode, KkEntryDialog } from "./KkEntryDialog";
import { KkSalaryDialog } from "./KkSalaryDialog";

const ACTIONS: EntryMode[] = ["SALE", "EXPENSE", "OWNER_DRAW", "OWNER_CONTRIBUTION", "TRANSFER", "OPENING"];

/**
 * Kasb-kor bosh sahifasi (kasbkor/SPEC 1, 2): 2-raqam — «Egasiga to'langan maosh»; pul oqimi
 * (haqiqiy foyda — K2), maosh kartasi, naqd kassa va karta, shu oy yozuvlari.
 */
export function KkHomeScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const o = useQuery({ queryKey: keys.kk(spaceId), queryFn: () => call(commands.kkOverview(spaceId, null)) });
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)) });
  const kkEntry = useUi((s) => s.kkEntry);
  const openKkEntry = useUi((s) => s.openKkEntry);
  const closeKkEntry = useUi((s) => s.closeKkEntry);
  const setScreen = useUi((s) => s.setScreen);
  const [salaryOpen, setSalaryOpen] = useState(false);
  const d = o.data;
  const category = (id: string | null) => {
    const c = categories.data?.find((x) => x.id === id);
    return c ? (c.customName ?? t(c.nameKey)) : "";
  };

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("space.KASBKOR")}</h1>
      {d?.closeDue && (
        <div data-testid="kk-close-due" className="card flex flex-wrap items-center justify-between gap-3 border-accent/60 py-3">
          <p>{t("kk.closeDue", { date: showDate(d.closeDue) })}</p>
          <button className="btn-primary" onClick={() => setScreen("kkClose")}>
            {t("kk.close.open")}
          </button>
        </div>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <div className="card">
          <p className="text-sm text-ink-muted">{t("kk.trueProfit")}</p>
          <p data-testid="kk-true-profit" className="kpi text-accent">
            {d?.profit.trueProfit.formatted ?? "…"}
          </p>
          {d && (
            <p className="text-sm text-ink-muted">
              {t("kk.visibleProfitLine", { amount: d.profit.visibleProfit.formatted })}
            </p>
          )}
        </div>
        <div className="card">
          <p className="text-sm text-ink-muted">{t("kk.ownerPaid")}</p>
          <p data-testid="kk-owner-paid" className="kpi text-accent">
            {d?.ownerPaid.formatted ?? "…"}
          </p>
          {d && (
            <p className="text-sm text-ink-muted">
              {t("kk.ownerPaidSplit", { salary: d.ownerSalaryTransferred.formatted, draws: d.ownerDraws.formatted })}
            </p>
          )}
        </div>
      </div>

      {d && <ProfitCard spaceId={spaceId} overview={d} />}

      <SalaryCard spaceId={spaceId} onPay={() => setSalaryOpen(true)} />

      <section aria-label={t("kk.wallets")} className="grid gap-5 md:grid-cols-2">
        <div className="card">
          <p className="text-sm text-ink-muted">{t("kk.cashFlow")}</p>
          <p data-testid="kk-cash-flow" className="text-2xl font-semibold tabular-nums">
            {d?.cashFlow.formatted ?? "…"}
          </p>
          {d && (
            <p className="text-sm text-ink-muted">
              {t("kk.cashFlowSplit", { revenue: d.revenue.formatted, expenses: d.expenses.formatted })}
            </p>
          )}
          <p className="mt-1 text-xs text-ink-muted">{t("kk.cashFlowHint")}</p>
          {d && d.stockPurchases.minor !== "0" && <p className="mt-1 text-xs text-ink-muted">{t("kk.stockPurchasesLine", { amount: d.stockPurchases.formatted })}</p>}
        </div>
        {(["CASH", "CARD"] as const).map((w) => {
          const bal = w === "CASH" ? d?.cash : d?.card;
          const negative = d?.negativeWallets.includes(w);
          return (
            <div key={w} className={`card ${negative ? "border-warn" : ""}`}>
              <p className="text-sm text-ink-muted">{t(`kk.wallet.${w}`)}</p>
              <p data-testid={`kk-wallet-${w}`} className="text-2xl font-semibold tabular-nums">
                {bal?.formatted ?? "…"}
              </p>
              {negative && (
                <p role="note" className="mt-1 text-sm text-warn">
                  {t("kk.negativeWallet")}
                </p>
              )}
            </div>
          );
        })}
      </section>

      {d && d.receivables.minor !== "0" && (
        <div className="card flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-ink-muted">{t("kk.receivables")}</p>
            <p data-testid="kk-receivables" className="text-2xl font-semibold tabular-nums">
              {d.receivables.formatted}
            </p>
            {d.receivablesOverdue.minor !== "0" && <p className="text-sm text-warn">{t("kk.receivablesOverdue", { amount: d.receivablesOverdue.formatted })}</p>}
          </div>
          <button className="btn-ghost" onClick={() => setScreen("kkCredit")}>
            {t("nav.kkCredit")}
          </button>
        </div>
      )}

      {d && (d.stockValue.minor !== "0" || d.stockFrozenCount > 0) && (
        <div className={`card flex flex-wrap items-center justify-between gap-3 ${d.stockFrozenCount > 0 ? "border-warn" : ""}`}>
          <div>
            <p className="text-sm text-ink-muted">{t("kk.stockValue")}</p>
            <p data-testid="kk-stock-value" className="text-2xl font-semibold tabular-nums">
              {d.stockValue.formatted}
            </p>
            {d.stockFrozenCount > 0 && (
              <p data-testid="kk-stock-frozen" className="text-sm text-warn">
                {t("kk.stockFrozen", { amount: d.stockFrozenValue.formatted, count: d.stockFrozenCount })}
              </p>
            )}
          </div>
          <button className="btn-ghost" onClick={() => setScreen("kkStock")}>
            {t("nav.kkStock")}
          </button>
        </div>
      )}

      <div role="group" aria-label={t("kk.actions")} className="flex flex-wrap gap-2">
        {ACTIONS.map((a, i) => (
          <button key={a} className={i === 0 ? "btn-primary" : "btn-ghost"} onClick={() => openKkEntry(a)}>
            {t(`kk.action.${a}`)}
            {i === 0 && <kbd className="text-xs">Ctrl+N</kbd>}
          </button>
        ))}
      </div>

      <section className="card flex flex-col gap-2" aria-label={t("kk.entries")}>
        <h2 className="text-lg font-semibold">
          {t("kk.entries")}
          {d && <span className="ml-2 text-sm font-normal text-ink-muted">{t("kk.period", { from: showDate(d.periodStart), to: showDate(d.periodEnd) })}</span>}
        </h2>
        {d && d.entries.length === 0 && <p className="text-sm text-ink-muted">{t("kk.noEntries")}</p>}
        {d && d.entries.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.col.kind")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.col.wallet")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.col.note")}</th>
                <th className="py-1 text-right font-normal">{t("kk.col.amount")}</th>
              </tr>
            </thead>
            <tbody>
              {d.entries.map((e) => (
                <tr key={e.id} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">{showDate(e.occurredOn)}</td>
                  <td className="py-1 pr-3">{t(`kk.kind.${e.kind}`)}</td>
                  <td className="py-1 pr-3">
                    {t(`kk.wallet.${e.wallet}`)}
                    {e.toWallet ? ` → ${t(`kk.wallet.${e.toWallet}`)}` : ""}
                  </td>
                  <td className="py-1 pr-3 text-ink-muted">{[category(e.categoryId), e.note].filter(Boolean).join(" · ")}</td>
                  <td className={`py-1 text-right tabular-nums ${e.kind === "SALE" ? "text-accent-text" : ""}`}>{e.amount.formatted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {kkEntry && <KkEntryDialog spaceId={spaceId} mode={kkEntry} onClose={closeKkEntry} />}
      {salaryOpen && d && <KkSalaryDialog spaceId={spaceId} overview={d} onClose={() => setSalaryOpen(false)} />}
    </section>
  );
}

/**
 * Haqiqiy foyda tarkibi (kasbkor/SPEC 3.1). Summalar yadrodan tayyor; UI faqat ko'rsatadi.
 * O'z mehnati bahosi egasi maoshi bilan yonma-yon.
 */
function ProfitCard({ spaceId, overview: d }: { spaceId: string; overview: KkOverviewDto }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const p = d.profit;
  const rows: [string, string, string?][] = [
    [t("kk.profit.revenue"), p.revenue.formatted],
    [t("kk.profit.cogs"), `− ${p.cogs.formatted}`, t("kk.profit.cogsHint")],
    [t("kk.profit.operating"), `− ${p.operatingExpenses.formatted}`],
    [t("kk.profit.visible"), p.visibleProfit.formatted],
    [t("kk.profit.ownerLabor"), p.ownerLabor ? `− ${p.ownerLabor.formatted}` : t("kk.profit.notSet")],
    [t("kk.profit.familyLabor"), `− ${p.familyLabor.formatted}`, p.familyLaborPaid.minor !== "0" ? t("kk.profit.familyPaid", { amount: p.familyLaborPaid.formatted }) : undefined],
    [t("kk.profit.depreciation"), `− ${p.depreciation.formatted}`],
  ];
  // Ortiqcha topilgan tovar (manfiy yo'qotish) foydaga qo'shiladi; faqat belgi almashadi.
  if (p.stockLosses.minor !== "0") rows.splice(2, 0, [t("kk.profit.stockLosses"), p.stockLosses.minor.startsWith("-") ? `+ ${p.stockLosses.formatted.slice(1)}` : `− ${p.stockLosses.formatted}`]);
  // Manfiy chiqib ketish — uskuna balansdan qimmatga sotilgan (foydaga qo'shiladi); faqat belgi almashadi.
  if (p.disposal.minor !== "0") rows.push([t("kk.profit.disposal"), p.disposal.minor.startsWith("-") ? `+ ${p.disposal.formatted.slice(1)}` : `− ${p.disposal.formatted}`]);
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.profit.title")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("kk.profit.title")}</h2>
        <button className="btn-ghost px-3 py-1 text-sm" onClick={() => setEditing((v) => !v)}>
          {p.ownerLabor ? t("kk.ownerLaborChange") : t("kk.ownerLaborSet")}
        </button>
      </div>
      {editing && <OwnerLaborForm spaceId={spaceId} current={p.ownerLabor?.plain ?? ""} onDone={() => setEditing(false)} />}
      {!p.ownerLabor && (
        <p role="note" className="text-sm text-warn">
          {t("kk.ownerLaborMissing")}
        </p>
      )}
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([label, value, hint]) => (
            <tr key={label} className="border-t border-line">
              <th scope="row" className="py-1 pr-3 text-left font-normal">
                {label}
                {hint && <span className="block text-xs text-ink-muted">{hint}</span>}
              </th>
              <td className="py-1 text-right tabular-nums">{value}</td>
            </tr>
          ))}
          <tr className="border-t border-line font-semibold">
            <th scope="row" className="py-1 pr-3 text-left">
              {t("kk.trueProfitShort")}
            </th>
            <td className="py-1 text-right tabular-nums">{p.trueProfit.formatted}</td>
          </tr>
        </tbody>
      </table>
      <p className="text-sm text-ink-muted">
        {t("kk.laborVsSalary", { labor: p.ownerLabor?.formatted ?? "—", salary: d.ownerSalary?.formatted ?? "—" })}
      </p>
    </section>
  );
}

function OwnerLaborForm({ spaceId, current, onDone }: { spaceId: string; current: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState(current);
  const [error, setError] = useState<unknown>(null);
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        call(commands.kkSetOwnerLabor(spaceId, amount)).then(onDone, setError);
      }}
    >
      <div className="flex-1">
        <label>
          <span className="label">{t("kk.ownerLaborAmount")}</span>
          <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} aria-describedby="kk-owner-labor-hint" />
        </label>
        <p id="kk-owner-labor-hint" className="mt-1 text-xs text-ink-muted">
          {t("kk.ownerLaborHint")}
        </p>
      </div>
      <button className="btn-primary">{t("common.save")}</button>
      <div className="w-full">
        <ErrorText error={error} />
      </div>
    </form>
  );
}

function SalaryCard({ spaceId, onPay }: { spaceId: string; onPay: () => void }) {
  const { t } = useTranslation();
  const o = useQuery({ queryKey: keys.kk(spaceId), queryFn: () => call(commands.kkOverview(spaceId, null)) });
  const [editing, setEditing] = useState(false);
  const d = o.data;
  if (!d) return null;
  return (
    <section className="card flex flex-col gap-2" aria-label={t("kk.salary")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("kk.salary")}</h2>
        <button className="btn-ghost px-3 py-1 text-sm" onClick={() => setEditing((v) => !v)}>
          {d.ownerSalary ? t("kk.salaryChange") : t("kk.salarySet")}
        </button>
      </div>
      {editing && <SalaryForm spaceId={spaceId} current={d.ownerSalary?.plain ?? ""} onDone={() => setEditing(false)} />}
      {d.ownerSalary ? (
        <>
          <p>
            {t("kk.salaryMonthly", { amount: d.ownerSalary.formatted })} ·{" "}
            <span data-testid="kk-salary-remaining">{t("kk.salaryRemaining", { amount: d.salaryRemaining?.formatted ?? "" })}</span>
          </p>
          {d.salaryCarry && <p className="text-sm text-ink-muted">{t("kk.salaryCarry", { amount: d.salaryCarry.formatted })}</p>}
          {d.overdrawn && (
            <p role="note" className="text-sm text-warn">
              {t("kk.overdrawn", { amount: d.overdrawn.formatted })}
            </p>
          )}
          <button className="btn-primary self-start" onClick={onPay}>
            {t("kk.paySalary")}
          </button>
        </>
      ) : (
        <p className="text-sm text-ink-muted">{t("kk.salaryHint")}</p>
      )}
    </section>
  );
}

function SalaryForm({ spaceId, current, onDone }: { spaceId: string; current: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState(current);
  const [error, setError] = useState<unknown>(null);
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        call(commands.kkSetOwnerSalary(spaceId, amount)).then(onDone, setError);
      }}
    >
      <label className="flex-1">
        <span className="label">{t("kk.salaryAmount")}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} />
      </label>
      <button className="btn-primary">{t("common.save")}</button>
      <div className="w-full">
        <ErrorText error={error} />
      </div>
    </form>
  );
}
