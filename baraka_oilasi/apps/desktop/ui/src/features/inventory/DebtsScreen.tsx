import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  type BorrowCheckDto,
  type ContributorDto,
  type BorrowCheckInput,
  commands,
  type DebtDto,
  type GoalDto,
  type NewDebtInput,
  type PlanStatusDto,
  type ReceivableDto,
  type ScheduleLineInput,
} from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { BorrowCheckFields } from "../../components/BorrowCheckFields";
import { ErrorText } from "../../components/ErrorText";
import { ScheduleEditor } from "../../components/ScheduleEditor";
import { call, CoreError } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

const CREDITOR_TYPES = ["BANK", "SHOP", "RELATIVE", "FRIEND", "OTHER"] as const;
const PLAN_KINDS = ["MANUAL", "ANNUITY", "DIFFERENTIATED", "FIXED_MARKUP"] as const;

/**
 * Qarzlar roʻyxati — «yaraning hajmi» (uy/SPEC 2C.7, 2D.3, 2D.5, 2D.6). Barcha summalar,
 * foizlar, qoldiq va eslatmalar yadroda hisoblanadi; bu ekran faqat koʻrsatadi va soʻraydi.
 */
export function DebtsScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [adding, setAdding] = useState<null | "debt" | "receivable">(null);
  const overview = useQuery({ queryKey: keys.debts(spaceId), queryFn: () => call(commands.debtsOverview(spaceId)) });
  const o = overview.data;

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("debts.title")}</h1>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={() => setAdding("debt")}>{t("debts.addDebt")}</button>
          <button className="btn-ghost" onClick={() => setAdding("receivable")}>{t("debts.addReceivable")}</button>
        </div>
      </div>
      <ErrorText error={overview.error} />
      {o && (
        <div className="grid gap-3 md:grid-cols-3">
          <Kpi label={t("debts.total")}>
            {o.totalDebt.length === 0 ? t("debts.none") : o.totalDebt.map((m) => <span key={m.currency} className="block">{m.formatted}</span>)}
          </Kpi>
          <Kpi label={t("debts.load")} danger={o.loadHigh}>
            {o.loadPercent === null ? (
              <span className="text-base text-ink-muted">{t("debts.loadUnknown")}</span>
            ) : (
              <>
                {o.loadPercent}%
                <span className="block text-sm font-normal text-ink-muted">
                  {t("debts.loadOf", { due: o.monthlyDue.formatted, income: o.monthlyIncome?.formatted ?? "" })}
                </span>
              </>
            )}
            {o.loadExcludesForeign && <span className="block text-xs font-normal text-ink-muted">{t("debts.loadForeign")}</span>}
          </Kpi>
          <Kpi label={t("debts.receivableTotal")}>
            {o.totalReceivable.length === 0 ? t("debts.none") : o.totalReceivable.map((m) => <span key={m.currency} className="block">{m.formatted}</span>)}
          </Kpi>
        </div>
      )}
      {o?.hasRiboDebt && (
        <p role="note" className="rounded-md border border-danger p-3 text-sm text-danger">{t("debts.riboBanner")}</p>
      )}
      {adding === "debt" && <AddDebtForm spaceId={spaceId} onDone={() => setAdding(null)} />}
      {adding === "receivable" && <AddReceivableForm spaceId={spaceId} onDone={() => setAdding(null)} />}

      {o && (
        <>
          <h2 className="text-lg font-semibold">{t("debts.myDebts")}</h2>
          {o.debts.length === 0 && <p className="text-sm text-ink-muted">{t("debts.emptyDebts")}</p>}
          {o.debts.map((d) => <DebtCard key={d.id} spaceId={spaceId} debt={d} />)}
          <h2 className="text-lg font-semibold">{t("debts.receivables")}</h2>
          {o.receivables.length === 0 && <p className="text-sm text-ink-muted">{t("debts.emptyReceivables")}</p>}
          {o.receivables.map((r) => <ReceivableCard key={r.id} spaceId={spaceId} item={r} />)}
          <Goals spaceId={spaceId} goals={o.goals} />
        </>
      )}
    </section>
  );
}

