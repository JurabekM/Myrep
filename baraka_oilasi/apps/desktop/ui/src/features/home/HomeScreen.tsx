import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { commands, type NudgeDto } from "../../bindings";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { showDate } from "../../lib/date";
import { useUi } from "../../state/ui";
import { ReminderText } from "../governance/GovernanceView";

/** Bosh sahifa: 1-raqam — «Oʻzingizga toʻlangan (shu oy)», keyin odat va oy yakuni. */
export function HomeScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const openIncome = useUi((s) => s.openIncome);
  const openOffer = useUi((s) => s.openOffer);
  const summary = useQuery({ queryKey: keys.summary(spaceId, null), queryFn: () => call(commands.monthlySummary(spaceId, null, null)) });
  const vault = useQuery({ queryKey: keys.vault(spaceId), queryFn: () => call(commands.vault(spaceId)) });
  const debts = useQuery({ queryKey: keys.debts(spaceId), queryFn: () => call(commands.debtsOverview(spaceId)) });
  const nudges = useQuery({ queryKey: keys.nudges(spaceId), queryFn: () => call(commands.homeNudges(spaceId)) });
  const reminders = useQuery({ queryKey: keys.reminders(spaceId), queryFn: () => call(commands.agreementReminders(spaceId)) });
  const setScreen = useUi((s) => s.setScreen);
  const openPartnership = useUi((s) => s.openPartnership);
  const free = debts.data?.debtFreeDate;

  return (
    <section className="flex flex-col gap-5">
      {(nudges.data ?? []).length > 0 && <Nudges items={nudges.data ?? []} />}
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
      {(reminders.data ?? []).length > 0 && (
        <section aria-label={t("home.reminders")} className="card flex flex-col gap-2 border-warn">
          <p className="text-sm text-ink-muted">{t("home.reminders")}</p>
          {(reminders.data ?? []).map((r) => (
            <button
              key={`${r.refId}-${r.kind}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded px-2 py-1 text-left hover:bg-paper"
              onClick={() => (r.agreementType === "PARTNERSHIP" ? openPartnership(r.refId, "governance") : setScreen("agreements"))}
            >
              <span>
                <span className="font-medium">{t(`home.reminder.${r.agreementType}.${r.kind}`)}</span> · {r.title}
              </span>
              <span className="text-sm">
                <ReminderText r={r} />
              </span>
            </button>
          ))}
        </section>
      )}
      <div>
        <button className="btn-primary" onClick={openIncome}>
          {t("home.quickIncome")} <kbd className="text-xs">Ctrl+N</kbd>
        </button>
        <button className="btn-ghost ml-2" onClick={openOffer}>
          {t("offer.open")}
        </button>
      </div>
    </section>
  );
}

/** Yumshoq eslatmalar (U15): daromad ritmi, qarzlarni yozish, oylik zaxira nusxa. */
function Nudges({ items }: { items: NudgeDto[] }) {
  const { t } = useTranslation();
  const openIncome = useUi((s) => s.openIncome);
  const setScreen = useUi((s) => s.setScreen);
  const settings = useQuery({ queryKey: keys.settings, queryFn: () => call(commands.settings()) });
  const dismissDebts = useMutation({
    mutationFn: () =>
      call(
        commands.updateSettings({
          locale: settings.data?.deviceLocale ?? null,
          incomeRhythm: settings.data?.incomeRhythm ?? null,
          debtsDeclared: false,
        }),
      ),
  });
  const action: Record<string, () => void> = {
    INCOME_TODAY: openIncome,
    INCOME_QUIET: openIncome,
    PAYDAY: openIncome,
    DEBT_INVENTORY: () => setScreen("inventory"),
    BACKUP: () => setScreen("sync"),
  };
  return (
    <section aria-label={t("nudge.title")} className="flex flex-col gap-2">
      {items.map((n) => (
        <div key={n.kind} data-testid={`nudge-${n.kind}`} className="card flex flex-wrap items-center justify-between gap-3 border-accent/60 py-3">
          <p className="min-w-0 flex-1 basis-72">{t(n.kind === "INCOME_QUIET" && n.days === null ? "nudge.INCOME_NONE" : `nudge.${n.kind}`, { count: n.days ?? 0 })}</p>
          <div className="flex gap-2">
            <button className="btn-primary px-3 py-1.5 text-sm" onClick={action[n.kind]}>
              {t(`nudge.action.${n.kind}`)}
            </button>
            {n.kind === "DEBT_INVENTORY" && (
              <button className="btn-ghost px-3 py-1.5 text-sm" disabled={!settings.data || dismissDebts.isPending} onClick={() => dismissDebts.mutate()}>
                {t("nudge.dismiss")}
              </button>
            )}
          </div>
        </div>
      ))}
    </section>
  );
}
