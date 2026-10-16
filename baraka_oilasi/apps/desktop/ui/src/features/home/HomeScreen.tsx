import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { showDate } from "../../lib/date";
import { useUi } from "../../state/ui";

/** Bosh sahifa: 1-raqam — «Oʻzingizga toʻlangan (shu oy)», keyin odat va oy yakuni. */
export function HomeScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const openIncome = useUi((s) => s.openIncome);
  const openOffer = useUi((s) => s.openOffer);
  const summary = useQuery({ queryKey: keys.summary(spaceId, null), queryFn: () => call(commands.monthlySummary(spaceId, null, null)) });
  const vault = useQuery({ queryKey: keys.vault(spaceId), queryFn: () => call(commands.vault(spaceId)) });
  const debts = useQuery({ queryKey: keys.debts(spaceId), queryFn: () => call(commands.debtsOverview(spaceId)) });
  const setScreen = useUi((s) => s.setScreen);
  const free = debts.data?.debtFreeDate;

  return (
    <section className="flex flex-col gap-5">
      <div className="card">
        <p className="text-sm text-ink-muted">{t("home.paidToSelf")}</p>
        <p data-testid="kpi-paid-to-self" className="kpi text-accent">{summary.data?.paidToSelf.formatted ?? "…"}</p>
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <div className="card">
          <p className="text-sm text-ink-muted">{t("home.vault")}</p>
          <p className="text-lg font-medium">{vault.data ? t("home.streak", { count: vault.data.streak.currentWeeks }) : "…"}</p>
          <p className="kpi">{vault.data?.balance.formatted ?? "…"}</p>
        </div>
        <div className="card">
          <p className="text-sm text-ink-muted">{t("home.monthResult")}</p>
          <p className="kpi">{summary.data?.monthResult.formatted ?? "…"}</p>
        </div>
      </div>
      {free && (
        <button className="card text-left hover:border-accent" onClick={() => setScreen("debts")}>
          <p className="text-sm text-ink-muted">{t("home.debtFree")}</p>
          <p data-testid="kpi-debt-free" className="kpi text-accent">{showDate(free)}</p>
          <p className="text-sm text-ink-muted">
            {t("payoff.months", { count: debts.data?.debtFreeMonths ?? 0 })}
            {debts.data?.debtFreeDateWithPlan ? ` · ${t("home.withPlan", { date: showDate(debts.data.debtFreeDateWithPlan) })}` : ""}
          </p>
        </button>
      )}
      <div>
        <button className="btn-primary" onClick={openIncome}>
          {t("home.quickIncome")} <kbd className="text-xs opacity-80">Ctrl+N</kbd>
        </button>
        <button className="btn-ghost ml-2" onClick={openOffer}>
          {t("offer.open")}
        </button>
      </div>
    </section>
  );
}