function Kpi({ label, danger, children }: { label: string; danger?: boolean; children: ReactNode }) {
  return (
    <div className="card min-w-0">
      <p className="label">{label}</p>
      <div className={`text-xl font-semibold tabular-nums [overflow-wrap:anywhere] ${danger ? "text-danger" : "text-accent-text"}`}>{children}</div>
    </div>
  );
}

function Badge({ tone, children }: { tone: "danger" | "warn" | "muted"; children: ReactNode }) {
  const cls = { danger: "border-danger text-danger", warn: "border-warn text-warn", muted: "border-line text-ink-muted" }[tone];
  return <span className={`rounded border px-2 py-0.5 text-xs ${cls}`}>{children}</span>;
}

function StatusLine({ s, gentle }: { s: PlanStatusDto; gentle?: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-3 text-sm sm:grid-cols-3">
      <div>
        <p className="label">{t("debts.remaining")}</p>
        <p className="text-xl font-semibold tabular-nums text-accent-text">{s.remaining.formatted}</p>
      </div>
      {s.nextDue && (
        <div>
          <p className="label">{t("debts.nextDue")}</p>
          <p className="tabular-nums">{showDate(s.nextDue.date)} — {s.nextDue.amount.formatted}</p>
        </div>
      )}
      {s.reminder && (
        <div>
          <p className="label">{t("debts.reminder")}</p>
          <p className={s.reminder === "OVERDUE" ? "text-danger" : "text-warn"}>
            {t(`debts.reminder.${gentle ? "gentle." : ""}${s.reminder}`, { amount: s.overdue.formatted })}
          </p>
        </div>
      )}
    </div>
  );
}

