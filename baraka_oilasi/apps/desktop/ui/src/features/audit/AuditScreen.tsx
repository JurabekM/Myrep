import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

/** Oylik audit: daromad → majburiyatlar → xarajatlar → izohsiz qolgan summa (ayblovsiz). */
export function AuditScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [delta, setDelta] = useState("");
  const applied = delta.trim() === "" ? null : delta;
  const s = useQuery({ queryKey: keys.summary(spaceId, applied), queryFn: () => call(commands.monthlySummary(spaceId, null, applied)) });

  const rows = s.data
    ? [
        [t("audit.income"), s.data.income.formatted],
        [t("audit.obligations"), s.data.obligationsPaid.formatted],
        [t("audit.expenses"), s.data.expenses.formatted],
        [t("audit.vaultNet"), s.data.vaultNet.formatted],
        [t("audit.balanceDelta"), s.data.balanceDelta.formatted],
      ]
    : [];

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("audit.title")}</h1>
      <p className="text-sm text-ink-muted">{s.data ? `${s.data.periodStart} — ${s.data.periodEnd}` : ""}</p>
      <div className="card">
        <dl className="divide-y divide-line">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between py-2">
              <dt>{label}</dt>
              <dd className="tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <label className="max-w-sm">
        <span className="label">{t("audit.balanceDelta")}</span>
        <AmountInput value={delta} onChange={(e) => setDelta(e.target.value)} />
      </label>
      <ErrorText error={s.error} />
      {s.data && (
        <div className="card">
          <p className="text-sm text-ink-muted">{t("audit.gap")}</p>
          <p data-testid="gap" className="kpi">{s.data.unexplainedGap.formatted}</p>
          <p className="mt-2 text-sm">{t("audit.gapHint")}</p>
        </div>
      )}
    </section>
  );
}
