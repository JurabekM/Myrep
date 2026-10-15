import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "./command-error";
import { financeKeys } from "./queries";
import { Card, Stat } from "./ui";

/** Darvoza sababi → tarjima kaliti. */
function reasonKey(code: string) {
  switch (code) {
    case "INTEREST_DEBT_WITHOUT_PLAN":
      return "reserve.reasonDebt" as const;
    default:
      return "reserve.reasonReserve" as const;
  }
}

/** O'ndan bir oylarni «1,4» ko'rinishida yozadi (ko'rsatish uchun; hisob Rustda). */
export function tenthsText(tenths: number): string {
  return `${String(Math.floor(tenths / 10))},${String(tenths % 10)}`;
}

/**
 * «Qorovul» zaxirasi (SPEC 2C.3–2C.4): maqsad 3 / 6 oy, «necha oylik zaxira bor» progressi va
 * tayyorgarlik darvozasi. Taqiq yo'q — tushuntirish bor; raqamlar backend'dan tayyor keladi.
 */
export function ReserveCard() {
  const { t } = useTranslation();
  const reserve = useQuery({
    queryKey: financeKeys.reserve,
    queryFn: () => commands.getReserve().then(unwrap),
  });

  if (!reserve.isSuccess) {
    return null;
  }
  const data = reserve.data;
  const tenths = data.reserveMonthsTenths;
  const percent =
    tenths === null ? 0 : Math.min(100, Math.round((tenths / (data.targetMonths * 10)) * 100));

  return (
    <Card title={t("reserve.title")}>
      <p className="text-sm text-muted">{t("reserve.intro")}</p>
      {data.targetFull === null ? (
        <p className="text-sm text-muted">{t("reserve.noData", { months: data.dataMonths })}</p>
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-3">
            <Stat
              label={t("reserve.monthlyAverage")}
              value={data.monthlyAverage?.formatted ?? "—"}
              hint={t("reserve.monthlyAverageHint")}
            />
            <Stat label={t("reserve.targetFirst")} value={data.targetFirst?.formatted ?? "—"} />
            <Stat label={t("reserve.targetFull")} value={data.targetFull.formatted} />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted">{t("reserve.progressLabel")}</span>
              <span className="text-text">
                {t("reserve.progressValue", {
                  have: tenths === null ? "0,0" : tenthsText(tenths),
                  target: data.targetMonths,
                })}
              </span>
            </div>
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label={t("reserve.progressLabel")}
              className="h-2 w-full overflow-hidden rounded-full bg-raised"
            >
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${String(percent)}%` }}
              />
            </div>
          </div>
        </>
      )}
      <div className="rounded-lg border border-border bg-app px-4 py-3">
        <p className="text-sm font-medium text-text">
          {data.gate === "OPEN" ? t("reserve.gateOpen") : t("reserve.gateLocked")}
        </p>
        {data.reasons.length > 0 ? (
          <ul className="mt-1 list-disc pl-5 text-sm text-muted">
            {data.reasons.map((reason) => (
              <li key={reason}>{t(reasonKey(reason))}</li>
            ))}
          </ul>
        ) : null}
        <p className="mt-1 text-xs text-subtle">{t("reserve.gateHint")}</p>
      </div>
    </Card>
  );
}
