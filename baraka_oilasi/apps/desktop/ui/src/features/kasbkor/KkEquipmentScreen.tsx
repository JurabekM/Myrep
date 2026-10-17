import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkEquipmentDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

type Paid = "CASH" | "CARD" | "BEFORE";

/**
 * Uskunalar (kasbkor/SPEC 3.3): narx, foydali muddat, qoldiq qiymati. Eskirish oyma-oy avtomatik
 * (pul harakati emas); sotilsa yoki yaroqsiz bo'lsa — qolgan balans bir martalik xarajat.
 */
export function KkEquipmentScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const list = useQuery({ queryKey: keys.kkEquipment(spaceId), queryFn: () => call(commands.kkEquipment(spaceId)) });
  const [disposing, setDisposing] = useState<string | null>(null);
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.eq.title")}</h1>
      <p className="text-ink-muted">{t("kk.eq.intro")}</p>
      <AddForm spaceId={spaceId} />
      <section className="card flex flex-col gap-2" aria-label={t("kk.eq.list")}>
        <h2 className="text-lg font-semibold">{t("kk.eq.list")}</h2>
        {list.data?.length === 0 && <p className="text-sm text-ink-muted">{t("kk.eq.empty")}</p>}
        {list.data && list.data.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.eq.name")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.eq.cost")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.eq.monthDep")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.eq.bookValue")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.eq.state")}</th>
                <th className="py-1 font-normal">
                  <span className="sr-only">{t("kk.eq.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((e) => (
                <Row key={e.id} spaceId={spaceId} e={e} disposing={disposing === e.id} onDispose={() => setDisposing(disposing === e.id ? null : e.id)} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}

function Row({ spaceId, e, disposing, onDispose }: { spaceId: string; e: KkEquipmentDto; disposing: boolean; onDispose: () => void }) {
  const { t } = useTranslation();
  const del = useMutation({ mutationFn: () => call(commands.kkDeleteEquipment(spaceId, e.id)) });
  return (
    <>
      <tr className="border-t border-line align-top">
        <td className="py-2 pr-3">
          <span className="font-medium">{e.name}</span>
          <span className="block text-xs text-ink-muted">
            {t("kk.eq.since", { date: showDate(e.acquiredOn), months: e.usefulMonths })}
            {e.wallet ? ` · ${t(`kk.wallet.${e.wallet}`)}` : ` · ${t("kk.eq.paidBefore")}`}
          </span>
        </td>
        <td className="py-2 pr-3 text-right tabular-nums">{e.cost.formatted}</td>
        <td data-testid={`kk-eq-dep-${e.name}`} className="py-2 pr-3 text-right tabular-nums">
          {e.monthDepreciation.formatted}
        </td>
        <td className="py-2 pr-3 text-right tabular-nums">{e.bookValue.formatted}</td>
        <td className="py-2 pr-3">
          {e.status === "DISPOSED"
            ? t("kk.eq.disposed", { date: showDate(e.disposedOn ?? ""), amount: e.disposalProceeds?.formatted ?? "" })
            : e.status === "DEPRECIATED"
              ? t("kk.eq.depreciated")
              : t("kk.eq.monthsLeft", { n: e.monthsLeft })}
        </td>
        <td className="py-2 text-right">
          <div className="flex flex-wrap justify-end gap-1">
            {e.status !== "DISPOSED" && (
              <button className="btn-ghost px-2 py-1 text-sm" aria-expanded={disposing} onClick={onDispose}>
                {t("kk.eq.dispose")}
              </button>
            )}
            <button className="btn-ghost px-2 py-1 text-sm" aria-label={t("kk.eq.deleteNamed", { name: e.name })} onClick={() => del.mutate()}>
              {t("kk.eq.delete")}
            </button>
          </div>
          <ErrorText error={del.error} />
        </td>
      </tr>
      {disposing && (
        <tr>
          <td colSpan={6} className="pb-3">
            <DisposeForm spaceId={spaceId} e={e} onDone={onDispose} />
          </td>
        </tr>
      )}
    </>
  );
}

function AddForm({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ name: "", cost: "", salvage: "", months: "60", acquiredOn: "" });
  const [paid, setPaid] = useState<Paid>("CARD");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkAddEquipment(spaceId, {
          name: f.name,
          cost: f.cost,
          salvage: f.salvage.trim() || null,
          usefulMonths: Number.parseInt(f.months, 10) || 0,
          acquiredOn: f.acquiredOn || null,
          wallet: paid === "BEFORE" ? null : paid,
        }),
      ),
    onSuccess: () => setF({ name: "", cost: "", salvage: "", months: "60", acquiredOn: "" }),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("kk.eq.add")}>
      <h2 className="text-lg font-semibold md:col-span-2">{t("kk.eq.add")}</h2>
      <label className="md:col-span-2">
        <span className="label">{t("kk.eq.name")}</span>
        <input className="field" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.eq.cost")}</span>
        <AmountInput value={f.cost} onChange={(e) => setF({ ...f, cost: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.eq.months")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.months} onChange={(e) => setF({ ...f, months: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.eq.salvage")}</span>
        <AmountInput value={f.salvage} onChange={(e) => setF({ ...f, salvage: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("kk.eq.acquiredOn")}</span>
        <input type="date" className="field" value={f.acquiredOn} onChange={(e) => setF({ ...f, acquiredOn: e.target.value })} />
      </label>
      <fieldset className="md:col-span-2">
        <legend className="label">{t("kk.eq.paidFrom")}</legend>
        <div className="flex flex-wrap gap-2">
          {(["CASH", "CARD", "BEFORE"] as const).map((w) => (
            <button key={w} type="button" aria-pressed={paid === w} className={paid === w ? "btn-primary" : "btn-ghost"} onClick={() => setPaid(w)}>
              {w === "BEFORE" ? t("kk.eq.paidBefore") : t(`kk.wallet.${w}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={save.isPending}>
        {t("kk.eq.addButton")}
      </button>
    </form>
  );
}

function DisposeForm({ spaceId, e, onDone }: { spaceId: string; e: KkEquipmentDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [proceeds, setProceeds] = useState("");
  const [wallet, setWallet] = useState<"CASH" | "CARD">("CASH");
  const [on, setOn] = useState("");
  const save = useMutation({
    mutationFn: () => call(commands.kkDisposeEquipment(spaceId, e.id, { proceeds: proceeds.trim() || null, wallet: proceeds.trim() ? wallet : null, disposedOn: on || null })),
    onSuccess: onDone,
  });
  return (
    <form
      className="flex flex-col gap-3 rounded-md border border-line p-3"
      aria-label={t("kk.eq.disposeTitle", { name: e.name })}
      onSubmit={(ev) => {
        ev.preventDefault();
        save.mutate();
      }}
    >
      <p className="text-sm text-ink-muted">{t("kk.eq.disposeHint", { amount: e.bookValue.formatted })}</p>
      <div className="flex flex-wrap items-end gap-3">
        <label>
          <span className="label">{t("kk.eq.proceeds")}</span>
          <AmountInput value={proceeds} onChange={(ev) => setProceeds(ev.target.value)} />
        </label>
        <fieldset>
          <legend className="label">{t("kk.eq.proceedsWallet")}</legend>
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
        {t("kk.eq.disposeSave")}
      </button>
    </form>
  );
}
