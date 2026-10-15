import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

/** Bosh sahifa: 1-raqam — «Oʻzingizga toʻlangan (shu oy)», keyin odat va oy yakuni. */
export function HomeScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const openIncome = useUi((s) => s.openIncome);
  const summary = useQuery({ queryKey: keys.summary(spaceId, null), queryFn: () => call(commands.monthlySummary(spaceId, null, null)) });
  const vault = useQuery({ queryKey: keys.vault(spaceId), queryFn: () => call(commands.vault(spaceId)) });

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
      <div>
        <button className="btn-primary" onClick={openIncome}>
          {t("home.quickIncome")} <kbd className="text-xs opacity-80">Ctrl+N</kbd>
        </button>
      </div>
    </section>
  );
}
