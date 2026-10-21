import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkItemDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

type MoveKind = "PURCHASE" | "SALE" | "WRITE_OFF" | "COUNT";
type Open = { id: string; mode: MoveKind | "EDIT" } | null;

const UNITS = ["G", "ML", "MM", "PCS"] as const;
const MOVES: MoveKind[] = ["PURCHASE", "SALE", "WRITE_OFF", "COUNT"];

/**
 * Tovarlar (kasbkor/SPEC 4.1–4.4): qoldiq, tannarx (o'rtacha yoki FIFO), qayta tiklash narxi va
 * «inflyatsiya yegan kapital», muzlagan tovar. Hamma hisob yadroda; UI faqat ko'rsatadi va matn yuboradi.
 */
export function KkStockScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const stock = useQuery({ queryKey: keys.kkStock(spaceId), queryFn: () => call(commands.kkStock(spaceId)) });
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<Open>(null);
  const s = stock.data;
  const toggle = (id: string, mode: MoveKind | "EDIT") => setOpen(open?.id === id && open.mode === mode ? null : { id, mode });
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.stock.title")}</h1>
      <p className="text-ink-muted">{t("kk.stock.intro")}</p>
      <ErrorText error={stock.error} />

      {s && (
        <section aria-label={t("kk.stock.totals")} className="grid gap-5 md:grid-cols-2">
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.stock.bookValue")}</p>
            <p data-testid="kk-stock-value" className="text-2xl font-semibold tabular-nums">
              {s.value.formatted}
            </p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.stock.replacementValue")}</p>
            <p data-testid="kk-stock-replacement" className="text-2xl font-semibold tabular-nums">
              {s.replacementValue.formatted}
            </p>
          </div>
          <div className="card">
            <p className="text-sm text-ink-muted">{t("kk.stock.gap")}</p>
            <p data-testid="kk-stock-gap" className="kpi text-accent">
              {s.inflationGap.formatted}
            </p>
            <p className="text-xs text-ink-muted">{t("kk.stock.gapHint")}</p>
          </div>
          <div className={`card ${s.frozenCount > 0 ? "border-warn" : ""}`}>
            <p className="text-sm text-ink-muted">{t("kk.stock.frozenTotal")}</p>
            <p data-testid="kk-stock-frozen" className="text-2xl font-semibold tabular-nums">
              {s.frozenValue.formatted}
            </p>
            <p className="text-xs text-ink-muted">{t("kk.stock.frozenCount", { count: s.frozenCount })}</p>
          </div>
        </section>
      )}

      <div>
        <button className={adding ? "btn-ghost" : "btn-primary"} aria-expanded={adding} onClick={() => setAdding((v) => !v)}>
          {t("kk.stock.add")}
        </button>
      </div>
      {adding && <ItemForm spaceId={spaceId} onDone={() => setAdding(false)} />}

      <section className="flex flex-col gap-4" aria-label={t("kk.stock.list")}>
        <h2 className="text-lg font-semibold">{t("kk.stock.list")}</h2>
        {s?.items.length === 0 && <p className="text-sm text-ink-muted">{t("kk.stock.empty")}</p>}
        {s?.items.map((item) => (
          <ItemCard key={item.id} spaceId={spaceId} item={item} open={open?.id === item.id ? open.mode : null} onToggle={(m) => toggle(item.id, m)} onDone={() => setOpen(null)} />
        ))}
      </section>
    </section>
  );
}

