import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkCreditSaleDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

type Channel = "CASH" | "CARD";

/**
 * Sotuvchi qurilmasi (ADR-0003): katalogdan yoki erkin summa bilan sotuv, bugungi o'z yozuvlari.
 * Foyda, chiqim va «egasi oldi» bu qurilmada yo'q — yadro ularni umuman bermaydi.
 */
export function KkSellerScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const day = useQuery({ queryKey: keys.kkSellerDay(spaceId), queryFn: () => call(commands.kkSellerDay(spaceId)) });
  const d = day.error ? undefined : day.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.seller.title")}</h1>
      <p className="text-ink-muted">{t("kk.seller.intro")}</p>
      <ErrorText error={day.error} />
      {d?.shiftClosed ? (
        <p role="status" data-testid="kk-seller-closed" className="card">
          {t("kk.seller.shiftClosed")}
        </p>
      ) : (
        <SaleForm spaceId={spaceId} />
      )}
      {d && (
        <section className="card flex flex-col gap-2" aria-label={t("kk.seller.today")}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold">{t("kk.seller.today")}</h2>
            <p data-testid="kk-seller-totals" className="text-sm tabular-nums">
              {t("kk.seller.totals", { cash: d.cash.formatted, card: d.card.formatted })}
            </p>
          </div>
          {d.sales.length === 0 && <p className="text-sm text-ink-muted">{t("kk.seller.empty")}</p>}
          <ul className="flex flex-col">
            {d.sales.map((s) => (
              <li key={s.id} data-testid="kk-seller-row" className="flex flex-wrap items-baseline justify-between gap-2 border-t border-line py-1 text-sm">
                <span>
                  {s.label || t("kk.seller.noNote")}
                  {s.qty && <span className="text-ink-muted"> · {s.qty}</span>}
                  {s.kind === "CREDIT_PAYMENT" && <span className="text-ink-muted"> · {t("kk.seller.creditPayment")}</span>}
                </span>
                <span className="tabular-nums">
                  {s.amount.formatted} <span className="text-ink-muted">· {t(`kk.channel.${s.channel}`)}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}

function ChannelPicker({ value, onChange, name }: { value: Channel; onChange: (c: Channel) => void; name: string }) {
  const { t } = useTranslation();
  return (
    <fieldset>
      <legend className="label">{t("kk.seller.channel")}</legend>
      <div className="flex gap-4">
        {(["CASH", "CARD"] as const).map((c) => (
          <label key={c} className="flex items-center gap-2">
            <input type="radio" name={name} checked={value === c} onChange={() => onChange(c)} />
            {t(`kk.channel.${c}`)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function SaleForm({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const catalog = useQuery({ queryKey: keys.kkCatalog(spaceId), queryFn: () => call(commands.kkCatalog(spaceId)) });
  const [itemId, setItemId] = useState("");
  const [qty, setQty] = useState("");
  const [amount, setAmount] = useState("");
  const [channel, setChannel] = useState<Channel>("CASH");
  const [note, setNote] = useState("");
  const item = (catalog.data ?? []).find((i) => i.id === itemId);
  const sale = useMutation({
    mutationFn: () =>
      call(
        commands.kkSellerSale(spaceId, {
          itemId: itemId || null,
          qty: itemId ? qty : null,
          amount: amount.trim() || null,
          channel,
          note: note.trim() || null,
        }),
      ),
    onSuccess: () => {
      setQty("");
      setAmount("");
      setNote("");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    sale.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={t("kk.seller.form")} onSubmit={submit}>
      <label className="md:col-span-2">
        <span className="label">{t("kk.seller.item")}</span>
        <select className="field" value={itemId} onChange={(e) => setItemId(e.target.value)}>
          <option value="">{t("kk.seller.freeAmount")}</option>
          {(catalog.data ?? []).map((i) => (
            <option key={i.id} value={i.id}>
              {i.salePrice ? t("kk.seller.itemPrice", { name: i.name, price: i.salePrice.formatted, unit: t(`kk.unit.${i.unit}`) }) : i.name}
            </option>
          ))}
        </select>
      </label>
      {item && (
        <label>
          <span className="label">{t("kk.seller.qty", { unit: t(`kk.unit.${item.unit}`) })}</span>
          <input className="field tabular-nums" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} required />
        </label>
      )}
      <label>
        <span className="label">{item ? t("kk.seller.amountOptional") : t("kk.seller.amount")}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required={!item} />
      </label>
      <ChannelPicker value={channel} onChange={setChannel} name="kk-seller-channel" />
      <label className="md:col-span-2">
        <span className="label">{t("kk.note")}</span>
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="md:col-span-2">
        <ErrorText error={sale.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={sale.isPending}>
        {t("kk.seller.save")}
      </button>
    </form>
  );
}

/** Sotuvchi uchun nasiya daftari: faqat qoldiq va to'lov qabul qilish. */
export function KkSellerCreditScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const book = useQuery({ queryKey: keys.kkCredit(spaceId), queryFn: () => call(commands.kkCreditBook(spaceId)) });
  const open = (book.error ? [] : (book.data?.sales ?? [])).filter((s) => s.outstanding.minor !== "0");
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.seller.creditTitle")}</h1>
      <p className="text-ink-muted">{t("kk.seller.creditIntro")}</p>
      <ErrorText error={book.error} />
      {book.data && open.length === 0 && <p className="card text-ink-muted">{t("kk.seller.creditEmpty")}</p>}
      {open.map((s) => (
        <CreditRow key={s.id} spaceId={spaceId} s={s} />
      ))}
    </section>
  );
}

function CreditRow({ spaceId, s }: { spaceId: string; s: KkCreditSaleDto }) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState("");
  const [wallet, setWallet] = useState<Channel>("CASH");
  const pay = useMutation({
    mutationFn: () => call(commands.kkCreditPayment(spaceId, s.id, { amount, wallet, paidOn: null, note: null })),
    onSuccess: () => setAmount(""),
  });
  return (
    <form
      className="card flex flex-col gap-3"
      aria-label={`${s.customerName}: ${s.item}`}
      data-testid={`kk-seller-credit-${s.customerName}`}
      onSubmit={(e) => {
        e.preventDefault();
        pay.mutate();
      }}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">
          {s.customerName} <span className="font-normal text-ink-muted">· {s.item}</span>
        </h2>
        <p className={s.status === "OVERDUE" ? "text-warn" : "text-ink-muted"}>
          {t("kk.seller.outstanding", { amount: s.outstanding.formatted })}
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <label>
          <span className="label">{t("kk.seller.payAmount")}</span>
          <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <ChannelPicker value={wallet} onChange={setWallet} name={`kk-seller-pay-${s.id}`} />
        <button className="btn-primary" disabled={pay.isPending}>
          {t("kk.seller.pay")}
        </button>
      </div>
      <ErrorText error={pay.error} />
    </form>
  );
}
