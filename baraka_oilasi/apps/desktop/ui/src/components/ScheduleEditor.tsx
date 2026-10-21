import { useTranslation } from "react-i18next";

import type { ScheduleLineInput } from "../bindings";
import { AmountInput } from "./AmountInput";

/** Toʻlov rejasi qatorlari: sana va summa matn sifatida yadroga yuboriladi (tekshiruv — yadroda). */
export function ScheduleEditor({ value, onChange }: { value: ScheduleLineInput[]; onChange: (rows: ScheduleLineInput[]) => void }) {
  const { t } = useTranslation();
  const setLine = (i: number, patch: Partial<ScheduleLineInput>) => onChange(value.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <fieldset className="md:col-span-2">
      <legend className="label">{t("receipt.schedule")}</legend>
      <div className="flex flex-col gap-2">
        {value.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              aria-label={`${t("receipt.lineDate")} ${i + 1}`}
              inputMode="numeric"
              placeholder="15.11.2026"
              className="field max-w-40 tabular-nums"
              value={row.date}
              onChange={(e) => setLine(i, { date: e.target.value })}
              required
            />
            <AmountInput aria-label={`${t("common.amount")} ${i + 1}`} value={row.amount} onChange={(e) => setLine(i, { amount: e.target.value })} required />
            <button type="button" className="btn-ghost" disabled={value.length === 1} onClick={() => onChange(value.filter((_, j) => j !== i))}>
              {t("receipt.removeLine")}
            </button>
          </div>
        ))}
      </div>
      <button type="button" className="btn-ghost mt-2" onClick={() => onChange([...value, { date: "", amount: "" }])}>
        {t("receipt.addLine")}
      </button>
    </fieldset>
  );
}
