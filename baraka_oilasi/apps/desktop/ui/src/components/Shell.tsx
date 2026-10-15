import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../bindings";
import { AuditScreen } from "../features/audit/AuditScreen";
import { LoanScreen } from "../features/debts/LoanScreen";
import { ExpensesScreen } from "../features/expenses/ExpensesScreen";
import { HomeScreen } from "../features/home/HomeScreen";
import { IncomeDialog } from "../features/income/IncomeDialog";
import { VaultScreen } from "../features/vault/VaultScreen";
import { call } from "../lib/api";
import { keys, resetAfterLock } from "../lib/queryClient";
import { type Screen, useUi } from "../state/ui";
import { Mentor } from "./Mentor";

const NAV: { screen: Screen; label: string }[] = [
  { screen: "home", label: "nav.home" },
  { screen: "vault", label: "nav.vault" },
  { screen: "expenses", label: "nav.expenses" },
  { screen: "audit", label: "nav.audit" },
  { screen: "debts", label: "nav.debts" },
];

const MENTOR: Record<Screen, string> = {
  home: "mentor.home",
  vault: "mentor.vault",
  expenses: "mentor.expenses",
  audit: "mentor.audit",
  debts: "mentor.debts",
};

/** Asosiy oyna: chapda navigatsiya va makonlar, markazda ish maydoni, oʻngda Sobir hoji. */
export function Shell() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { screen, setScreen, spaceId, setSpace, incomeOpen, openIncome, closeIncome } = useUi();
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const lock = useMutation({ mutationFn: () => call(commands.lock()), onSettled: () => resetAfterLock(qc) });

  const spaces = household.data?.spaces ?? [];
  const active = spaceId ?? spaces[0]?.id ?? null;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        openIncome();
      } else if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        lock.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openIncome, lock]);

  return (
    <div className="flex h-full">
      <nav aria-label="Asosiy" className="flex w-60 shrink-0 flex-col gap-1 border-r border-line p-4">
        <p className="mb-4 font-serif text-xl font-semibold">{t("app.name")}</p>
        <div className="mb-4 flex flex-wrap gap-1">
          {spaces.map((s) => (
            <button key={s.id} aria-pressed={s.id === active} className={s.id === active ? "btn-primary px-3 py-1 text-sm" : "btn-ghost px-3 py-1 text-sm"} onClick={() => setSpace(s.id)}>
              {t(`space.${s.kind}`)}
            </button>
          ))}
        </div>
        {NAV.map((n) => (
          <button
            key={n.screen}
            aria-current={screen === n.screen ? "page" : undefined}
            className={`rounded-md px-3 py-2 text-left ${screen === n.screen ? "bg-surface font-medium" : "hover:bg-surface"}`}
            onClick={() => setScreen(n.screen)}
          >
            {t(n.label)}
          </button>
        ))}
        <button className="btn-ghost mt-auto" onClick={() => lock.mutate()}>
          {t("nav.lock")} <kbd className="text-xs opacity-70">Ctrl+L</kbd>
        </button>
      </nav>
      <main className="min-w-0 flex-1 overflow-y-auto p-8">
        {active && screen === "home" && <HomeScreen spaceId={active} />}
        {active && screen === "vault" && <VaultScreen spaceId={active} />}
        {active && screen === "expenses" && <ExpensesScreen spaceId={active} />}
        {active && screen === "audit" && <AuditScreen spaceId={active} />}
        {screen === "debts" && <LoanScreen />}
      </main>
      <Mentor tipKey={MENTOR[screen]} />
      {incomeOpen && active && <IncomeDialog spaceId={active} onClose={closeIncome} />}
    </div>
  );
}
