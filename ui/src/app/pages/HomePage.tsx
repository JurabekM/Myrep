import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AppInfoCard } from "../components/AppInfoCard";
import { Alert, Card, PageHeader, PrimaryButton, SecondaryButton, Stat } from "../finance/ui";
import { fetchers, financeKeys } from "../finance/queries";
import { useUiStore } from "../store";

/** Bosh sahifa: 1-raqam («O'zingizga to'langan»), «Kelajagim», odat, audit holati va tezkor harakatlar. */
export function HomePage() {
  const { t } = useTranslation();
  const setPage = useUiStore((state) => state.setPage);
  const setQuickEntryOpen = useUiStore((state) => state.setQuickEntryOpen);
  const home = useQuery({ queryKey: financeKeys.home, queryFn: fetchers.home });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("home.greeting")} subtitle={t("home.subtitle")} />

      {home.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
      {home.isError ? <Alert>{t("errors.generic")}</Alert> : null}

      {home.data !== undefined ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2">
            <Card>
              <Stat label={t("home.kpi.paidToSelf")} value={home.data.paidToSelf.formatted} />
            </Card>
            <Card>
              <Stat label={t("home.kpi.vault")} value={home.data.vaultBalance.formatted} />
            </Card>
            <Card>
              <Stat label={t("home.kpi.income")} value={home.data.income.formatted} />
            </Card>
            <Card>
              <Stat
                label={t("home.kpi.monthResult")}
                value={home.data.monthResult.formatted}
                hint={t("home.kpi.monthResultHint")}
              />
            </Card>
          </section>

          <Card title={t("home.habit.title")}>
            <p className="text-base text-text">
              {home.data.habit.currentStreakWeeks > 0
                ? t("home.habit.streak", { weeks: home.data.habit.currentStreakWeeks })
                : t("home.habit.noStreak")}
            </p>
            <p className="text-sm text-muted">
              {home.data.habit.thisWeekDone
                ? t("home.habit.thisWeekDone")
                : t("home.habit.thisWeekPending")}
            </p>
          </Card>

          <Card title={t("home.audit.title")}>
            {home.data.audit.done ? (
              <p className="text-base text-muted">{t("home.audit.done")}</p>
            ) : (
              <div className="flex flex-col gap-4">
                <p className="text-base text-muted">{t("home.audit.pending")}</p>
                <div>
                  <PrimaryButton
                    onClick={() => {
                      setPage("audit");
                    }}
                  >
                    {t("home.audit.start")}
                  </PrimaryButton>
                </div>
              </div>
            )}
          </Card>
        </>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <PrimaryButton
          onClick={() => {
            setQuickEntryOpen(true);
          }}
        >
          {t("home.actions.income")}
        </PrimaryButton>
        <SecondaryButton
          onClick={() => {
            setPage("future");
          }}
        >
          {t("home.actions.vault")}
        </SecondaryButton>
        <SecondaryButton
          onClick={() => {
            setPage("whose-money");
          }}
        >
          {t("home.actions.whoseMoney")}
        </SecondaryButton>
        <SecondaryButton
          onClick={() => {
            setPage("obligations");
          }}
        >
          {t("home.actions.obligations")}
        </SecondaryButton>
      </div>

      <AppInfoCard />
    </div>
  );
}
