import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkSupplierDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { AgreementFileActions, AgreementStatus, EndForm, PhoneFields, SignForm, TemplateReviewNote } from "./KkAgreementParts";

type Mode = "SIGN" | "DELIVERY" | "PAYMENT" | "EDIT" | "END";

/**
 * Ta'minotchilar (kasbkor/SPEC 7.1 `SUPPLY`): narx kelishuvda qotiriladi, yetkazish — nasiyaga tovar
 * (tovar bog'lansa — qoldiqqa kiradi), to'lov eng erta muddatdan yopiladi; kechikish uchun jarima yo'q.
 */
export function KkSuppliersScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const list = useQuery({ queryKey: keys.kkSuppliers(spaceId), queryFn: () => call(commands.kkSuppliers(spaceId)) });
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<{ id: string; mode: Mode } | null>(null);
  const s = list.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.supply.title")}</h1>
      <p className="text-ink-muted">{t("kk.supply.intro")}</p>
      <TemplateReviewNote status={s?.templateReview} />
      <ErrorText error={list.error} />
      {s && (
        <section aria-label={t("kk.supply.totals")} className="grid gap-5 md:grid-cols-3">
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.supply.outstanding")}</p>
            <p data-testid="kk-supply-outstanding" className="text-2xl font-semibold tabular-nums text-accent">
              {s.outstanding.formatted}
            </p>
          </div>
          <div className={`card ${s.overdue.minor !== "0" ? "border-warn" : ""}`}>
            <p className="text-sm text-ink-muted">{t("kk.supply.overdue")}</p>
            <p data-testid="kk-supply-overdue" className="text-2xl font-semibold tabular-nums">
              {s.overdue.formatted}
            </p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.supply.dueSoon")}</p>
            <p data-testid="kk-supply-due-soon" className="text-2xl font-semibold tabular-nums">
              {s.dueSoon.formatted}
            </p>
          </div>
        </section>
      )}
      <div>
        <button className={adding ? "btn-ghost" : "btn-primary"} aria-expanded={adding} onClick={() => setAdding((v) => !v)}>
          {t("kk.supply.add")}
        </button>
      </div>
      {adding && <SupplierForm spaceId={spaceId} onDone={() => setAdding(false)} />}
      <section className="flex flex-col gap-4" aria-label={t("kk.supply.list")}>
        <h2 className="text-lg font-semibold">{t("kk.supply.list")}</h2>
        {s?.suppliers.length === 0 && <p className="text-sm text-ink-muted">{t("kk.supply.empty")}</p>}
        {s?.suppliers.map((x) => (
          <SupplierCard
            key={x.id}
            spaceId={spaceId}
            x={x}
            open={open?.id === x.id ? open.mode : null}
            onToggle={(m) => setOpen(open?.id === x.id && open.mode === m ? null : { id: x.id, mode: m })}
            onDone={() => setOpen(null)}
          />
        ))}
      </section>
    </section>
  );
}

