import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import { type BudgetModeDto, commands, type PlannerDebtDto, type SellableItemDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { BalanceChart } from "../../components/BalanceChart";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { showDate, showMonth } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

/**
 * «Qarzdan chiqish» (uy/SPEC 2D.1, 2D.2, 2D.7, 2D.9): 70/20/10 rejimi, odatiy va qoʻshimcha
 * toʻlovli prognoz, yopish tartibi, «Qarzsiz kun» va sotiladigan buyumlar. Barcha hisob — yadroda.
 */
export function PayoffScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [extra, setExtra] = useState("");
  const [applied, setApplied] = useState<string | null>(null);
  const mode = useQuery({ queryKey: keys.budget(spaceId), queryFn: () => call(commands.budgetMode(spaceId)) });
  const plan = useQuery({
    queryKey: keys.planner(spaceId, applied),
    queryFn: () => call(commands.payoffPlanner(spaceId, { extraPerMonth: applied })),
  });
  const p = plan.data;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setApplied(extra.trim() === "" ? null : extra);
  };

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("payoff.title")}</h1>
      {mode.data && <ModeCard spaceId={spaceId} mode={mode.data} />}
      <ErrorText error={mode.error ?? plan.error} />

      {p && p.debts.length === 0 && <p className="card text-ink-muted">{t("payoff.noDebts")}</p>}
      {p && p.debts.length > 0 && (
        <>
          <form className="card flex flex-wrap items-end gap-3" onSubmit={submit}>
            <label className="min-w-64">
              <span className="label">{t("payoff.extra")}</span>
              <AmountInput placeholder={p.extraPerMonth.plain} value={extra} onChange={(e) => setExtra(e.target.value)} />
            </label>
            <button className="btn-primary">{t("payoff.calculate")}</button>
            <p className="w-full text-sm text-ink-muted">{t(`payoff.source.${p.extraSource}`, { amount: p.extraPerMonth.formatted })}</p>
          </form>

          <div className="grid gap-3 md:grid-cols-3">
            <Kpi label={t("payoff.debtFreeBase")}>
              {p.base.payoffDate ? showDate(p.base.payoffDate) : "—"}
              <Sub>{t("payoff.months", { count: p.base.months })}</Sub>
            </Kpi>
            <Kpi label={t("payoff.debtFreeFast")} accent>
              {p.accelerated.payoffDate ? showDate(p.accelerated.payoffDate) : "—"}
              <Sub>{t("payoff.earlier", { count: p.monthsSaved })}</Sub>
            </Kpi>
            <Kpi label={t("payoff.saved")} accent>
              {p.netSaved.formatted}
              <Sub>
                {p.accelerated.fees.minor === "0"
                  ? t("payoff.savedInterest", { interest: p.interestSaved.formatted })
                  : t("payoff.savedDetail", { interest: p.interestSaved.formatted, fees: p.accelerated.fees.formatted })}
              </Sub>
            </Kpi>
          </div>
          {p.excludedForeign > 0 && <p className="text-sm text-ink-muted">{t("payoff.foreign", { count: p.excludedForeign })}</p>}

          <div className="card"><BalanceChart points={p.timeline} /></div>
          <OrderList spaceId={spaceId} debts={p.debts} />
          <details className="card">
            <summary className="cursor-pointer font-medium">{t("payoff.table")}</summary>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm tabular-nums">
                <thead className="text-left text-ink-muted">
                  <tr>
                    <th className="py-1 pr-3 font-normal">{t("loan.col.month")}</th>
                    <th className="py-1 pr-3 text-right font-normal">{t("payoff.col.due")}</th>
                    <th className="py-1 pr-3 text-right font-normal">{t("loan.col.interest")}</th>
                    <th className="py-1 pr-3 text-right font-normal">{t("loan.col.extra")}</th>
                    <th className="py-1 pr-3 text-right font-normal">{t("payoff.col.fee")}</th>
                    <th className="py-1 text-right font-normal">{t("loan.col.balance")}</th>
                  </tr>
                </thead>
                <tbody>
                  {p.schedule.map((r) => (
                    <tr key={r.month} className="border-t border-line">
                      <td className="py-1 pr-3">{showMonth(r.month)}</td>
                      <td className="py-1 pr-3 text-right">{r.due.formatted}</td>
                      <td className="py-1 pr-3 text-right">{r.interest.formatted}</td>
                      <td className="py-1 pr-3 text-right">{r.extra.formatted}</td>
                      <td className="py-1 pr-3 text-right">{r.fee.formatted}</td>
                      <td className="py-1 text-right">{r.balance.formatted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <p className="text-xs text-ink-muted">{t("loan.estimate")}</p>
        </>
      )}
      <Items spaceId={spaceId} debts={p?.debts ?? []} />
    </section>
  );
}

function Kpi({ label, accent, children }: { label: string; accent?: boolean; children: ReactNode }) {
  return (
    <div className="card min-w-0">
      <p className="label">{label}</p>
      <div className={`text-xl font-semibold tabular-nums [overflow-wrap:anywhere] ${accent ? "text-accent" : ""}`}>{children}</div>
    </div>
  );
}

function Sub({ children }: { children: ReactNode }) {
  return <span className="block text-sm font-normal text-ink-muted">{children}</span>;
}

/** Foiz (butun son) → bp. Pul emas; notoʻgʻri qiymat yadroga yuborilmaydi. */
const toBp = (v: string) => {
  if (!/^\d{1,3}$/.test(v.trim())) throw new CoreError({ code: "INVALID_NUMBER", field: null });
  return Number(v.trim()) * 100;
};

function ModeCard({ spaceId, mode: m }: { spaceId: string; mode: BudgetModeDto }) {
  const { t } = useTranslation();
  const [split, setSplit] = useState({ h: m.householdPercent, e: m.extraDebtPercent, s: m.savingsPercent });
  const save = useMutation({
    mutationFn: (mode: string) =>
      call(commands.setBudgetMode(spaceId, { mode, householdBp: toBp(split.h), extraDebtBp: toBp(split.e), savingsBp: toBp(split.s) })),
  });
  const recovery = m.mode === "DEBT_RECOVERY";
  return (
    <div className="card flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t(`mode.${m.mode}`)}</h2>
        {m.changedOn && <span className="text-xs text-ink-muted">{t("mode.since", { date: showDate(m.changedOn) })}</span>}
      </div>
      {m.suggested && <p role="note" className="rounded-md border border-warn p-3 text-sm">{t("mode.suggest")}</p>}
      <p className="text-sm text-ink-muted">{t("mode.why")}</p>
      <div className="grid gap-3 md:grid-cols-3">
        <Part label={t("mode.household")} value={split.h} onChange={(h) => setSplit({ ...split, h })} amount={m.household.formatted}>
          {t("mode.mandatory", { amount: m.mandatoryDebtPayments.formatted })}
          {m.householdShort && <span className="block text-danger">{t("mode.short")}</span>}
        </Part>
        <Part label={t("mode.extra")} value={split.e} onChange={(e) => setSplit({ ...split, e })} amount={m.extraDebt.formatted} />
        <Part label={t("mode.savings")} value={split.s} onChange={(s) => setSplit({ ...split, s })} amount={m.savings.formatted}>
          {t("mode.savingsMin")}
        </Part>
      </div>
      {!m.monthlyIncome && <p className="text-sm text-ink-muted">{t("debts.loadUnknown")}</p>}
      <ErrorText error={save.error} />
      <div className="flex flex-wrap gap-2">
        {(recovery || m.hasActiveDebt) && (
          <button className="btn-primary" disabled={save.isPending} onClick={() => save.mutate("DEBT_RECOVERY")}>
            {recovery ? t("common.save") : t("mode.enable")}
          </button>
        )}
        {recovery && (
          <button className="btn-ghost" disabled={save.isPending} onClick={() => save.mutate("STANDARD")}>
            {t("mode.disable")}
          </button>
        )}
      </div>
    </div>
  );
}

function Part({ label, value, onChange, amount, children }: { label: string; value: string; onChange: (v: string) => void; amount: string; children?: ReactNode }) {
  return (
    <div className="rounded-md border border-line p-3">
      <label className="flex items-center gap-2">
        <span className="label mb-0 flex-1">{label}</span>
        <input className="field w-16 text-right tabular-nums" inputMode="numeric" aria-label={`${label}, %`} value={value} onChange={(e) => onChange(e.target.value)} />
        <span className="text-ink-muted">%</span>
      </label>
      <p className="mt-2 text-lg font-semibold tabular-nums">{amount}</p>
      {children && <p className="text-xs text-ink-muted">{children}</p>}
    </div>
  );
}

function OrderList({ spaceId, debts }: { spaceId: string; debts: PlannerDebtDto[] }) {
  const { t } = useTranslation();
  const order = useMutation({ mutationFn: (ids: string[]) => call(commands.setDebtOrder(spaceId, ids)) });
  const reset = useMutation({ mutationFn: () => call(commands.resetDebtOrder(spaceId)) });
  const move = (i: number, d: -1 | 1) => {
    const ids = debts.map((x) => x.id);
    const j = i + d;
    const a = ids[i];
    const b = ids[j];
    if (a === undefined || b === undefined) return;
    ids[i] = b;
    ids[j] = a;
    order.mutate(ids);
  };
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="order-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="order-title" className="text-lg font-semibold">{t("payoff.order")}</h2>
        {debts.some((d) => d.manualOrder) && (
          <button className="btn-ghost px-3 py-1 text-sm" onClick={() => reset.mutate()}>{t("payoff.orderReset")}</button>
        )}
      </div>
      <p className="text-sm text-ink-muted">{t("payoff.orderHint")}</p>
      <ol className="flex flex-col gap-2">
        {debts.map((d, i) => (
          <li key={d.id} className="grid items-center gap-2 border-b border-line pb-2 text-sm md:grid-cols-[2rem_1fr_auto_auto]">
            <span className="text-lg font-semibold text-accent-text">{d.order}</span>
            <span>
              <span className="font-medium">{d.creditor}</span>
              {d.isRibo && <span className="ml-2 rounded border border-danger px-2 py-0.5 text-xs text-danger">{t("debts.ribo")}</span>}
              <span className="block text-ink-muted tabular-nums">
                {d.balance.formatted} · {d.basePayoff ? showDate(d.basePayoff) : "—"} → {d.acceleratedPayoff ? showDate(d.acceleratedPayoff) : "—"}
                {d.monthsSaved > 0 && ` · ${t("payoff.earlier", { count: d.monthsSaved })}`}
                {d.fees.minor !== "0" && ` · ${t("payoff.feesShort", { amount: d.fees.formatted })}`}
              </span>
            </span>
            <button className="btn-ghost px-2 py-1 text-xs" aria-label={t("payoff.up", { name: d.creditor })} disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
            <button className="btn-ghost px-2 py-1 text-xs" aria-label={t("payoff.down", { name: d.creditor })} disabled={i === debts.length - 1} onClick={() => move(i, 1)}>↓</button>
          </li>
        ))}
      </ol>
      <ErrorText error={order.error ?? reset.error} />
    </section>
  );
}

function Items({ spaceId, debts }: { spaceId: string; debts: PlannerDebtDto[] }) {
  const { t } = useTranslation();
  const items = useQuery({ queryKey: keys.items(spaceId), queryFn: () => call(commands.sellableItems(spaceId)) });
  const [title, setTitle] = useState("");
  const [estimated, setEstimated] = useState("");
  const add = useMutation({
    mutationFn: () => call(commands.addSellableItem(spaceId, { title, estimated, currency: "UZS" })),
    onSuccess: () => {
      setTitle("");
      setEstimated("");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="items-title">
      <h2 id="items-title" className="text-lg font-semibold">{t("items.title")}</h2>
      <p className="text-sm text-ink-muted">{t("items.intro")}</p>
      <ul className="flex flex-col gap-2">
        {(items.data ?? []).map((i) => <Item key={i.id} spaceId={spaceId} item={i} debts={debts} />)}
      </ul>
      <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
        <label className="min-w-56 flex-1">
          <span className="label">{t("items.name")}</span>
          <input className="field text-lg" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("items.estimated")}</span>
          <AmountInput value={estimated} onChange={(e) => setEstimated(e.target.value)} required />
        </label>
        <button className="btn-ghost">{t("goals.add")}</button>
      </form>
      <ErrorText error={items.error ?? add.error} />
    </section>
  );
}

function Item({ spaceId, item: i, debts }: { spaceId: string; item: SellableItemDto; debts: PlannerDebtDto[] }) {
  const { t } = useTranslation();
  const afterRepayment = useUi((s) => s.afterRepayment);
  const [open, setOpen] = useState(false);
  const [price, setPrice] = useState(i.estimated.plain);
  const [debtId, setDebtId] = useState(debts[0]?.id ?? "");
  const sell = useMutation({
    mutationFn: () => call(commands.sellItem(spaceId, i.id, { price, date: null, debtId: debtId === "" ? null : debtId })),
    onSuccess: (r) => {
      setOpen(false);
      if (r.repayment) afterRepayment(r.repayment);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    sell.mutate();
  };
  const sold = i.status === "SOLD";
  return (
    <li className="flex flex-col gap-2 border-b border-line pb-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span>
          <span className="font-medium">{i.title}</span>
          <span className="ml-2 text-ink-muted tabular-nums">
            {sold ? t("items.sold", { amount: i.sold?.formatted ?? "", date: showDate(i.soldOn ?? "") }) : t("items.listed", { amount: i.estimated.formatted })}
          </span>
        </span>
        {!sold && <button className="btn-ghost px-3 py-1 text-sm" onClick={() => setOpen((v) => !v)}>{t("items.sell")}</button>}
      </div>
      {open && (
        <form className="flex flex-wrap items-end gap-3 rounded-md border border-line p-3" onSubmit={submit}>
          <label>
            <span className="label">{t("items.price")}</span>
            <AmountInput value={price} onChange={(e) => setPrice(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("items.toDebt")}</span>
            <select className="field text-lg" value={debtId} onChange={(e) => setDebtId(e.target.value)}>
              {debts.map((d) => <option key={d.id} value={d.id}>{d.creditor}</option>)}
              <option value="">{t("items.noDebt")}</option>
            </select>
          </label>
          <button className="btn-primary" disabled={sell.isPending}>{t("common.save")}</button>
          <div className="w-full"><ErrorText error={sell.error} /></div>
        </form>
      )}
    </li>
  );
}