function ItemCard({
  spaceId,
  item,
  open,
  onToggle,
  onDone,
}: {
  spaceId: string;
  item: KkItemDto;
  open: MoveKind | "EDIT" | null;
  onToggle: (m: MoveKind | "EDIT") => void;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const unit = t(`kk.unit.${item.unit}`);
  const del = useMutation({ mutationFn: () => call(commands.kkDeleteItem(spaceId, item.id)) });
  const rows: [string, string][] = [
    [t("kk.stock.bookValue"), item.value.formatted],
    [t("kk.stock.unitCost", { unit }), item.unitCost?.formatted ?? "—"],
    [t("kk.stock.replacementPrice", { unit }), item.replacementPrice?.formatted ?? "—"],
    [t("kk.stock.replacementValue"), item.replacementValue?.formatted ?? "—"],
    [t("kk.stock.gap"), item.inflationGap?.formatted ?? "—"],
  ];
  if (item.salePrice) rows.push([t("kk.stock.salePrice", { unit }), item.salePrice.formatted]);
  return (
    <article data-testid={`kk-item-${item.name}`} aria-label={item.name} className={`card flex flex-col gap-3 ${item.frozen ? "border-warn" : ""}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">
          {item.name}
          <span className="ml-2 text-sm font-normal text-ink-muted">{t(`kk.stock.method.${item.method}`)}</span>
        </h3>
        <p data-testid="kk-item-qty" className="text-2xl font-semibold tabular-nums">
          {item.qty} {unit}
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
        </tbody>
      </table>
      {item.saleBelowReplacement && (
        <p role="note" className="text-sm text-warn">
          {t("kk.stock.saleBelow")}
        </p>
      )}
      {item.belowMin && (
        <p role="note" className="text-sm text-warn">
          {t("kk.stock.belowMin", { qty: item.minQty ?? "", unit })}
        </p>
      )}
      {item.frozen && (
        <p role="note" className="text-sm text-warn">
          {item.lastSaleOn ? t("kk.stock.frozenSince", { date: showDate(item.lastSaleOn), days: item.frozenDays }) : t("kk.stock.frozenNeverSold", { days: item.frozenDays })}{" "}
          {t("kk.stock.frozenOffer")}
        </p>
      )}
      <div role="group" aria-label={t("kk.stock.actions", { name: item.name })} className="flex flex-wrap gap-2">
        {MOVES.map((m) => (
          <button key={m} className={open === m ? "btn-primary" : "btn-ghost"} aria-expanded={open === m} onClick={() => onToggle(m)}>
            {t(`kk.stock.action.${m}`)}
          </button>
        ))}
        <button className="btn-ghost" aria-expanded={open === "EDIT"} onClick={() => onToggle("EDIT")}>
          {t("kk.stock.edit")}
        </button>
        {item.moves.length === 0 && (
          <button className="btn-ghost" aria-label={t("kk.stock.deleteNamed", { name: item.name })} onClick={() => del.mutate()}>
            {t("kk.stock.delete")}
          </button>
        )}
      </div>
      <ErrorText error={del.error} />
      {open && open !== "EDIT" && <MoveForm spaceId={spaceId} item={item} kind={open} onDone={onDone} />}
      {open === "EDIT" && <ItemForm spaceId={spaceId} item={item} onDone={onDone} />}
      {item.moves.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm text-ink-muted">{t("kk.stock.history", { count: item.moves.length })}</summary>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.col.kind")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.stock.qtyShort", { unit })}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.col.amount")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.stock.cost")}</th>
                <th className="py-1 font-normal">{t("kk.col.note")}</th>
              </tr>
            </thead>
            <tbody>
              {item.moves.map((m) => (
                <tr key={m.id} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">{showDate(m.occurredOn)}</td>
                  <td className="py-1 pr-3">{t(`kk.stock.kind.${m.kind}`)}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.qty}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.amount?.formatted ?? "—"}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{m.cost.formatted}</td>
                  <td className="py-1 text-ink-muted">{[m.wallet ? t(`kk.wallet.${m.wallet}`) : null, m.reason].filter(Boolean).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </article>
  );
}

function MoveForm({ spaceId, item, kind, onDone }: { spaceId: string; item: KkItemDto; kind: MoveKind; onDone: () => void }) {
  const { t } = useTranslation();
  const hintId = useId();
  const unit = t(`kk.unit.${item.unit}`);
  const [qty, setQty] = useState("");
  const [amount, setAmount] = useState("");
  const [wallet, setWallet] = useState<"CASH" | "CARD" | "BEFORE">(kind === "SALE" ? "CASH" : "CARD");
  const [on, setOn] = useState("");
  const [reason, setReason] = useState("");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkStockMove(spaceId, item.id, {
          kind,
          qty,
          amount: amount.trim() || null,
          wallet: kind === "PURCHASE" || kind === "SALE" ? (wallet === "BEFORE" ? null : wallet) : null,
          occurredOn: on || null,
          reason: reason.trim() || null,
        }),
      ),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  const amountHint =
    kind === "SALE"
      ? item.salePrice
        ? t("kk.stock.saleAmountHint", { price: item.salePrice.formatted, unit })
        : null
      : kind === "COUNT"
        ? t("kk.stock.foundValueHint")
        : null;
  const wallets = kind === "PURCHASE" ? (["CASH", "CARD", "BEFORE"] as const) : (["CASH", "CARD"] as const);
  return (
    <form className="flex flex-col gap-3 rounded-md border border-line p-3" aria-label={t("kk.stock.formTitle", { action: t(`kk.stock.action.${kind}`), name: item.name })} onSubmit={submit}>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label>
            <span className="label">{kind === "COUNT" ? t("kk.stock.counted", { unit }) : t("kk.stock.qty", { unit })}</span>
            <input className="field tabular-nums" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} aria-describedby={kind === "COUNT" ? `${hintId}-qty` : undefined} required />
          </label>
          {kind === "COUNT" && (
            <p id={`${hintId}-qty`} className="mt-1 text-xs text-ink-muted">
              {t("kk.stock.bookQty", { qty: item.qty, unit })}
            </p>
          )}
        </div>
        {kind !== "WRITE_OFF" && (
          <div>
            <label>
              <span className="label">{t(`kk.stock.amount.${kind}`)}</span>
              <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required={kind === "PURCHASE"} aria-describedby={amountHint ? `${hintId}-amount` : undefined} />
            </label>
            {amountHint && (
              <p id={`${hintId}-amount`} className="mt-1 text-xs text-ink-muted">
                {amountHint}
              </p>
            )}
          </div>
        )}
        {(kind === "PURCHASE" || kind === "SALE") && (
          <fieldset className="md:col-span-2">
            <legend className="label">{kind === "PURCHASE" ? t("kk.stock.paidFrom") : t("kk.stock.paidTo")}</legend>
            <div className="flex flex-wrap gap-2">
              {wallets.map((w) => (
                <button key={w} type="button" aria-pressed={wallet === w} className={wallet === w ? "btn-primary" : "btn-ghost"} onClick={() => setWallet(w)}>
                  {w === "BEFORE" ? t("kk.stock.paidBefore") : t(`kk.wallet.${w}`)}
                </button>
              ))}
            </div>
          </fieldset>
        )}
        {(kind === "WRITE_OFF" || kind === "COUNT") && (
          <div className="md:col-span-2">
            <label>
              <span className="label">{t("kk.stock.reason")}</span>
              <input className="field" value={reason} onChange={(e) => setReason(e.target.value)} aria-describedby={`${hintId}-reason`} />
            </label>
            <p id={`${hintId}-reason`} className="mt-1 text-xs text-ink-muted">
              {t(`kk.stock.reasonHint.${kind}`)}
            </p>
          </div>
        )}
        <label>
          <span className="label">{t("kk.date")}</span>
          <input type="date" className="field" value={on} onChange={(e) => setOn(e.target.value)} />
        </label>
      </div>
      <ErrorText error={save.error} />
      <button className="btn-primary self-start" disabled={save.isPending}>
        {t("common.save")}
      </button>
    </form>
  );
}

function ItemForm({ spaceId, item, onDone }: { spaceId: string; item?: KkItemDto; onDone: () => void }) {
  const { t } = useTranslation();
  const hintId = useId();
  const [f, setF] = useState({
    name: item?.name ?? "",
    unit: item?.unit ?? "G",
    method: item?.method ?? "AVERAGE",
    salePrice: item?.salePrice?.plain ?? "",
    replacementPrice: item?.replacementPriceInput?.plain ?? "",
    minQty: item?.minQty ?? "",
    frozenDays: String(item?.frozenDays ?? 90),
  });
  const unit = t(`kk.unit.${f.unit}`);
  const locked = (item?.moves.length ?? 0) > 0;
  const save = useMutation({
    mutationFn: () => {
      const input = {
        name: f.name,
        unit: f.unit,
        method: f.method,
        salePrice: f.salePrice.trim() || null,
        replacementPrice: f.replacementPrice.trim() || null,
        minQty: f.minQty.trim() || null,
        frozenDays: Number.parseInt(f.frozenDays, 10) || null,
        note: item?.note ?? null,
      };
      return call(item ? commands.kkUpdateItem(spaceId, item.id, input) : commands.kkAddItem(spaceId, input));
    },
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" aria-label={item ? t("kk.stock.editTitle", { name: item.name }) : t("kk.stock.add")} onSubmit={submit}>
      <label>
        <span className="label">{t("kk.stock.name")}</span>
        <input className="field" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.stock.unit")}</span>
        <select className="field" value={f.unit} disabled={!!item} onChange={(e) => setF({ ...f, unit: e.target.value })}>
          {UNITS.map((u) => (
            <option key={u} value={u}>
              {t(`kk.unit.${u}`)}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="md:col-span-2" disabled={locked}>
        <legend className="label">{t("kk.stock.methodLabel")}</legend>
        <div className="flex flex-wrap gap-2">
          {(["AVERAGE", "FIFO"] as const).map((m) => (
            <button key={m} type="button" aria-pressed={f.method === m} className={f.method === m ? "btn-primary" : "btn-ghost"} onClick={() => setF({ ...f, method: m })}>
              {t(`kk.stock.method.${m}`)}
            </button>
          ))}
        </div>
        <p className="mt-1 text-xs text-ink-muted">{locked ? t("kk.stock.methodLocked") : t("kk.stock.methodHint")}</p>
      </fieldset>
      <label>
        <span className="label">{t("kk.stock.salePrice", { unit })}</span>
        <AmountInput value={f.salePrice} onChange={(e) => setF({ ...f, salePrice: e.target.value })} />
      </label>
      <div>
        <label>
          <span className="label">{t("kk.stock.currentPrice", { unit })}</span>
          <AmountInput value={f.replacementPrice} onChange={(e) => setF({ ...f, replacementPrice: e.target.value })} aria-describedby={`${hintId}-price`} />
        </label>
        <p id={`${hintId}-price`} className="mt-1 text-xs text-ink-muted">
          {t("kk.stock.currentPriceHint")}
        </p>
      </div>
      <label>
        <span className="label">{t("kk.stock.minQty", { unit })}</span>
        <input className="field tabular-nums" inputMode="decimal" value={f.minQty} onChange={(e) => setF({ ...f, minQty: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("kk.stock.frozenDays")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.frozenDays} onChange={(e) => setF({ ...f, frozenDays: e.target.value })} />
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={save.isPending}>
        {item ? t("common.save") : t("kk.stock.addButton")}
      </button>
    </form>
  );
}