function PlanDetails({ plan, payments }: { plan: DebtDto["plan"]; payments: DebtDto["payments"] }) {
  const { t } = useTranslation();
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-ink-muted">{t("debts.planAndPayments", { plan: plan.length, paid: payments.length })}</summary>
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        <ol className="flex flex-col gap-1 tabular-nums">
          {plan.map((l, i) => (
            <li key={i} className="flex justify-between border-b border-line py-1">
              <span>{showDate(l.date)}</span>
              <span>{l.amount.formatted}</span>
            </li>
          ))}
        </ol>
        <ul className="flex flex-col gap-1 tabular-nums">
          {payments.map((p) => (
            <li key={p.id} className="flex justify-between gap-3 border-b border-line py-1">
              <span>{showDate(p.date)}{p.isPrepayment ? ` · ${t("debts.prepayment")}` : ""}</span>
              <span>
                {p.amount.formatted}
                {p.journalShortCode && <code className="ml-2 text-xs text-ink-muted">{p.journalShortCode}</code>}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}

function DebtCard({ spaceId, debt: d }: { spaceId: string; debt: DebtDto }) {
  const { t } = useTranslation();
  const [paying, setPaying] = useState(false);
  const pdf = useMutation({ mutationFn: (agreementId: string) => call(commands.exportAgreementReceipt(spaceId, agreementId)) });
  const tc = d.trueCost;
  return (
    <article className="card flex flex-col gap-3" aria-label={d.creditor}>
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-semibold">{d.creditor}</h3>
        <Badge tone="muted">{t(`debts.creditor.${d.creditorType}`)}</Badge>
        {d.isRibo && <Badge tone="danger">{t("debts.ribo")}</Badge>}
        {d.status === "CLOSED" && <Badge tone="muted">{t("debts.closed")}</Badge>}
        {d.agreementId && <Badge tone="muted">{t("debts.withReceipt")}</Badge>}
        {d.reason && <span className="text-sm text-ink-muted">· {d.reason}</span>}
      </header>
      <StatusLine s={d.statusInfo} />
      <p className="text-sm">
        <span className="text-ink-muted">{t("debts.trueCost")}: </span>
        <span className="tabular-nums">
          {tc.originalPrincipal.formatted} → {tc.totalCost.formatted} →{" "}
          <span className={tc.overpay.minor === "0" ? "" : "text-danger"}>
            {t("debts.overpay", { amount: tc.overpay.formatted, percent: tc.overpayPercent })}
          </span>
        </span>
      </p>
      {tc.goalEquivalents.map((g) => (
        <p key={g.goalId} className="text-sm text-accent-text">{t("debts.goalEquivalent", { title: g.title, percent: g.percent })}</p>
      ))}
      {d.borrowWarnings.length > 0 && (
        <p className="text-xs text-ink-muted">
          {t("debts.checkedWith")}: {d.borrowWarnings.map((w) => t(`friction.warn.${w}`)).join(" · ")}
        </p>
      )}
      <PlanDetails plan={d.plan} payments={d.payments} />
      <div className="flex flex-wrap gap-2">
        {d.status === "ACTIVE" && (
          <button className="btn-ghost" onClick={() => setPaying((v) => !v)}>{t("debts.recordPayment")}</button>
        )}
        {d.agreementId && (
          <button className="btn-ghost" disabled={pdf.isPending} onClick={() => pdf.mutate(d.agreementId ?? "")}>{t("debts.receiptPdf")}</button>
        )}
      </div>
      <ErrorText error={pdf.error} />
      {paying && <PaymentForm spaceId={spaceId} ownerType="DEBT" id={d.id} contributors={d.contributors} onDone={() => setPaying(false)} />}
      {d.status === "ACTIVE" && <Contributors spaceId={spaceId} debtId={d.id} items={d.contributors} />}
    </article>
  );
}

function ReceivableCard({ spaceId, item: r }: { spaceId: string; item: ReceivableDto }) {
  const { t } = useTranslation();
  const [paying, setPaying] = useState(false);
  const pdf = useMutation({ mutationFn: (agreementId: string) => call(commands.exportAgreementReceipt(spaceId, agreementId)) });
  return (
    <article className="card flex flex-col gap-3" aria-label={r.debtor}>
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-semibold">{r.debtor}</h3>
        <Badge tone="muted">{t("debts.hasana")}</Badge>
        {r.status === "CLOSED" && <Badge tone="muted">{t("debts.closed")}</Badge>}
        <span className="text-sm text-ink-muted">· {r.amount.formatted}, {showDate(r.lentOn)}</span>
      </header>
      <StatusLine s={r.statusInfo} gentle />
      <PlanDetails plan={r.plan} payments={r.payments} />
      <div className="flex flex-wrap gap-2">
        {r.status === "ACTIVE" && <button className="btn-ghost" onClick={() => setPaying((v) => !v)}>{t("debts.recordReturn")}</button>}
        {r.agreementId && (
          <button className="btn-ghost" disabled={pdf.isPending} onClick={() => pdf.mutate(r.agreementId ?? "")}>{t("debts.receiptPdf")}</button>
        )}
      </div>
      <ErrorText error={pdf.error} />
      {paying && <PaymentForm spaceId={spaceId} ownerType="RECEIVABLE" id={r.id} contributors={[]} onDone={() => setPaying(false)} />}
    </article>
  );
}

function PaymentForm({
  spaceId,
  ownerType,
  id,
  contributors,
  onDone,
}: {
  spaceId: string;
  ownerType: "DEBT" | "RECEIVABLE";
  id: string;
  contributors: ContributorDto[];
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const afterRepayment = useUi((s) => s.afterRepayment);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [prepayment, setPrepayment] = useState(false);
  const [payer, setPayer] = useState("");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.recordRepayment(spaceId, ownerType, id, {
          amount,
          date: date.trim() === "" ? null : date,
          isPrepayment: prepayment,
          note: null,
          contributorId: payer === "" ? null : payer,
        }),
      ),
    onSuccess: (r) => {
      onDone();
      afterRepayment(r);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-wrap items-end gap-3 rounded-md border border-line p-3" onSubmit={submit}>
      <label>
        <span className="label">{t("common.amount")}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
      </label>
      <label>
        <span className="label">{t("debts.paidOn")}</span>
        <input className="field max-w-40 text-lg tabular-nums" inputMode="numeric" placeholder={t("debts.today")} value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      {contributors.length > 0 && (
        <label>
          <span className="label">{t("debts.payer")}</span>
          <select className="field text-lg" value={payer} onChange={(e) => setPayer(e.target.value)}>
            <option value="">{t("debts.payerSelf")}</option>
            {contributors.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
      )}
      {ownerType === "DEBT" && (
        <label className="flex items-center gap-2 pb-2">
          <input type="checkbox" checked={prepayment} onChange={(e) => setPrepayment(e.target.checked)} />
          {t("debts.prepayment")}
        </label>
      )}
      <button className="btn-primary" disabled={save.isPending}>{t("common.save")}</button>
      <div className="w-full"><ErrorText error={save.error} /></div>
    </form>
  );
}

/** Qarzni to'lashga yelkadoshlar (uy/SPEC 2D.4): oylik ulush va to'lagani. */
function Contributors({ spaceId, debtId, items }: { spaceId: string; debtId: string; items: ContributorDto[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [share, setShare] = useState("");
  const add = useMutation({
    mutationFn: () => call(commands.addContributor(spaceId, debtId, { name, monthlyShare: optional(share) })),
    onSuccess: () => {
      setName("");
      setShare("");
      setOpen(false);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <div className="flex flex-col gap-2 text-sm">
      {items.length > 0 && (
        <ul className="flex flex-col gap-1">
          {items.map((c) => (
            <li key={c.id} className="flex flex-wrap justify-between gap-2 text-ink-muted tabular-nums">
              <span>{c.name}{c.monthlyShare ? ` · ${t("debts.share", { amount: c.monthlyShare.formatted })}` : ""}</span>
              <span>{t("debts.contributorPaid", { amount: c.paid.formatted })}</span>
            </li>
          ))}
        </ul>
      )}
      {!open && <button className="self-start text-ink-muted underline" onClick={() => setOpen(true)}>{t("debts.addContributor")}</button>}
      {open && (
        <form className="flex flex-wrap items-end gap-3 rounded-md border border-line p-3" onSubmit={submit}>
          <label className="min-w-48 flex-1">
            <span className="label">{t("debts.contributorName")}</span>
            <input className="field text-lg" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("debts.contributorShare")}</span>
            <AmountInput value={share} onChange={(e) => setShare(e.target.value)} />
          </label>
          <button className="btn-ghost">{t("goals.add")}</button>
          <div className="w-full"><ErrorText error={add.error} /></div>
        </form>
      )}
    </div>
  );
}

const optional = (v: string) => (v.trim() === "" ? null : v);

function AddDebtForm({ spaceId, onDone }: { spaceId: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({
    creditorType: "RELATIVE",
    creditor: "",
    reason: "",
    principal: "",
    planKind: "MANUAL",
    annualBp: "2400",
    months: "12",
    firstDate: "",
    markup: "",
    original: "",
    paidBefore: "",
    terms: "",
    feeBp: "",
    isNew: false,
  });
  const [schedule, setSchedule] = useState<ScheduleLineInput[]>([{ date: "", amount: "" }]);
  const [check, setCheck] = useState<BorrowCheckInput>({ need: "NECESSITY", alternatives: [] });
  const [preview, setPreview] = useState<BorrowCheckDto | null>(null);
  // Har qanday oʻzgarishdan keyin «toʻxta va oʻyla» natijasi qayta soʻraladi.
  const set = (patch: Partial<typeof f>) => {
    setPreview(null);
    setF((v) => ({ ...v, ...patch }));
  };
  const bank = f.planKind === "ANNUITY" || f.planKind === "DIFFERENTIATED";
  const generated = f.planKind !== "MANUAL";

  const input = (): NewDebtInput => {
    // bp va oylar — pul emas, butun son; notoʻgʻri qiymat yadroga yuborilmaydi.
    if (
      (generated && (!/^\d+$/.test(f.months) || (bank && !/^\d+$/.test(f.annualBp)))) ||
      (f.feeBp.trim() !== "" && !/^\d+$/.test(f.feeBp.trim()))
    ) {
      throw new CoreError({ code: "INVALID_NUMBER", field: null });
    }
    return {
      creditorType: f.creditorType,
      creditor: f.creditor,
      reason: optional(f.reason),
      currency: "UZS",
      principal: f.principal,
      originalPrincipal: optional(f.original),
      paidBefore: optional(f.paidBefore),
      planKind: f.planKind,
      annualBp: bank ? Number(f.annualBp) : null,
      markup: bank ? null : optional(f.markup),
      months: generated ? Number(f.months) : null,
      firstDate: optional(f.firstDate),
      schedule: generated ? [] : schedule,
      earlyRepaymentTerms: optional(f.terms),
      prepaymentFeeBp: f.feeBp.trim() === "" ? null : Number(f.feeBp.trim()),
      isNew: f.isNew,
      borrowCheck: f.isNew ? check : null,
    };
  };
  const run = useMutation({
    mutationFn: async () => {
      const i = input();
      if (i.isNew && !preview) return { preview: await call(commands.previewBorrowCheck(spaceId, i)) };
      await call(commands.addDebt(spaceId, i));
      return { preview: null };
    },
    onSuccess: (r) => (r.preview ? setPreview(r.preview) : onDone()),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run.mutate();
  };

  return (
    <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("debts.addDebt")}>
      <label>
        <span className="label">{t("debts.creditorType")}</span>
        <select className="field" value={f.creditorType} onChange={(e) => set({ creditorType: e.target.value })}>
          {CREDITOR_TYPES.map((c) => <option key={c} value={c}>{t(`debts.creditor.${c}`)}</option>)}
        </select>
      </label>
      <label>
        <span className="label">{t("debts.creditorName")}</span>
        <input className="field" value={f.creditor} onChange={(e) => set({ creditor: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("debts.principal")}</span>
        <AmountInput value={f.principal} onChange={(e) => set({ principal: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("debts.reason")}</span>
        <input className="field" placeholder={t("debts.reasonHint")} value={f.reason} onChange={(e) => set({ reason: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("debts.planKind")}</span>
        <select className="field" value={f.planKind} onChange={(e) => set({ planKind: e.target.value })}>
          {PLAN_KINDS.map((k) => <option key={k} value={k}>{t(`debts.plan.${k}`)}</option>)}
        </select>
      </label>
      <label>
        <span className="label">{generated ? t("debts.firstPayment") : t("debts.startedOn")}</span>
        <input className="field tabular-nums" inputMode="numeric" placeholder={t("debts.today")} value={f.firstDate} onChange={(e) => set({ firstDate: e.target.value })} />
      </label>
      {bank && (
        <label>
          <span className="label">{t("loan.rateBp")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.annualBp} onChange={(e) => set({ annualBp: e.target.value })} />
        </label>
      )}
      {!bank && (
        <label>
          <span className="label">{t("debts.markup")}</span>
          <AmountInput value={f.markup} onChange={(e) => set({ markup: e.target.value })} required={f.planKind === "FIXED_MARKUP"} />
        </label>
      )}
      {generated && (
        <label>
          <span className="label">{t("loan.months")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.months} onChange={(e) => set({ months: e.target.value })} />
        </label>
      )}
      {(bank || f.markup.trim() !== "") && <p className="text-sm text-danger md:col-span-2">{t("debts.riboHint")}</p>}
      {!generated && (
        <ScheduleEditor
          value={schedule}
          onChange={(rows) => {
            setPreview(null);
            setSchedule(rows);
          }}
        />
      )}
      <details className="md:col-span-2">
        <summary className="cursor-pointer text-sm text-ink-muted">{t("debts.history")}</summary>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <label>
            <span className="label">{t("debts.original")}</span>
            <AmountInput value={f.original} onChange={(e) => set({ original: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("debts.paidBefore")}</span>
            <AmountInput value={f.paidBefore} onChange={(e) => set({ paidBefore: e.target.value })} />
          </label>
          {f.creditorType === "BANK" && (
            <>
              <label>
                <span className="label">{t("debts.terms")}</span>
                <input className="field" value={f.terms} onChange={(e) => set({ terms: e.target.value })} />
              </label>
              <label>
                <span className="label">{t("debts.feeBp")}</span>
                <input className="field tabular-nums" inputMode="numeric" placeholder="0" value={f.feeBp} onChange={(e) => set({ feeBp: e.target.value })} />
              </label>
            </>
          )}
        </div>
      </details>
      <label className="flex items-center gap-2 md:col-span-2">
        <input type="checkbox" checked={f.isNew} onChange={(e) => set({ isNew: e.target.checked })} />
        {t("debts.isNew")}
      </label>
      {f.isNew && (
        <BorrowCheckFields
          value={check}
          onChange={(v) => {
            setPreview(null);
            setCheck(v);
          }}
        />
      )}
      {preview && <FrictionResult preview={preview} />}
      <div className="md:col-span-2"><ErrorText error={run.error} /></div>
      <div className="flex gap-2">
        <button className="btn-primary" disabled={run.isPending}>
          {f.isNew && !preview ? t("friction.check") : preview ? t("friction.confirm") : t("common.save")}
        </button>
        <button type="button" className="btn-ghost" onClick={onDone}>{t("common.cancel")}</button>
      </div>
    </form>
  );
}

export function FrictionResult({ preview }: { preview: BorrowCheckDto }) {
  const { t } = useTranslation();
  return (
    <div role="status" className="rounded-md border border-warn p-4 text-sm md:col-span-2">
      <p className="mb-2 font-semibold text-accent-text">{t("mentor.name")}</p>
      <ul className="mb-2 flex list-disc flex-col gap-1 pl-5">
        {preview.warnings.map((w) => (
          <li key={w} className={w === "RIBO" ? "text-danger" : ""}>{t(`friction.warn.${w}`)}</li>
        ))}
        {preview.warnings.length === 0 && <li>{t("friction.allClear")}</li>}
      </ul>
      {preview.projectedLoadPercent !== null && <p>{t("friction.load", { percent: preview.projectedLoadPercent })}</p>}
      <p>{t("friction.cost", { total: preview.trueCost.totalCost.formatted, overpay: preview.trueCost.overpay.formatted })}</p>
      <p className="mt-2 text-ink-muted">{t("friction.notForbidden")}</p>
    </div>
  );
}

function AddReceivableForm({ spaceId, onDone }: { spaceId: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [debtor, setDebtor] = useState("");
  const [amount, setAmount] = useState("");
  const [lentOn, setLentOn] = useState("");
  const [note, setNote] = useState("");
  const [schedule, setSchedule] = useState<ScheduleLineInput[]>([{ date: "", amount: "" }]);
  const save = useMutation({
    mutationFn: () =>
      call(commands.addReceivable(spaceId, { debtor, currency: "UZS", amount, lentOn: optional(lentOn), schedule, note: optional(note) })),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("debts.addReceivable")}>
      <p className="text-sm text-ink-muted md:col-span-2">{t("debts.receivableIntro")}</p>
      <label>
        <span className="label">{t("debts.debtor")}</span>
        <input className="field" value={debtor} onChange={(e) => setDebtor(e.target.value)} required />
      </label>
      <label>
        <span className="label">{t("common.amount")}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
      </label>
      <label>
        <span className="label">{t("debts.lentOn")}</span>
        <input className="field tabular-nums" inputMode="numeric" placeholder={t("debts.today")} value={lentOn} onChange={(e) => setLentOn(e.target.value)} />
      </label>
      <label>
        <span className="label">{t("common.note")}</span>
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <ScheduleEditor value={schedule} onChange={setSchedule} />
      <div className="md:col-span-2"><ErrorText error={save.error} /></div>
      <div className="flex gap-2">
        <button className="btn-primary" disabled={save.isPending}>{t("common.save")}</button>
        <button type="button" className="btn-ghost" onClick={onDone}>{t("common.cancel")}</button>
      </div>
    </form>
  );
}

function Goals({ spaceId, goals }: { spaceId: string; goals: GoalDto[] }) {
  const { t } = useTranslation();
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("");
  const add = useMutation({
    mutationFn: () => call(commands.addGoal(spaceId, { title, target, currency: "UZS" })),
    onSuccess: () => {
      setTitle("");
      setTarget("");
    },
  });
  const remove = useMutation({ mutationFn: (id: string) => call(commands.deleteGoal(spaceId, id)) });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="goals-title">
      <h2 id="goals-title" className="text-lg font-semibold">{t("goals.title")}</h2>
      <p className="text-sm text-ink-muted">{t("goals.intro")}</p>
      <ul className="flex flex-col gap-1">
        {goals.map((g) => (
          <li key={g.id} className="flex items-center justify-between border-b border-line py-1 text-sm">
            <span>{g.title}</span>
            <span className="flex items-center gap-3 tabular-nums">
              {g.target.formatted}
              <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => remove.mutate(g.id)}>{t("receipt.removeLine")}</button>
            </span>
          </li>
        ))}
      </ul>
      <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
        <label className="min-w-56 flex-1">
          <span className="label">{t("goals.name")}</span>
          <input className="field text-lg" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("goals.target")}</span>
          <AmountInput value={target} onChange={(e) => setTarget(e.target.value)} required />
        </label>
        <button className="btn-ghost">{t("goals.add")}</button>
      </form>
      <ErrorText error={add.error ?? remove.error} />
    </section>
  );
}
