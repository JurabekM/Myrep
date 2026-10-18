import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkEmployeeDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { AgreementFileActions, AgreementStatus, EndForm, PhoneFields, SignForm, TemplateReviewNote } from "./KkAgreementParts";

type Mode = "SIGN" | "ADVANCE" | "PAY" | "EDIT" | "END";

/**
 * Xodimlar (kasbkor/SPEC 7.2): `EMPLOYMENT` kelishuvi (9 savol), imzolangan versiyalar, foizsiz va
 * jarimasiz avans, haq to'lovi, oylik hisob varaqchasi. Hisob yadroda; UI faqat ko'rsatadi.
 */
export function KkStaffScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const staff = useQuery({ queryKey: keys.kkStaff(spaceId), queryFn: () => call(commands.kkStaff(spaceId)) });
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<{ id: string; mode: Mode } | null>(null);
  const s = staff.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.staff.title")}</h1>
      <p className="text-ink-muted">{t("kk.staff.intro")}</p>
      <TemplateReviewNote status={s?.templateReview} />
      <ErrorText error={staff.error} />
      {s && (
        <section aria-label={t("kk.staff.totals")} className="grid gap-5 md:grid-cols-2">
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.staff.owed")}</p>
            <p data-testid="kk-staff-owed" className="kpi text-accent">
              {s.owed.formatted}
            </p>
            <p className="text-xs text-ink-muted">{t("kk.staff.owedHint")}</p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.staff.advances")}</p>
            <p data-testid="kk-staff-advances" className="text-2xl font-semibold tabular-nums">
              {s.advancesOutstanding.formatted}
            </p>
            <p className="text-xs text-ink-muted">{t("kk.staff.advancesHint")}</p>
          </div>
        </section>
      )}
      <div>
        <button className={adding ? "btn-ghost" : "btn-primary"} aria-expanded={adding} onClick={() => setAdding((v) => !v)}>
          {t("kk.staff.add")}
        </button>
      </div>
      {adding && <EmployeeForm spaceId={spaceId} onDone={() => setAdding(false)} />}
      <section className="flex flex-col gap-4" aria-label={t("kk.staff.list")}>
        <h2 className="text-lg font-semibold">{t("kk.staff.list")}</h2>
        {s?.employees.length === 0 && <p className="text-sm text-ink-muted">{t("kk.staff.empty")}</p>}
        {s?.employees.map((e) => (
          <EmployeeCard
            key={e.id}
            spaceId={spaceId}
            e={e}
            open={open?.id === e.id ? open.mode : null}
            onToggle={(m) => setOpen(open?.id === e.id && open.mode === m ? null : { id: e.id, mode: m })}
            onDone={() => setOpen(null)}
          />
        ))}
      </section>
    </section>
  );
}

