import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";

/** Qarzdan chiqish rejalovchisi: odatiy va tezlashtirilgan grafik (hisob — yadroda). */
export function LoanScreen() {
  const { t } = useTranslation();
  const [principal, setPrincipal] = useState("");
  const [rateBp, setRateBp] = useState("2400");
  const [months, setMonths] = useState("14");
  const [extra, setExtra] = useState("0");

  const sim = useMutation({
    mutationFn: () => {
      // bp va oylar soni — pul emas, butun son; noto'g'ri qiymat yadroga yuborilmaydi.
      if (!/^\d+$/.test(rateBp) || !/^\d+$/.test(months)) {
        return Promise.reject(new CoreError({ code: "INVALID_NUMBER", field: null }));
      }
      return call(
        commands.simulateLoan({
          principal,
          currency: "UZS",
          annualBp: Number(rateBp),
          months: Number(months),
          kind: "ANNUITY",
          extraPerMonth: extra,
        }),
      );
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    sim.mutate();
  };

  const r = sim.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("loan.title")}</h1>
      <form className="card grid gap-4 md:grid-cols-4" onSubmit={submit}>
        <label>
          <span className="label">{t("loan.principal")}</span>
          <AmountInput value={principal} onChange={(e) => setPrincipal(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("loan.rateBp")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={rateBp} onChange={(e) => setRateBp(e.target.value)} />
        </label>
        <label>
          <span className="label">{t("loan.months")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={months} onChange={(e) => setMonths(e.target.value)} />
        </label>
        <label>
          <span className="label">{t("loan.extra")}</span>
          <AmountInput value={extra} onChange={(e) => setExtra(e.target.value)} />
        </label>
        <div className="md:col-span-4"><ErrorText error={sim.error} /></div>
        <div><button className="btn-primary" disabled={sim.isPending}>{t("common.save")}</button></div>
      </form>
      {r && (
        <>
          <div className="card">
            <p className="text-xl font-semibold text-accent">{t("loan.result", { months: r.monthsSaved, amount: r.interestSaved.formatted })}</p>
            <p className="mt-1 text-sm text-ink-muted">{t("loan.estimate")}</p>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="text-left text-ink-muted">
                  {(["month", "interest", "principal", "extra", "balance"] as const).map((c) => (
                    <th key={c} className="py-1 pr-4 font-normal">{t(`loan.col.${c}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {r.acceleratedSchedule.map((row) => (
                  <tr key={row.month} className="border-b border-line">
                    <td className="py-1 pr-4 text-ink-muted">{row.month}</td>
                    <td className="py-1 pr-4">{row.interest.formatted}</td>
                    <td className="py-1 pr-4">{row.principal.formatted}</td>
                    <td className="py-1 pr-4">{row.extra.formatted}</td>
                    <td className="py-1">{row.balance.formatted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
