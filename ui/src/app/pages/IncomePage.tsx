import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Alert, Card, PageHeader, PrimaryButton } from "../finance/ui";
import { fetchers, financeKeys } from "../finance/queries";
import { useUiStore } from "../store";

/** Shu oydagi daromadlar ro'yxati. Yangi daromad — Ctrl+N yoki tugma bilan. */
export function IncomePage() {
  const { t } = useTranslation();
  const setQuickEntryOpen = useUiStore((state) => state.setQuickEntryOpen);
  const incomes = useQuery({ queryKey: financeKeys.incomes, queryFn: fetchers.incomes });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("income.title")} subtitle={t("income.subtitle")} />

      <div>
        <PrimaryButton
          onClick={() => {
            setQuickEntryOpen(true);
          }}
        >
          {t("income.new")}
        </PrimaryButton>
      </div>

      <Card>
        {incomes.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
        {incomes.isError ? <Alert>{t("errors.generic")}</Alert> : null}
        {incomes.data?.length === 0 ? (
          <p className="text-sm text-muted">{t("income.empty")}</p>
        ) : null}
        {incomes.data !== undefined && incomes.data.length > 0 ? (
          <ul className="flex flex-col divide-y divide-border">
            {incomes.data.map((income) => (
              <li key={income.id} className="flex items-center justify-between gap-4 py-3">
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-base text-text">{income.source}</span>
                  <span className="text-xs text-subtle">
                    {income.channel === "CASH" ? t("quickEntry.cash") : t("quickEntry.card")} ·{" "}
                    {income.occurredOn}
                  </span>
                </span>
                <span className="shrink-0 text-base font-medium text-text">
                  {income.amount.formatted}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}
