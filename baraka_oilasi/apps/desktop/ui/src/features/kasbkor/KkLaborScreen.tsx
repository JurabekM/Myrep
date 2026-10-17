import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

/**
 * Oilaviy mehnat (kasbkor/SPEC 3.1): pul to'lanmasa ham tannarxga kiradi. To'langan bo'lsa — u chiqimda
 * bor, haqiqiy foydadan qayta ayirilmaydi. Qiymat (soat × baho) yadroda hisoblanadi.
 */
export function KkLaborScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const list = useQuery({ queryKey: keys.kkLabor(spaceId), queryFn: () => call(commands.kkFamilyLabor(spaceId, null)) });
  const overview = useQuery({ queryKey: keys.kk(spaceId), queryFn: () => call(commands.kkOverview(spaceId, null)) });
  const del = useMutation({ mutationFn: (id: string) => call(commands.kkDeleteFamilyLabor(spaceId, id)) });
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.fl.title")}</h1>
      <p className="text-ink-muted">{t("kk.fl.intro")}</p>
      {overview.data && (
        <p className="card">
          <span className="text-sm text-ink-muted">{t("kk.fl.total")}</span>
          <span data-testid="kk-family-labor" className="block text-2xl font-semibold tabular-nums">
            {overview.data.profit.familyLabor.formatted}
          </span>
        </p>
      )}
      <AddForm spaceId={spaceId} />
      <section className="card flex flex-col gap-2" aria-label={t("kk.fl.list")}>
        <h2 className="text-lg font-semibold">{t("kk.fl.list")}</h2>
        {list.data?.length === 0 && <p className="text-sm text-ink-muted">{t("kk.fl.empty")}</p>}
        {list.data && list.data.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.fl.person")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.fl.hours")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.fl.rate")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.fl.value")}</th>
                <th className="py-1 font-normal">
                  <span className="sr-only">{t("kk.eq.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((r) => (
                <tr key={r.id} className="border-t border-line">
                  <td className="py-1 pr-3 tabular-nums">{showDate(r.workedOn)}</td>
                  <td className="py-1 pr-3">
                    {r.person}
                    {r.paid && <span className="ml-2 text-xs text-ink-muted">{t("kk.fl.paidTag")}</span>}
                    {r.note && <span className="block text-xs text-ink-muted">{r.note}</span>}
                  </td>
                  <td className="py-1 pr-3 text-right tabular-nums">{r.hours}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{r.hourlyRate.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{r.value.formatted}</td>
                  <td className="py-1 text-right">
                    <button className="btn-ghost px-2 py-1 text-sm" aria-label={t("kk.fl.deleteNamed", { name: r.person, date: showDate(r.workedOn) })} onClick={() => del.mutate(r.id)}>
                      {t("kk.eq.delete")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <ErrorText error={del.error} />
      </section>
    </section>
  );
}

function AddForm({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const empty = { person: "", hours: "", rate: "", workedOn: "", note: "" };
  const [f, setF] = useState(empty);
  const [paid, setPaid] = useState(false);
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkAddFamilyLabor(spaceId, {
          person: f.person,
          hours: f.hours,
          hourlyRate: f.rate,
          paid,
          workedOn: f.workedOn || null,
          note: f.note.trim() || null,
        }),
      ),
    onSuccess: () => {
      setF({ ...empty, person: f.person, rate: f.rate });
      setPaid(false);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("kk.fl.add")}>
      <h2 className="text-lg font-semibold md:col-span-2">{t("kk.fl.add")}</h2>
      <label>
        <span className="label">{t("kk.fl.person")}</span>
        <input className="field" value={f.person} onChange={(e) => setF({ ...f, person: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("kk.date")}</span>
        <input type="date" className="field" value={f.workedOn} onChange={(e) => setF({ ...f, workedOn: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("kk.fl.hours")}</span>
        <input className="field tabular-nums" inputMode="decimal" value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })} required />
      </label>
      <div>
        <label>
          <span className="label">{t("kk.fl.rate")}</span>
          <AmountInput value={f.rate} onChange={(e) => setF({ ...f, rate: e.target.value })} required aria-describedby="kk-fl-rate-hint" />
        </label>
        <p id="kk-fl-rate-hint" className="mt-1 text-xs text-ink-muted">
          {t("kk.fl.rateHint")}
        </p>
      </div>
      <label className="md:col-span-2">
        <span className="label">{t("kk.note")}</span>
        <input className="field" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
      </label>
      <label className="flex items-center gap-2 md:col-span-2">
        <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
        {t("kk.fl.paid")}
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary justify-self-start md:col-span-2" disabled={save.isPending}>
        {t("kk.fl.addButton")}
      </button>
    </form>
  );
}
