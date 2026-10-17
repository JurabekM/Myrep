import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../bindings";
import { AuditScreen } from "../features/audit/AuditScreen";
import { CeremoniesScreen } from "../features/ceremony/CeremoniesScreen";
import { ExpensesScreen } from "../features/expenses/ExpensesScreen";
import { AgreementsScreen } from "../features/governance/AgreementsScreen";
import { HomeScreen } from "../features/home/HomeScreen";
import { DebtsScreen } from "../features/inventory/DebtsScreen";
import { PartnershipsScreen } from "../features/partnership/PartnershipsScreen";
import { PayoffScreen } from "../features/payoff/PayoffScreen";
import { IncomeDialog } from "../features/income/IncomeDialog";
import { KkHomeScreen } from "../features/kasbkor/KkHomeScreen";
import { ReceiptScreen } from "../features/receipt/ReceiptScreen";
import { SettingsScreen } from "../features/settings/SettingsScreen";
import { SyncScreen } from "../features/sync/SyncScreen";
import { VaultScreen } from "../features/vault/VaultScreen";
import { IdeasScreen } from "../features/venture/IdeasScreen";
import { OfferCheckDialog } from "../features/venture/OfferCheckDialog";
import { call } from "../lib/api";
import { keys, resetAfterLock } from "../lib/queryClient";
import { type Screen, useUi } from "../state/ui";
import { CelebrationDialog } from "./CelebrationDialog";
import { Mentor } from "./Mentor";

const NAV: { screen: Screen; label: string }[] = [
  { screen: "home", label: "nav.home" },
  { screen: "vault", label: "nav.vault" },
  { screen: "expenses", label: "nav.expenses" },
  { screen: "audit", label: "nav.audit" },
  { screen: "inventory", label: "nav.inventory" },
  { screen: "debts", label: "nav.debts" },
  { screen: "ceremonies", label: "nav.ceremonies" },
  { screen: "partnerships", label: "nav.partnerships" },
  { screen: "ideas", label: "nav.ideas" },
  { screen: "agreements", label: "nav.agreements" },
  { screen: "receipt", label: "nav.receipt" },
  { screen: "sync", label: "nav.sync" },
  { screen: "settings", label: "nav.settings" },
];

/** Kasb-kor makonida (K1): bosh sahifa, sinxronlash va sozlamalar; qolgan bo'limlar keyingi vazifalarda. */
const KK_SCREENS: Screen[] = ["home", "sync", "settings"];

const MENTOR: Record<Screen, string> = {
  home: "mentor.home",
  vault: "mentor.vault",
  expenses: "mentor.expenses",
  audit: "mentor.audit",
  inventory: "mentor.inventory",
  debts: "mentor.debts",
  ceremonies: "mentor.ceremonies",
  partnerships: "mentor.partnerships",
  ideas: "mentor.ideas",
  agreements: "mentor.agreements",
  receipt: "mentor.receipt",
  sync: "mentor.sync",
  settings: "mentor.settings",
};

/** Asosiy oyna: chapda navigatsiya va makonlar, markazda ish maydoni, oʻngda Sobir hoji. */
export function Shell() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { screen: picked, setScreen, spaceId, setSpace, incomeOpen, openIncome, closeIncome, openKkEntry, celebration, closeCelebration, offerOpen, openOffer, closeOffer } = useUi();
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const settings = useQuery({ queryKey: keys.settings, queryFn: () => call(commands.settings()) });
  const lock = useMutation({ mutationFn: () => call(commands.lock()), onSettled: () => resetAfterLock(qc) });

  const spaces = household.data?.spaces ?? [];
  const active = spaceId ?? spaces[0]?.id ?? null;
  const kasbkor = spaces.find((s) => s.id === active)?.kind === "KASBKOR";
  const screen: Screen = kasbkor && !KK_SCREENS.includes(picked) ? "home" : picked;
  const nav = kasbkor ? NAV.filter((n) => KK_SCREENS.includes(n.screen)) : NAV;

  // Bazadagi til (shu qurilma yoki xonadon) — UI shu tilda; qulf ekrani uchun ham eslab qolinadi.
  const locale = settings.data?.locale;
  useEffect(() => {
    if (locale && locale !== i18n.language) void i18n.changeLanguage(locale);
  }, [locale, i18n]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        if (kasbkor) openKkEntry("SALE");
        else openIncome();
      } else if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        lock.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openIncome, openKkEntry, kasbkor, lock]);

  return (
    <div className="flex h-full">
      <a href="#main" className="skip-link">
        {t("a11y.skipToMain")}
      </a>
      <nav aria-label={t("a11y.mainNav")} className="flex w-60 shrink-0 flex-col gap-1 border-r border-line bg-sidebar p-4">
        <p className="mb-4 font-serif text-xl font-semibold">{t("app.name")}</p>
        <div role="group" aria-label={t("a11y.spaces")} className="mb-4 flex flex-wrap gap-1">
          {spaces.map((s) => (
            <button key={s.id} aria-pressed={s.id === active} className={s.id === active ? "btn-primary px-3 py-1 text-sm" : "btn-ghost px-3 py-1 text-sm"} onClick={() => setSpace(s.id)}>
              {t(`space.${s.kind}`)}
            </button>
          ))}
        </div>
        {nav.map((n) => (
          <button
            key={n.screen}
            aria-current={screen === n.screen ? "page" : undefined}
            className={`rounded-md px-3 py-2 text-left ${screen === n.screen ? "bg-surface font-medium text-ink" : "text-ink-muted hover:bg-surface hover:text-ink"}`}
            onClick={() => setScreen(n.screen)}
          >
            {t(n.label)}
          </button>
        ))}
        <button className="btn-ghost mt-auto text-sm" onClick={openOffer}>
          {t("offer.open")}
        </button>
        <button className="btn-ghost" onClick={() => lock.mutate()}>
          {t("nav.lock")} <kbd className="text-xs">Ctrl+L</kbd>
        </button>
      </nav>
      <main id="main" tabIndex={-1} className="min-w-0 flex-1 overflow-y-auto p-8 outline-none">
        {active && screen === "home" && (kasbkor ? <KkHomeScreen spaceId={active} /> : <HomeScreen spaceId={active} />)}
        {active && screen === "vault" && <VaultScreen spaceId={active} />}
        {active && screen === "expenses" && <ExpensesScreen spaceId={active} />}
        {active && screen === "audit" && <AuditScreen spaceId={active} />}
        {active && screen === "inventory" && <DebtsScreen spaceId={active} />}
        {active && screen === "debts" && <PayoffScreen spaceId={active} />}
        {active && screen === "ceremonies" && <CeremoniesScreen spaceId={active} />}
        {active && screen === "partnerships" && <PartnershipsScreen spaceId={active} />}
        {active && screen === "ideas" && <IdeasScreen spaceId={active} />}
        {active && screen === "agreements" && <AgreementsScreen spaceId={active} />}
        {active && screen === "receipt" && <ReceiptScreen spaceId={active} />}
        {screen === "sync" && <SyncScreen />}
        {screen === "settings" && <SettingsScreen />}
      </main>
      <Mentor tipKey={kasbkor && screen === "home" ? "mentor.kk" : MENTOR[screen]} />
      {incomeOpen && active && !kasbkor && <IncomeDialog spaceId={active} onClose={closeIncome} />}
      {offerOpen && <OfferCheckDialog onClose={closeOffer} />}
      {celebration && active && <CelebrationDialog spaceId={active} result={celebration} onClose={closeCelebration} />}
    </div>
  );
}
