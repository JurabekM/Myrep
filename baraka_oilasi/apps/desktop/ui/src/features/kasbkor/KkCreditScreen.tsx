import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkCreditSaleDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const BUCKETS = ["current", "d1_30", "d31_60", "d61_90", "d90_plus"] as const;

/**
 * Nasiya daftari (kasbkor/SPEC 5.2): narx savdo paytida qotiriladi, kechikish uchun ustama yo'q.
 * Yosh guruhlari, haftalik ko'rik (eslatma matni nusxalanadi — ilova o'zi yubormaydi), yangi nasiya.
 */
export function KkCreditScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const book = useQuery({ queryKey: keys.kkCredit(spaceId), queryFn: () => call(commands.kkCreditBook(spaceId)) });
  const b = book.data;
  const review = b?.sales.filter((s) => s.status === "OVERDUE" || s.talkThisWeek) ?? [];
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.credit.title")}</h1>
      <p className="text-ink-muted">{t("kk.credit.intro")}</p>
      {b && (
        <section className="card flex flex-col gap-2" aria-label={t("kk.credit.aging")}>
          <h2 className="text-lg font-semibold">{t("kk.credit.aging")}</h2>
          <p className="kpi" data-testid="kk-credit-total">
            {b.aging.total.formatted}
          </p>
          <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-5">
            {BUCKETS.map((k) => (
              <div key={k}>
                <dt className="text-ink-muted">{t(`kk.credit.bucket.${k}`)}</dt>
                <dd data-testid={`kk-credit-${k}`} className={`tabular-nums ${k === "d90_plus" ? "text-warn" : ""}`}>
                  {b.aging[k].formatted}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {b && review.length > 0 && (
        <section className="card flex flex-col gap-3" aria-label={t("kk.credit.review")}>
          <h2 className="text-lg font-semibold">{t("kk.credit.review")}</h2>
          <p className="text-sm text-ink-muted">{t("kk.credit.reviewHint")}</p>
          {review.map((s) => (
            <ReviewItem key={s.id} spaceId={spaceId} s={s} />
          ))}
        </section>
      )}
      <NewSale spaceId={spaceId} />
      {b && b.sales.length > 0 && (
        <section className="flex flex-col gap-3" aria-label={t("kk.credit.list")}>
          <h2 className="text-lg font-semibold">{t("kk.credit.list")}</h2>
          {b.sales.map((s) => (
            <SaleCard key={s.id} spaceId={spaceId} s={s} />
          ))}
        </section>
      )}
    </section>
  );
}

function ReviewItem({ spaceId, s }: { spaceId: string; s: KkCreditSaleDto }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const mark = useMutation({ mutationFn: (talk: boolean) => call(commands.kkCreditMark(spaceId, s.id, talk)) });
  const text = t("kk.credit.reminder", { name: s.customerName, item: s.item, amount: s.nextDue?.amount.formatted ?? s.outstanding.formatted, date: showDate(s.nextDue?.date ?? "") });
  const copy = () => {
    void navigator.clipboard?.writeText(text).then(() => setCopied(true), () => setCopied(false));
  };
  return (
    <article className="flex flex-col gap-2 border-t border-line pt-3" aria-label={`${s.customerName}: ${s.item}`}>
      <p>
        <span className="font-medium">{s.customerName}</span> · {s.item} · {s.outstanding.formatted}
        {s.status === "OVERDUE" && <span className="ml-2 text-sm text-warn">{t("kk.credit.overdueDays", { n: s.overdueDays })}</span>}
        {s.customerPhone && <span className="ml-2 text-sm text-ink-muted">{s.customerPhone}</span>}
      </p>
      <label>
        <span className="label">{t("kk.credit.reminderLabel")}</span>
        <textarea className="field min-h-16 text-sm" readOnly value={text} />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-ghost px-3 py-1 text-sm" onClick={copy}>
          {copied ? t("kk.credit.copied") : t("kk.credit.copy")}
        </button>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={s.talkThisWeek} onChange={(e) => mark.mutate(e.target.checked)} />
          {t("kk.credit.talk")}
        </label>
      </div>
      <ErrorText error={mark.error} />
    </article>
  );
}

function NewSale({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const customers = useQuery({ queryKey: keys.kkCustomers(spaceId), queryFn: () => call(commands.kkCustomers(spaceId)) });
  const [open, setOpen] = useState(false);
  const [newCustomer, setNewCustomer] = useState(false);
  const empty = { customerId: "", item: "", cashPrice: "", creditPrice: "", installments: "3", soldOn: "", firstDue: "", witness: "", note: "" };
  const [f, setF] = useState(empty);
  const customerId = f.customerId || customers.data?.[0]?.id || "";
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkAddCreditSale(spaceId, {
          customerId,
          item: f.item,
          cashPrice: f.cashPrice.trim() || null,
          creditPrice: f.creditPrice,
          installments: Number.parseInt(f.installments, 10) || 0,
          soldOn: f.soldOn || null,
          firstDue: f.firstDue || null,
          witness: f.witness.trim() || null,
          note: f.note.trim() || null,
        }),
      ),
    onSuccess: () => {
      setF(empty);
      setOpen(false);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  if (!open) {
    return (
      <button className="btn-primary self-start" onClick={() => setOpen(true)}>
        {t("kk.credit.new")}
      </button>
    );
  }
  return (
    <section className="card flex flex-col gap-4" aria-label={t("kk.credit.new")}>
      <h2 className="text-lg font-semibold">{t("kk.credit.new")}</h2>
      <p className="text-sm text-ink-muted">{t("kk.credit.newHint")}</p>
      {(newCustomer || customers.data?.length === 0) && <NewCustomer spaceId={spaceId} onDone={(id) => (setNewCustomer(false), setF({ ...f, customerId: id }))} />}
      {customers.data && customers.data.length > 0 && (
        <form className="grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("kk.credit.saleForm")}>
          <div className="flex items-end gap-2 md:col-span-2">
            <label className="flex-1">
              <span className="label">{t("kk.credit.customer")}</span>
              <select className="field" value={customerId} onChange={(e) => setF({ ...f, customerId: e.target.value })}>
                {customers.data.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="btn-ghost" onClick={() => setNewCustomer(true)}>
              {t("kk.credit.addCustomer")}
            </button>
          </div>
          <label className="md:col-span-2">
            <span className="label">{t("kk.credit.item")}</span>
            <input className="field" value={f.item} onChange={(e) => setF({ ...f, item: e.target.value })} required />
          </label>
          <label>
            <span className="label">{t("kk.credit.cashPrice")}</span>
            <AmountInput value={f.cashPrice} onChange={(e) => setF({ ...f, cashPrice: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("kk.credit.creditPrice")}</span>
            <AmountInput value={f.creditPrice} onChange={(e) => setF({ ...f, creditPrice: e.target.value })} required />
          </label>
          <label>
            <span className="label">{t("kk.credit.installments")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={f.installments} onChange={(e) => setF({ ...f, installments: e.target.value })} required />
          </label>
          <label>
            <span className="label">{t("kk.credit.firstDue")}</span>
            <input type="date" className="field" value={f.firstDue} onChange={(e) => setF({ ...f, firstDue: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("kk.credit.soldOn")}</span>
            <input type="date" className="field" value={f.soldOn} onChange={(e) => setF({ ...f, soldOn: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("kk.credit.witness")}</span>
            <input className="field" value={f.witness} onChange={(e) => setF({ ...f, witness: e.target.value })} />
          </label>
          <p className="text-sm text-ink-muted md:col-span-2">{t("kk.credit.noSurcharge")}</p>
          <div className="md:col-span-2">
            <ErrorText error={save.error} />
          </div>
          <div className="flex gap-2 md:col-span-2">
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" disabled={save.isPending}>
              {t("common.save")}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function NewCustomer({ spaceId, onDone }: { spaceId: string; onDone: (id: string) => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ name: "", phone: "", consent: false });
  const save = useMutation({
    mutationFn: () => call(commands.kkAddCustomer(spaceId, { name: f.name, phone: f.phone.trim() || null, phoneConsent: f.consent, note: null })),
    onSuccess: (list) => onDone(list.find((c) => c.name === f.name.trim())?.id ?? ""),
  });
  return (
    <form
      className="grid gap-3 rounded-md border border-line p-3 md:grid-cols-2"
      aria-label={t("kk.credit.customerForm")}
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <label>
        <span className="label">{t("kk.credit.customerName")}</span>
        <input className="field" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.credit.phone")}</span>
        <input className="field" inputMode="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
      </label>
      <label className="flex items-start gap-2 text-sm md:col-span-2">
        <input type="checkbox" className="mt-1" checked={f.consent} onChange={(e) => setF({ ...f, consent: e.target.checked })} />
        {t("kk.credit.consent")}
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary justify-self-start" disabled={save.isPending}>
        {t("kk.credit.saveCustomer")}
      </button>
    </form>
  );
}

type Action = "pay" | "extend" | "forgive" | null;

function SaleCard({ spaceId, s }: { spaceId: string; s: KkCreditSaleDto }) {
  const { t } = useTranslation();
  const [action, setAction] = useState<Action>(null);
  const [amount, setAmount] = useState("");
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CASH");
  const [months, setMonths] = useState("1");
  const done = () => {
    setAction(null);
    setAmount("");
  };
  const run = useMutation({
    mutationFn: () => {
      if (action === "pay") return call(commands.kkCreditPayment(spaceId, s.id, { amount, wallet, paidOn: null, note: null }));
      if (action === "extend") return call(commands.kkCreditExtend(spaceId, s.id, { months: Number.parseInt(months, 10) || 0, on: null, note: null }));
      return call(commands.kkCreditForgive(spaceId, s.id, { amount: amount.trim() || null, on: null, note: null }));
    },
    onSuccess: done,
  });
  const del = useMutation({ mutationFn: () => call(commands.kkDeleteCreditSale(spaceId, s.id)) });
  const open = (a: Action) => {
    setAction(action === a ? null : a);
    setAmount(a === "pay" ? (s.nextDue?.amount.plain ?? "") : "");
  };
  const settled = s.status === "SETTLED";
  return (
    <article className="card flex flex-col gap-3" aria-label={`${s.customerName}: ${s.item}`} data-testid={`kk-credit-sale-${s.customerName}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">
          {s.customerName} · {s.item}
        </h3>
        <span className={`text-sm ${s.status === "OVERDUE" ? "text-warn" : "text-ink-muted"}`} data-testid="kk-credit-status">
          {s.status === "OVERDUE" ? t("kk.credit.overdueDays", { n: s.overdueDays }) : t(`kk.credit.status.${s.status}`)}
        </span>
      </div>
      <p className="text-sm text-ink-muted">
        {t("kk.credit.terms", { price: s.creditPrice.formatted, n: s.installments, date: showDate(s.soldOn) })}
        {s.creditMarkup && ` · ${t("kk.credit.markup", { cash: s.cashPrice?.formatted ?? "", diff: s.creditMarkup.formatted })}`}
        {s.witness && ` · ${t("kk.credit.witnessShow", { name: s.witness })}`}
      </p>
      <p>
        {t("kk.credit.outstanding")}: <span data-testid="kk-credit-outstanding" className="font-semibold tabular-nums">{s.outstanding.formatted}</span>
        {s.nextDue && <span className="ml-2 text-sm text-ink-muted">{t("kk.credit.next", { date: showDate(s.nextDue.date), amount: s.nextDue.amount.formatted })}</span>}
      </p>
      <details>
        <summary className="cursor-pointer text-sm">{t("kk.credit.schedule")}</summary>
        <table className="mt-2 w-full text-left text-sm">
          <thead className="text-ink-muted">
            <tr>
              <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
              <th className="py-1 pr-3 text-right font-normal">{t("kk.col.amount")}</th>
              <th className="py-1 pr-3 text-right font-normal">{t("kk.credit.covered")}</th>
              <th className="py-1 font-normal">{t("kk.eq.state")}</th>
            </tr>
          </thead>
          <tbody>
            {s.schedule.map((r) => (
              <tr key={r.due} className="border-t border-line">
                <td className="py-1 pr-3 tabular-nums">{showDate(r.due)}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{r.amount.formatted}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{r.covered.formatted}</td>
                <td className={`py-1 ${r.state === "OVERDUE" ? "text-warn" : ""}`}>{t(`kk.credit.state.${r.state}`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {s.events.length > 0 && (
          <ul className="mt-2 text-sm">
            {s.events.map((e) => (
              <li key={e.id}>
                {showDate(e.occurredOn)} · {t(`kk.credit.event.${e.kind}`, { amount: e.amount?.formatted ?? "", n: e.months ?? 0 })}
                {e.wallet && ` · ${t(`kk.wallet.${e.wallet}`)}`}
                {e.note && ` · ${e.note}`}
              </li>
            ))}
          </ul>
        )}
      </details>
      {!settled && (
        <div className="flex flex-wrap gap-2">
          {(["pay", "extend", "forgive"] as const).map((a) => (
            <button key={a} className={a === "pay" ? "btn-primary" : "btn-ghost"} aria-expanded={action === a} onClick={() => open(a)}>
              {t(`kk.credit.action.${a}`)}
            </button>
          ))}
          {s.events.length === 0 && (
            <button className="btn-ghost" aria-label={t("kk.credit.deleteNamed", { name: s.customerName, item: s.item })} onClick={() => del.mutate()}>
              {t("kk.eq.delete")}
            </button>
          )}
        </div>
      )}
      {action && (
        <form
          className="flex flex-wrap items-end gap-3 rounded-md border border-line p-3"
          aria-label={t(`kk.credit.action.${action}`)}
          onSubmit={(e) => {
            e.preventDefault();
            run.mutate();
          }}
        >
          {action === "extend" ? (
            <label>
              <span className="label">{t("kk.credit.months")}</span>
              <input className="field tabular-nums" inputMode="numeric" value={months} onChange={(e) => setMonths(e.target.value)} />
            </label>
          ) : (
            <label>
              <span className="label">{action === "pay" ? t("common.amount") : t("kk.credit.forgiveAmount")}</span>
              <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required={action === "pay"} />
            </label>
          )}
          {action === "pay" && (
            <fieldset>
              <legend className="label">{t("kk.walletLabel")}</legend>
              <div className="flex gap-2">
                {(["CASH", "CARD"] as const).map((w) => (
                  <button key={w} type="button" aria-pressed={wallet === w} className={wallet === w ? "btn-primary" : "btn-ghost"} onClick={() => setWallet(w)}>
                    {t(`kk.wallet.${w}`)}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          <p className="w-full text-sm text-ink-muted">{t(`kk.credit.actionHint.${action}`)}</p>
          <div className="w-full">
            <ErrorText error={run.error} />
          </div>
          <button className="btn-primary" disabled={run.isPending}>
            {t("common.save")}
          </button>
        </form>
      )}
      <ErrorText error={del.error} />
    </article>
  );
}
