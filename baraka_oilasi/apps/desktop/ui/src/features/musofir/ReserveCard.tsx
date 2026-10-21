import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { commands, type MfOverviewDto, type MfReserveDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import type { MfEntryMode } from "./MfEntryDialog";

const TONE: Record<string, string> = { FULL: "text-accent-text", PARTIAL: "text-warn", EMPTY: "text-warn", NO_HISTORY: "text-ink-muted" };
const ACTIONS: MfEntryMode[] = ["RESERVE_IN", "RESERVE_OUT", "RESERVE_OPENING"];

/**
 * Qorovul pul (musofir/SPEC 6.4): chet eldagi kutilmagan xarajat uchun alohida pul. Maqsad — oxirgi
 * oylardagi o'rtacha xarajat × N oy; hammasi yadrodan. O'z ulushi avval shu yerga, keyin jamg'armaga.
 */
export function ReserveCard({ spaceId, d, r, onAction }: { spaceId: string; d: MfOverviewDto; r: MfReserveDto; onAction: (mode: MfEntryMode) => void }) {
  const { t } = useTranslation();
  const save = useMutation({
    mutationFn: (months: number) =>
      call(
        commands.mfSetPlan(spaceId, {
          reserveMonths: months,
          startup: d.startup?.startup.plain ?? null,
          startupIdeaId: d.startup?.ideaId ?? null,
        }),
      ),
  });
  return (
    <section className="card flex flex-col gap-3" aria-label={t("mf.reserve.title")}>
      <h2 className="text-lg font-semibold">{t("mf.reserve.title")}</h2>
      <p data-testid="mf-reserve" className="kpi text-accent">
        {r.balance.formatted}
      </p>
      <p data-testid="mf-reserve-status" className={`text-sm ${TONE[r.status] ?? ""}`}>
        {t(`mf.reserve.status.${r.status}`, { gap: r.gap?.formatted ?? "", count: r.months })}
      </p>
      {r.target && r.progressBp !== null && (
        <div>
          <div className="h-2 w-full overflow-hidden rounded bg-line" role="progressbar" aria-label={t("mf.reserve.progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.floor(r.progressBp / 100)}>
            <div className="h-full bg-accent" style={{ width: `${r.progressBp / 100}%` }} />
          </div>
          <p className="mt-1 text-xs text-ink-muted">{t("mf.reserve.progressLine", { percent: r.progressPercent, target: r.target.formatted })}</p>
        </div>
      )}
      {r.avgMonthly && <p className="text-sm text-ink-muted">{t("mf.reserve.avg", { amount: r.avgMonthly.formatted, count: r.monthsUsed })}</p>}
      <label>
        <span className="label">{t("mf.reserve.months")}</span>
        <select className="field w-40" value={r.months} disabled={save.isPending} onChange={(e) => save.mutate(Number(e.target.value))}>
          {[1, 2, 3].map((n) => (
            <option key={n} value={n}>
              {t("mf.months", { count: n })}
            </option>
          ))}
        </select>
      </label>
      <ErrorText error={save.error} />
      <div role="group" aria-label={t("mf.reserve.actions")} className="flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <button key={a} className="btn-ghost" onClick={() => onAction(a)}>
            {t(`mf.action.${a}`)}
          </button>
        ))}
      </div>
      <p className="text-xs text-ink-muted">{t("mf.reserve.hint")}</p>
    </section>
  );
}