function EmployeeCard({ spaceId, e, open, onToggle, onDone }: { spaceId: string; e: KkEmployeeDto; open: Mode | null; onToggle: (m: Mode) => void; onDone: () => void }) {
  const { t } = useTranslation();
  const slip = useMutation({ mutationFn: (month: string) => call(commands.exportKkPayslip(spaceId, e.id, month)) });
  const a = e.agreement;
  const active = a.status !== "ENDED";
  const signed = a.signedVersions > 0;
  const rows: [string, string, string?][] = [
    [t("kk.staff.salary"), e.terms.salary.formatted],
    [t("kk.staff.payDayRow"), t("kk.staff.payDayValue", { day: e.terms.payDay })],
    [t("kk.staff.dueNow"), e.dueNow.formatted, "kk-employee-due"],
    [t("kk.staff.balance"), e.balance.formatted],
    [t("kk.staff.advances"), e.advancesOutstanding.formatted],
  ];
  const action = (m: Mode, label: string) => (
    <button key={m} className={open === m ? "btn-primary" : "btn-ghost"} aria-expanded={open === m} onClick={() => onToggle(m)}>
      {label}
    </button>
  );
  return (
    <article data-testid={`kk-employee-${e.name}`} aria-label={e.name} className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">
          {e.name}
          {e.terms.role && <span className="ml-2 text-sm font-normal text-ink-muted">{e.terms.role}</span>}
        </h3>
        <AgreementStatus state={a} testId="kk-employee-status" />
      </div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([label, value, id]) => (
            <tr key={label} className="border-t border-line">
              <th scope="row" className="py-1 pr-3 text-left font-normal">
                {label}
              </th>
              <td data-testid={id} className="py-1 text-right tabular-nums">
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div role="group" aria-label={t("kk.agr.actions", { name: e.name })} className="flex flex-wrap gap-2">
        {a.canSign && action("SIGN", t("kk.agr.sign"))}
        {signed && active && action("ADVANCE", t("kk.staff.advance"))}
        {signed && action("PAY", t("kk.staff.pay"))}
        {active && action("EDIT", t("kk.agr.edit"))}
        {signed && active && action("END", t("kk.staff.end"))}
        <AgreementFileActions spaceId={spaceId} id={e.id} name={e.name} state={a} />
      </div>
      {open === "SIGN" && <SignForm spaceId={spaceId} id={e.id} name={e.name} state={a} onDone={onDone} />}
      {open === "ADVANCE" && <AdvanceForm spaceId={spaceId} e={e} onDone={onDone} />}
      {open === "PAY" && <PayForm spaceId={spaceId} e={e} onDone={onDone} />}
      {open === "EDIT" && <EmployeeForm spaceId={spaceId} e={e} onDone={onDone} />}
      {open === "END" && <EndForm spaceId={spaceId} id={e.id} name={e.name} onDone={onDone} />}
      {e.months.length > 0 && signed && (
        <details>
          <summary className="cursor-pointer text-sm text-ink-muted">{t("kk.staff.months")}</summary>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.staff.col.period")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.staff.salary")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.staff.col.deducted")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.staff.col.paid")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.staff.col.balance")}</th>
                <th className="py-1 font-normal">
                  <span className="sr-only">{t("kk.staff.slip")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {e.months.map((m) => (
                <tr key={m.periodStart} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">
                    {showDate(m.periodStart)} — {showDate(m.periodEnd)}
                  </td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.salary.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.deducted.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.paid.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.balance.formatted}</td>
                  <td className="py-1 text-right">
                    <button className="btn-ghost px-2 py-1 text-sm" aria-label={t("kk.staff.slipNamed", { period: showDate(m.periodStart) })} onClick={() => slip.mutate(m.periodStart)}>
                      {t("kk.staff.slip")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <ErrorText error={slip.error} />
        </details>
      )}
      {e.advances.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm text-ink-muted">{t("kk.staff.advanceList", { count: e.advances.length })}</summary>
          <ul className="mt-2 flex flex-col gap-1 text-sm">
            {e.advances.map((x) => (
              <li key={x.id}>
                {t("kk.staff.advanceLine", {
                  date: showDate(x.givenOn),
                  amount: x.amount.formatted,
                  n: x.installments,
                  outstanding: x.outstanding.formatted,
                })}
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

function WalletPicker({ value, onChange, legend }: { value: "CASH" | "CARD"; onChange: (w: "CASH" | "CARD") => void; legend: string }) {
  const { t } = useTranslation();
  return (
    <fieldset>
      <legend className="label">{legend}</legend>
      <div className="flex gap-2">
        {(["CASH", "CARD"] as const).map((w) => (
          <button key={w} type="button" aria-pressed={value === w} className={value === w ? "btn-primary" : "btn-ghost"} onClick={() => onChange(w)}>
            {t(`kk.wallet.${w}`)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function AdvanceForm({ spaceId, e, onDone }: { spaceId: string; e: KkEmployeeDto; onDone: () => void }) {
  const { t } = useTranslation();
  const hint = useId();
  const [amount, setAmount] = useState("");
  const [n, setN] = useState("1");
  const [startOn, setStartOn] = useState("");
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CASH");
  const [on, setOn] = useState("");
  const save = useMutation({
    mutationFn: () =>
      call(commands.kkStaffAdvance(spaceId, e.id, { amount, installments: Number.parseInt(n, 10), startOn: startOn || null, wallet, occurredOn: on || null, note: null })),
    onSuccess: onDone,
  });
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    save.mutate();
  };
  const max = e.terms.maxAdvanceInstallments;
  return (
    <form className="flex flex-col gap-3 rounded-md border border-line p-3" aria-label={t("kk.staff.advanceTitle", { name: e.name })} onSubmit={submit}>
      <p id={hint} className="text-sm text-ink-muted">
        {e.terms.maxAdvance ? t("kk.staff.advanceRule", { max: e.terms.maxAdvance.formatted, n: max }) : t("kk.staff.advanceRuleNoLimit", { n: max })}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <label>
          <span className="label">{t("kk.staff.amount")}</span>
          <AmountInput value={amount} onChange={(ev) => setAmount(ev.target.value)} aria-describedby={hint} required />
        </label>
        <label>
          <span className="label">{t("kk.staff.installments")}</span>
          <select className="field" value={n} onChange={(ev) => setN(ev.target.value)}>
            {Array.from({ length: max }, (_, i) => String(i + 1)).map((v) => (
              <option key={v} value={v}>
                {t("kk.staff.installmentsValue", { n: v })}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">{t("kk.staff.startOn")}</span>
          <input type="date" className="field" value={startOn} onChange={(ev) => setStartOn(ev.target.value)} />
        </label>
        <label>
          <span className="label">{t("kk.date")}</span>
          <input type="date" className="field" value={on} onChange={(ev) => setOn(ev.target.value)} />
        </label>
        <WalletPicker value={wallet} onChange={setWallet} legend={t("kk.staff.fromWallet")} />
      </div>
      <ErrorText error={save.error} />
      <button className="btn-primary self-start" disabled={save.isPending}>
        {t("kk.staff.advanceSave")}
      </button>
    </form>
  );
}

function PayForm({ spaceId, e, onDone }: { spaceId: string; e: KkEmployeeDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState(e.dueNow.minor === "0" ? "" : e.dueNow.plain);
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CARD");
  const [on, setOn] = useState("");
  const save = useMutation({
    mutationFn: () => call(commands.kkStaffPay(spaceId, e.id, { amount: amount.trim() || null, wallet, occurredOn: on || null, note: null })),
    onSuccess: onDone,
  });
  return (
    <form
      className="flex flex-col gap-3 rounded-md border border-line p-3"
      aria-label={t("kk.staff.payTitle", { name: e.name })}
      onSubmit={(ev) => {
        ev.preventDefault();
        save.mutate();
      }}
    >
      <div className="flex flex-wrap items-end gap-3">
        <label>
          <span className="label">{t("kk.staff.amount")}</span>
          <AmountInput value={amount} onChange={(ev) => setAmount(ev.target.value)} />
        </label>
        <WalletPicker value={wallet} onChange={setWallet} legend={t("kk.staff.fromWallet")} />
        <label>
          <span className="label">{t("kk.date")}</span>
          <input type="date" className="field" value={on} onChange={(ev) => setOn(ev.target.value)} />
        </label>
      </div>
      <ErrorText error={save.error} />
      <button className="btn-primary self-start" disabled={save.isPending}>
        {t("common.save")}
      </button>
    </form>
  );
}

function EmployeeForm({ spaceId, e, onDone }: { spaceId: string; e?: KkEmployeeDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({
    name: e?.name ?? "",
    role: e?.terms.role ?? "",
    phone: e?.phone ?? "",
    consent: !!e?.phone,
    duties: e?.terms.duties ?? "",
    hours: e?.terms.hours ?? "",
    salary: e?.terms.salary.plain ?? "",
    payDay: String(e?.terms.payDay ?? 5),
    noticeDays: String(e?.terms.noticeDays ?? 14),
    maxAdvance: e?.terms.maxAdvance?.plain ?? "",
    maxInstallments: String(e?.terms.maxAdvanceInstallments ?? 3),
    startedOn: e?.agreement.startedOn ?? "",
    opening: e && e.terms.openingBalance.minor !== "0" ? e.terms.openingBalance.plain : "",
    arbiter: e?.terms.arbiter ?? "",
    reviewOn: e?.agreement.reviewOn ?? "",
  });
  const set = (k: keyof typeof f) => (ev: { target: { value: string } }) => setF({ ...f, [k]: ev.target.value });
  const save = useMutation({
    mutationFn: () => {
      const input = {
        name: f.name,
        role: f.role.trim() || null,
        phone: f.phone.trim() || null,
        phoneConsent: f.consent,
        duties: f.duties.trim() || null,
        hours: f.hours.trim() || null,
        salary: f.salary,
        payDay: Number.parseInt(f.payDay, 10) || 0,
        noticeDays: Number.parseInt(f.noticeDays, 10) || 0,
        maxAdvance: f.maxAdvance.trim() || null,
        maxAdvanceInstallments: Number.parseInt(f.maxInstallments, 10) || null,
        startedOn: f.startedOn || null,
        openingBalance: f.opening.trim() || null,
        arbiter: f.arbiter.trim() || null,
        reviewOn: f.reviewOn || null,
        note: e?.terms.note ?? null,
      };
      return call(e ? commands.kkUpdateEmployee(spaceId, e.id, input) : commands.kkAddEmployee(spaceId, input));
    },
    onSuccess: onDone,
  });
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={e ? t("kk.agr.editTitle", { name: e.name }) : t("kk.staff.add")} onSubmit={submit}>
      <p className="text-sm text-ink-muted md:col-span-2">{t("kk.staff.formHint")}</p>
      <label>
        <span className="label">{t("kk.staff.name")}</span>
        <input className="field" value={f.name} onChange={set("name")} required />
      </label>
      <label>
        <span className="label">{t("kk.staff.role")}</span>
        <input className="field" value={f.role} onChange={set("role")} />
      </label>
      <PhoneFields phone={f.phone} consent={f.consent} onPhone={(v) => setF({ ...f, phone: v })} onConsent={(v) => setF({ ...f, consent: v })} />
      <label className="md:col-span-2">
        <span className="label">{t("kk.staff.duties")}</span>
        <textarea className="field min-h-16" value={f.duties} onChange={set("duties")} />
      </label>
      <label className="md:col-span-2">
        <span className="label">{t("kk.staff.hours")}</span>
        <input className="field" value={f.hours} onChange={set("hours")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.salary")}</span>
        <AmountInput value={f.salary} onChange={set("salary")} required />
      </label>
      <label>
        <span className="label">{t("kk.staff.payDay")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.payDay} onChange={set("payDay")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.maxAdvance")}</span>
        <AmountInput value={f.maxAdvance} onChange={set("maxAdvance")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.maxInstallments")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.maxInstallments} onChange={set("maxInstallments")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.noticeDays")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.noticeDays} onChange={set("noticeDays")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.startedOn")}</span>
        <input type="date" className="field" value={f.startedOn} disabled={!!e && e.agreement.signedVersions > 0} onChange={set("startedOn")} />
      </label>
      <label>
        <span className="label">{t("kk.staff.opening")}</span>
        <AmountInput value={f.opening} onChange={set("opening")} />
      </label>
      <label>
        <span className="label">{t("kk.agr.arbiter")}</span>
        <input className="field" value={f.arbiter} onChange={set("arbiter")} />
      </label>
      <label>
        <span className="label">{t("kk.agr.reviewOn")}</span>
        <input type="date" className="field" value={f.reviewOn} onChange={set("reviewOn")} />
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={save.isPending}>
        {e ? t("common.save") : t("kk.staff.addButton")}
      </button>
    </form>
  );
}
