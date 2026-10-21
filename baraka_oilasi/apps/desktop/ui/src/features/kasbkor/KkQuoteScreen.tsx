import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkQuoteInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";

const FIELDS = ["material", "hours", "hourlyRate", "travel", "depreciation", "reservePercent", "price", "advance"] as const;
type Field = (typeof FIELDS)[number];
const MONEY: Field[] = ["material", "hourlyRate", "travel", "depreciation", "price", "advance"];

/**
 * Buyurtma kalkulyatori (kasbkor/SPEC 3.2): tannarx, narx tannarxdan past bo'lsa — ogohlantirish,
 * avans materialga yetadimi. Hisob yadroda; hech narsa saqlanmaydi.
 */
export function KkQuoteScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [f, setF] = useState<Record<Field, string>>({ material: "", hours: "", hourlyRate: "", travel: "", depreciation: "", reservePercent: "", price: "", advance: "" });
  const quote = useMutation({
    mutationFn: () => {
      const input = Object.fromEntries(FIELDS.map((k) => [k, f[k].trim() || null])) as KkQuoteInput;
      return call(commands.kkOrderQuote(spaceId, input));
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    quote.mutate();
  };
  const q = quote.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.q.title")}</h1>
      <p className="text-ink-muted">{t("kk.q.intro")}</p>
      <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("kk.q.title")}>
        {FIELDS.map((k) => (
          <label key={k}>
            <span className="label">{t(`kk.q.${k}`)}</span>
            {MONEY.includes(k) ? (
              <AmountInput value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} />
            ) : (
              <input className="field tabular-nums" inputMode="decimal" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} />
            )}
          </label>
        ))}
        <div className="md:col-span-2">
          <ErrorText error={quote.error} />
        </div>
        <button className="btn-primary justify-self-start md:col-span-2" disabled={quote.isPending}>
          {t("kk.q.calculate")}
        </button>
      </form>
      {q && (
        <section className="card flex flex-col gap-3" aria-label={t("kk.q.result")} aria-live="polite">
          <h2 className="text-lg font-semibold">{t("kk.q.result")}</h2>
          <table className="w-full text-sm">
            <tbody>
              {(
                [
                  ["kk.q.labor", q.labor.formatted],
                  ["kk.q.subtotal", q.subtotal.formatted],
                  ["kk.q.reserve", q.reserve.formatted],
                ] as const
              ).map(([k, v]) => (
                <tr key={k} className="border-t border-line">
                  <th scope="row" className="py-1 pr-3 text-left font-normal">
                    {t(k)}
                  </th>
                  <td className="py-1 text-right tabular-nums">{v}</td>
                </tr>
              ))}
              <tr className="border-t border-line font-semibold">
                <th scope="row" className="py-1 pr-3 text-left">
                  {t("kk.q.cost")}
                </th>
                <td data-testid="kk-quote-cost" className="py-1 text-right tabular-nums">
                  {q.cost.formatted}
                </td>
              </tr>
            </tbody>
          </table>
          {q.margin && q.laborPaid && (
            <p role={q.belowCost ? "alert" : "status"} data-testid="kk-quote-verdict" className={q.belowCost ? "text-warn" : ""}>
              {q.belowCost
                ? t(q.effectiveHourlyRate ? "kk.q.belowCost" : "kk.q.belowCostNoHours", { margin: q.margin.formatted, labor: q.laborPaid.formatted, hourly: q.effectiveHourlyRate?.formatted ?? "" })
                : t(q.effectiveHourlyRate ? "kk.q.aboveCost" : "kk.q.aboveCostNoHours", { margin: q.margin.formatted, labor: q.laborPaid.formatted, hourly: q.effectiveHourlyRate?.formatted ?? "" })}
            </p>
          )}
          {q.materialShortfall && q.advanceAfterMaterial && (
            <p data-testid="kk-quote-advance">
              {q.materialShortfall.minor !== "0"
                ? t("kk.q.advanceShort", { amount: q.materialShortfall.formatted })
                : t("kk.q.advanceCovers", { amount: q.advanceAfterMaterial.formatted })}
            </p>
          )}
        </section>
      )}
    </section>
  );
}
