import { useTranslation } from "react-i18next";

import type { BorrowCheckInput } from "../bindings";

const ALTERNATIVES = ["QOROVUL", "RELATIVE", "SELL_ITEM"] as const;

/** «Toʻxta va oʻyla» savollari (uy/SPEC 2D.6). Taqiqlamaydi — faqat soʻraydi. */
export function BorrowCheckFields({ value, onChange }: { value: BorrowCheckInput; onChange: (v: BorrowCheckInput) => void }) {
  const { t } = useTranslation();
  const toggle = (a: string) =>
    onChange({ ...value, alternatives: value.alternatives.includes(a) ? value.alternatives.filter((x) => x !== a) : [...value.alternatives, a] });
  return (
    <fieldset className="rounded-md border border-line p-4 md:col-span-2">
      <legend className="px-1 text-sm font-semibold text-accent-text">{t("friction.title")}</legend>
      <p className="mb-3 text-sm text-ink-muted">{t("friction.intro")}</p>
      <div className="mb-3 flex flex-wrap gap-4" role="radiogroup" aria-label={t("friction.need")}>
        {(["NECESSITY", "LUXURY"] as const).map((n) => (
          <label key={n} className="flex items-center gap-2">
            <input type="radio" name="need" checked={value.need === n} onChange={() => onChange({ ...value, need: n })} />
            {t(`friction.need.${n}`)}
          </label>
        ))}
      </div>
      <p className="label">{t("friction.alternatives")}</p>
      <div className="flex flex-wrap gap-4">
        {ALTERNATIVES.map((a) => (
          <label key={a} className="flex items-center gap-2">
            <input type="checkbox" checked={value.alternatives.includes(a)} onChange={() => toggle(a)} />
            {t(`friction.alt.${a}`)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
