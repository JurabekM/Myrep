import { useTranslation } from "react-i18next";

import type { MfShareDto, MfShareInput } from "../../bindings";

/** Maqsadlar (yadrodagi kanonik tartib). */
export const PURPOSES = ["HOUSEHOLD", "DEBT", "BUILD", "EDUCATION", "CEREMONY", "SAVINGS", "OTHER"] as const;

/** Maqsad → foiz matni (bo'sh — kiritilmagan). Tekshiruv (yig'indi 100 %) — yadroda. */
export type SharesDraft = Partial<Record<(typeof PURPOSES)[number], string>>;

export const DEFAULT_DRAFT: SharesDraft = { HOUSEHOLD: "100" };

export function draftFrom(shares: MfShareDto[] | undefined): SharesDraft {
  if (!shares || shares.length === 0) return DEFAULT_DRAFT;
  return Object.fromEntries(shares.map((s) => [s.purpose, s.percent]));
}

export function sharesInput(d: SharesDraft): MfShareInput[] {
  return PURPOSES.filter((p) => (d[p] ?? "").trim() !== "").map((p) => ({ purpose: p, percent: (d[p] ?? "").trim() }));
}

/** «Ikki qirg'oq» ulushlari: har maqsad uchun foiz. */
export function PurposeShares({ value, onChange, legend }: { value: SharesDraft; onChange: (d: SharesDraft) => void; legend: string }) {
  const { t } = useTranslation();
  return (
    <fieldset>
      <legend className="label">{legend}</legend>
      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        {PURPOSES.map((p) => (
          <label key={p} className="flex items-center justify-between gap-2 text-sm">
            <span>{t(`mf.purpose.${p}`)}</span>
            <span className="flex items-center gap-1">
              <input
                className="field w-20 py-1 text-right tabular-nums"
                inputMode="decimal"
                aria-label={t("mf.sharePercent", { purpose: t(`mf.purpose.${p}`) })}
                value={value[p] ?? ""}
                onChange={(e) => onChange({ ...value, [p]: e.target.value })}
              />
              <span aria-hidden="true" className="text-ink-muted">
                %
              </span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
