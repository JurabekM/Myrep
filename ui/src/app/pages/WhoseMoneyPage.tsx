import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, Card, PageHeader, SecondaryButton, Stat } from "../finance/ui";
import { ownerKey } from "../finance/labels";
import { fetchers, financeKeys } from "../finance/queries";

/** Ko'rish mumkin bo'lgan eng uzoq oy (oy ortga). */
const MAX_MONTHS_BACK = 24;

/**
 * «Kimning puli?» (SPEC 2.4): daromad kimlarga ketgani. Bo'lak kengligi — backend hisoblagan ulush (bp).
 */
export function WhoseMoneyPage() {
  const { t } = useTranslation();
  const [monthsBack, setMonthsBack] = useState(0);
  const whose = useQuery({
    queryKey: financeKeys.whose(monthsBack),
    queryFn: () => fetchers.whose(monthsBack),
  });
  const data = whose.data;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("whoseMoney.title")} subtitle={t("whoseMoney.subtitle")} />

      <div className="flex flex-wrap items-center gap-2">
        <SecondaryButton
          disabled={monthsBack >= MAX_MONTHS_BACK}
          onClick={() => {
            setMonthsBack((current) => current + 1);
          }}
        >
          {t("whoseMoney.older")}
        </SecondaryButton>
        <span className="text-sm text-muted">
          {monthsBack === 0 || data === undefined
            ? t("whoseMoney.current")
            : t("whoseMoney.period", { start: data.periodStart })}
        </span>
        <SecondaryButton
          disabled={monthsBack === 0}
          onClick={() => {
            setMonthsBack((current) => Math.max(0, current - 1));
          }}
        >
          {t("whoseMoney.newer")}
        </SecondaryButton>
      </div>

      <Card>
        {whose.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
        {whose.isError ? <Alert>{t("errors.generic")}</Alert> : null}
        {data !== undefined ? (
          <>
            <Stat label={t("whoseMoney.total")} value={data.total.formatted} />
            {data.parts.length === 0 ? (
              <p className="text-sm text-muted">{t("whoseMoney.empty")}</p>
            ) : (
              <ul className="flex flex-col gap-4">
                {data.parts.map((part) => (
                  <li key={part.owner} className="flex flex-col gap-2">
                    <div className="flex items-center justify-between gap-4 text-sm">
                      <span className="text-text">{t(ownerKey(part.owner))}</span>
                      <span className="text-muted">{part.amount.formatted}</span>
                    </div>
                    <div
                      role="meter"
                      aria-label={t(ownerKey(part.owner))}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={part.shareBp / 100}
                      className="h-2 w-full overflow-hidden rounded-full bg-raised"
                    >
                      <div
                        className="h-2 rounded-full bg-accent"
                        style={{ width: `${String(part.shareBp / 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : null}
      </Card>
    </div>
  );
}