function SupplierCard({ spaceId, x, open, onToggle, onDone }: { spaceId: string; x: KkSupplierDto; open: Mode | null; onToggle: (m: Mode) => void; onDone: () => void }) {
  const { t } = useTranslation();
  const a = x.agreement;
  const active = a.status !== "ENDED";
  const signed = a.signedVersions > 0;
  const unit = x.terms.unit ? t(`kk.unit.${x.terms.unit}`) : null;
  const rows: [string, string, string?][] = [
    [t("kk.supply.goods"), x.terms.itemName ?? x.terms.goods ?? "—"],
    [t("kk.supply.priceRow"), x.terms.unitPrice ? (unit ? `${x.terms.unitPrice.formatted} / ${unit}` : x.terms.unitPrice.formatted) : t("kk.supply.priceEach")],
    [t("kk.supply.paymentRow"), t("kk.supply.paymentDaysValue", { n: x.terms.paymentDays })],
    [t("kk.supply.outstanding"), x.outstanding.formatted, "kk-supplier-outstanding"],
  ];
  if (x.nextDue) rows.push([t("kk.supply.nextDue"), t("kk.supply.nextDueValue", { date: showDate(x.nextDue.date), amount: x.nextDue.amount.formatted })]);
  const action = (m: Mode, label: string) => (
    <button key={m} className={open === m ? "btn-primary" : "btn-ghost"} aria-expanded={open === m} onClick={() => onToggle(m)}>
      {label}
    </button>
  );
  return (
    <article data-testid={`kk-supplier-${x.name}`} aria-label={x.name} className={`card flex flex-col gap-3 ${x.overdue.minor !== "0" ? "border-warn" : ""}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">{x.name}</h3>
        <AgreementStatus state={a} testId="kk-supplier-status" />
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
      {x.overdue.minor !== "0" && (
        <p role="note" className="text-sm text-warn">
          {t("kk.supply.overdueNote", { amount: x.overdue.formatted })}
        </p>
      )}
      <div role="group" aria-label={t("kk.agr.actions", { name: x.name })} className="flex flex-wrap gap-2">
        {a.canSign && action("SIGN", t("kk.agr.sign"))}
        {signed && active && action("DELIVERY", t("kk.supply.delivery"))}
        {signed && x.outstanding.minor !== "0" && action("PAYMENT", t("kk.supply.payment"))}
        {active && action("EDIT", t("kk.agr.edit"))}
        {signed && active && action("END", t("kk.supply.end"))}
        <AgreementFileActions spaceId={spaceId} id={x.id} name={x.name} state={a} />
      </div>
      {open === "SIGN" && <SignForm spaceId={spaceId} id={x.id} name={x.name} state={a} onDone={onDone} />}
      {open === "DELIVERY" && <DeliveryForm spaceId={spaceId} x={x} onDone={onDone} />}
      {open === "PAYMENT" && <PaymentForm spaceId={spaceId} x={x} onDone={onDone} />}
      {open === "EDIT" && <SupplierForm spaceId={spaceId} x={x} onDone={onDone} />}
      {open === "END" && <EndForm spaceId={spaceId} id={x.id} name={x.name} onDone={onDone} />}
      {x.deliveries.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm text-ink-muted">{t("kk.supply.history", { count: x.deliveries.length + x.payments.length })}</summary>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.col.kind")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.col.amount")}</th>
                <th className="py-1 font-normal">{t("kk.col.note")}</th>
              </tr>
            </thead>
            <tbody>
              {x.deliveries.map((d) => (
                <tr key={d.id} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">{showDate(d.deliveredOn)}</td>
                  <td className="py-1 pr-3">{t("kk.supply.kind.DELIVERY")}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{d.amount.formatted}</td>
                  <td className="py-1 text-ink-muted">
                    {[d.qty && unit ? `${d.qty} ${unit}` : null, t(`kk.supply.state.${d.state}`, { date: showDate(d.dueOn), days: d.overdueDays })].filter(Boolean).join(" · ")}
                  </td>
                </tr>
              ))}
              {x.payments.map((p) => (
                <tr key={p.id} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">{showDate(p.paidOn)}</td>
                  <td className="py-1 pr-3">{t("kk.supply.kind.PAYMENT")}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{p.amount.formatted}</td>
                  <td className="py-1 text-ink-muted">{t(`kk.wallet.${p.wallet}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </article>
  );
}

function DeliveryForm({ spaceId, x, onDone }: { spaceId: string; x: KkSupplierDto; onDone: () => void }) {
  const { t } = useTranslation();
  const hint = useId();
  const [qty, setQty] = useState("");
  const [amount, setAmount] = useState("");
  const [on, setOn] = useState("");
  const unit = x.terms.unit ? t(`kk.unit.${x.terms.unit}`) : null;
  const save = useMutation({
    mutationFn: () => call(commands.kkSupplyDelivery(spaceId, x.id, { deliveredOn: on || null, qty: qty.trim() || null, amount: amount.trim() || null, note: null })),
    onSuccess: onDone,
  });
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-col gap-3 rounded-md border border-line p-3" aria-label={t("kk.supply.deliveryTitle", { name: x.name })} onSubmit={submit}>
      <p id={hint} className="text-sm text-ink-muted">
        {t("kk.supply.deliveryHint", { n: x.terms.paymentDays })}
      </p>
      <div className="flex flex-wrap items-end gap-3">
        {unit && (
          <label>
            <span className="label">{t("kk.stock.qty", { unit })}</span>
            <input className="field tabular-nums" inputMode="decimal" value={qty} onChange={(ev) => setQty(ev.target.value)} required />
          </label>
        )}
        <label>
          <span className="label">{x.terms.unitPrice && unit ? t("kk.supply.amountOptional") : t("kk.supply.amount")}</span>
          <AmountInput value={amount} onChange={(ev) => setAmount(ev.target.value)} aria-describedby={hint} />
        </label>
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

function PaymentForm({ spaceId, x, onDone }: { spaceId: string; x: KkSupplierDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState(x.nextDue?.amount.plain ?? "");
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CARD");
  const [on, setOn] = useState("");
  const save = useMutation({
    mutationFn: () => call(commands.kkSupplyPayment(spaceId, x.id, { amount: amount.trim() || null, wallet, paidOn: on || null, note: null })),
    onSuccess: onDone,
  });
  return (
    <form
      className="flex flex-col gap-3 rounded-md border border-line p-3"
      aria-label={t("kk.supply.paymentTitle", { name: x.name })}
      onSubmit={(ev) => {
        ev.preventDefault();
        save.mutate();
      }}
    >
      <div className="flex flex-wrap items-end gap-3">
        <label>
          <span className="label">{t("kk.supply.amount")}</span>
          <AmountInput value={amount} onChange={(ev) => setAmount(ev.target.value)} />
        </label>
        <fieldset>
          <legend className="label">{t("kk.staff.fromWallet")}</legend>
          <div className="flex gap-2">
            {(["CASH", "CARD"] as const).map((w) => (
              <button key={w} type="button" aria-pressed={wallet === w} className={wallet === w ? "btn-primary" : "btn-ghost"} onClick={() => setWallet(w)}>
                {t(`kk.wallet.${w}`)}
              </button>
            ))}
          </div>
        </fieldset>
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

function SupplierForm({ spaceId, x, onDone }: { spaceId: string; x?: KkSupplierDto; onDone: () => void }) {
  const { t } = useTranslation();
  const hint = useId();
  const stock = useQuery({ queryKey: keys.kkStock(spaceId), queryFn: () => call(commands.kkStock(spaceId)) });
  const [f, setF] = useState({
    name: x?.name ?? "",
    phone: x?.phone ?? "",
    consent: !!x?.phone,
    goods: x?.terms.goods ?? "",
    itemId: x?.terms.itemId ?? "",
    unitPrice: x?.terms.unitPrice?.plain ?? "",
    paymentDays: String(x?.terms.paymentDays ?? 30),
    delivery: x?.terms.delivery ?? "",
    returns: x?.terms.returns ?? "",
    startedOn: x?.agreement.startedOn ?? "",
    arbiter: x?.terms.arbiter ?? "",
    reviewOn: x?.agreement.reviewOn ?? "",
  });
  const set = (k: keyof typeof f) => (ev: { target: { value: string } }) => setF({ ...f, [k]: ev.target.value });
  const item = stock.data?.items.find((i) => i.id === f.itemId);
  const save = useMutation({
    mutationFn: () => {
      const input = {
        name: f.name,
        phone: f.phone.trim() || null,
        phoneConsent: f.consent,
        goods: f.goods.trim() || null,
        itemId: f.itemId || null,
        unitPrice: f.unitPrice.trim() || null,
        paymentDays: Number.parseInt(f.paymentDays, 10) || 0,
        delivery: f.delivery.trim() || null,
        returns: f.returns.trim() || null,
        startedOn: f.startedOn || null,
        arbiter: f.arbiter.trim() || null,
        reviewOn: f.reviewOn || null,
        note: x?.terms.note ?? null,
      };
      return call(x ? commands.kkUpdateSupplier(spaceId, x.id, input) : commands.kkAddSupplier(spaceId, input));
    },
    onSuccess: onDone,
  });
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={x ? t("kk.agr.editTitle", { name: x.name }) : t("kk.supply.add")} onSubmit={submit}>
      <label>
        <span className="label">{t("kk.supply.name")}</span>
        <input className="field" value={f.name} onChange={set("name")} required />
      </label>
      <div className="hidden md:block" />
      <PhoneFields phone={f.phone} consent={f.consent} onPhone={(v) => setF({ ...f, phone: v })} onConsent={(v) => setF({ ...f, consent: v })} />
      <div>
        <label>
          <span className="label">{t("kk.supply.item")}</span>
          <select className="field" value={f.itemId} onChange={set("itemId")} aria-describedby={hint}>
            <option value="">{t("kk.supply.noItem")}</option>
            {stock.data?.items.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
        </label>
        <p id={hint} className="mt-1 text-xs text-ink-muted">
          {f.itemId ? t("kk.supply.itemHint") : t("kk.supply.noItemHint")}
        </p>
      </div>
      <label>
        <span className="label">{t("kk.supply.goods")}</span>
        <input className="field" value={f.goods} onChange={set("goods")} />
      </label>
      <label>
        <span className="label">{item ? t("kk.supply.priceUnit", { unit: t(`kk.unit.${item.unit}`) }) : t("kk.supply.price")}</span>
        <AmountInput value={f.unitPrice} onChange={set("unitPrice")} />
      </label>
      <label>
        <span className="label">{t("kk.supply.paymentDays")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.paymentDays} onChange={set("paymentDays")} />
      </label>
      <label className="md:col-span-2">
        <span className="label">{t("kk.supply.deliveryTerms")}</span>
        <input className="field" value={f.delivery} onChange={set("delivery")} />
      </label>
      <label className="md:col-span-2">
        <span className="label">{t("kk.supply.returns")}</span>
        <input className="field" value={f.returns} onChange={set("returns")} />
      </label>
      <label>
        <span className="label">{t("kk.supply.startedOn")}</span>
        <input type="date" className="field" value={f.startedOn} disabled={!!x && x.agreement.signedVersions > 0} onChange={set("startedOn")} />
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
        {x ? t("common.save") : t("kk.supply.addButton")}
      </button>
    </form>
  );
}
