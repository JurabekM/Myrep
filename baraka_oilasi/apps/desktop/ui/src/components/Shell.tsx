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
import { KkCashScreen } from "../features/kasbkor/KkCashScreen";
import { KkCloseScreen } from "../features/kasbkor/KkCloseScreen";
import { KkCreditScreen } from "../features/kasbkor/KkCreditScreen";
import { KkStaffScreen } from "../features/kasbkor/KkStaffScreen";
import { KkGateScreen } from "../features/kasbkor/KkGateScreen";
import { KkMeasureScreen } from "../features/kasbkor/KkMeasureScreen";
import { KkStockScreen } from "../features/kasbkor/KkStockScreen";
import { KkSuppliersScreen } from "../features/kasbkor/KkSuppliersScreen";
import { KkZakatScreen } from "../features/kasbkor/KkZakatScreen";
import { KkEquipmentScreen } from "../features/kasbkor/KkEquipmentScreen";
import { KkHomeScreen } from "../features/kasbkor/KkHomeScreen";
import { KkLaborScreen } from "../features/kasbkor/KkLaborScreen";
import { KkQuoteScreen } from "../features/kasbkor/KkQuoteScreen";
import { KkSellerCreditScreen, KkSellerScreen } from "../features/kasbkor/KkSellerScreen";
import { KkShiftScreen } from "../features/kasbkor/KkShiftScreen";
import { MfHomeScreen } from "../features/musofir/MfHomeScreen";
import { TwoShoresScreen } from "../features/musofir/TwoShoresScreen";
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

/** Kasb-kor makoni bo'limlari (K1–K2); qolganlari keyingi K-vazifalarda. */
const KK_NAV: { screen: Screen; label: string }[] = [
  { screen: "home", label: "nav.home" },
  { screen: "kkCash", label: "nav.kkCash" },
  { screen: "kkCredit", label: "nav.kkCredit" },
  { screen: "kkStock", label: "nav.kkStock" },
  { screen: "kkSuppliers", label: "nav.kkSuppliers" },
  { screen: "kkStaff", label: "nav.kkStaff" },
  { screen: "kkEquipment", label: "nav.kkEquipment" },
  { screen: "kkLabor", label: "nav.kkLabor" },
  { screen: "kkQuote", label: "nav.kkQuote" },
  { screen: "kkClose", label: "nav.kkClose" },
  { screen: "kkGate", label: "nav.kkGate" },
  { screen: "kkZakat", label: "nav.kkZakat" },
  { screen: "kkMeasure", label: "nav.kkMeasure" },
  { screen: "sync", label: "nav.sync" },
  { screen: "settings", label: "nav.settings" },
];

/** Musofir makoni (M1): bosh sahifa — hamma narsa shu yerda. */
const MF_NAV: { screen: Screen; label: string }[] = [
  { screen: "home", label: "nav.home" },
  { screen: "sync", label: "nav.sync" },
  { screen: "settings", label: "nav.settings" },
];

/** Sotuvchi qurilmasi (ADR-0003): faqat sotuv, nasiya to'lovi va smena. */
const SELLER_NAV: { screen: Screen; label: string }[] = [
  { screen: "home", label: "nav.kkSell" },
  { screen: "kkSellerCredit", label: "nav.kkSellerCredit" },
  { screen: "kkShift", label: "nav.kkShift" },
  { screen: "sync", label: "nav.sync" },
  { screen: "settings", label: "nav.settings" },
];

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
  kkEquipment: "mentor.kkEquipment",
  kkLabor: "mentor.kkLabor",
  kkQuote: "mentor.kkQuote",
  kkClose: "mentor.kkClose",
  kkCash: "mentor.kkCash",
  kkCredit: "mentor.kkCredit",
  kkStock: "mentor.kkStock",
  kkStaff: "mentor.kkStaff",
  kkSuppliers: "mentor.kkSuppliers",
  kkGate: "mentor.kkGate",
  kkZakat: "mentor.kkZakat",
  kkMeasure: "mentor.kkMeasure",
  kkSellerCredit: "mentor.kkSellerCredit",
  kkShift: "mentor.kkShift",
  twoShores: "mentor.twoShores",
  sync: "mentor.sync",
  settings: "mentor.settings",
};

/** Asosiy oyna: chapda navigatsiya va makonlar, markazda ish maydoni, oʻngda Sobir hoji. */
export function Shell() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { screen: picked, setScreen, spaceId, setSpace, incomeOpen, openIncome, closeIncome, openKkEntry, openMfEntry, celebration, closeCelebration, offerOpen, openOffer, closeOffer } = useUi();
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const settings = useQuery({ queryKey: keys.settings, queryFn: () => call(commands.settings()) });
  const lock = useMutation({ mutationFn: () => call(commands.lock()), onSettled: () => resetAfterLock(qc) });
  // Qurilma roli (ADR-0003): sotuvchi — alohida qisqa menyu, hisobchi — faqat o'qish.
  const deviceRole = useQuery({ queryKey: keys.deviceRole, queryFn: () => call(commands.deviceRole()) });
  const role = deviceRole.data?.role ?? "OWNER";
  const seller = role === "SELLER";

  const allSpaces = household.data?.spaces ?? [];
  // Uydagi oila qurilmasi (ADR-0004): Musofir makoni — musofirning shaxsiy hisobi, ko'rsatilmaydi.
  const home = role === "HOME";
  const spaces = home ? allSpaces.filter((s) => s.kind !== "MUSOFIR") : allSpaces;
  const active = spaceId && spaces.some((s) => s.id === spaceId) ? spaceId : (spaces[0]?.id ?? null);
  const activeKind = spaces.find((s) => s.id === active)?.kind;
  const kasbkor = activeKind === "KASBKOR";
  const musofir = activeKind === "MUSOFIR";
  // «Ikki qirg'oq» (M2): xonadonda Musofir makoni bo'lsa — Uy makonida uy tomoni ekrani.
  const mfSpaceId = home ? (deviceRole.data?.spaceId ?? null) : (allSpaces.find((s) => s.kind === "MUSOFIR")?.id ?? null);
  const uyNav = mfSpaceId ? [...NAV.slice(0, -2), { screen: "twoShores" as Screen, label: "nav.twoShores" }, ...NAV.slice(-2)] : NAV;
  const nav = seller ? SELLER_NAV : kasbkor ? KK_NAV : musofir ? MF_NAV : uyNav;
  // Boshqa makonga o'tilganda shu makonda yo'q bo'lim tanlangan bo'lsa — bosh sahifa.
  const screen: Screen = nav.some((n) => n.screen === picked) ? picked : "home";

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
        if (seller) setScreen("home");
        else if (kasbkor) openKkEntry("SALE");
        else if (musofir) {
          setScreen("home");
          openMfEntry("SALARY");
        }
        else openIncome();
      } else if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        lock.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openIncome, openKkEntry, openMfEntry, kasbkor, musofir, seller, setScreen, lock]);

  return (
    <div className="flex h-full">
      <a href="#main" className="skip-link">
        {t("a11y.skipToMain")}
      </a>
      <nav aria-label={t("a11y.mainNav")} className="flex min-h-0 w-60 shrink-0 flex-col gap-1 border-r border-line bg-sidebar p-4">
        <p className="mb-4 font-serif text-xl font-semibold">{t("app.name")}</p>
        <div role="group" aria-label={t("a11y.spaces")} className="mb-4 flex flex-wrap gap-1">
          {spaces.map((s) => (
            <button key={s.id} aria-pressed={s.id === active} className={s.id === active ? "btn-primary px-3 py-1 text-sm" : "btn-ghost px-3 py-1 text-sm"} onClick={() => setSpace(s.id)}>
              {t(`space.${s.kind}`)}
            </button>
          ))}
        </div>
        {/* Bandlar ko'p (Kasb-kor) — ro'yxat o'zi aylanadi, oyna emas; pastki tugmalar doim ko'rinadi. */}
        <div className="-mx-1 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-1">
          {nav.map((n) => (
            <button
              key={n.screen}
              aria-current={screen === n.screen ? "page" : undefined}
              className={`shrink-0 rounded-md px-3 py-2 text-left ${screen === n.screen ? "bg-surface font-medium text-ink" : "text-ink-muted hover:bg-surface hover:text-ink"}`}
              onClick={() => setScreen(n.screen)}
            >
              {t(n.label)}
            </button>
          ))}
        </div>
        {role === "HOME" && (
          <p data-testid="role-badge" className="mt-3 rounded-md border border-line px-3 py-2 text-xs text-ink-muted">
            {t("role.badge.HOME")}
          </p>
        )}
        {role === "OWNER" || role === "HOME" ? (
          <button className={`btn-ghost text-sm ${home ? "" : "mt-3"}`} onClick={openOffer}>
            {t("offer.open")}
          </button>
        ) : (
          <p data-testid="role-badge" className="mt-3 rounded-md border border-line px-3 py-2 text-xs text-ink-muted">
            {t(`role.badge.${role}`, { space: t(`space.${spaces.find((s) => s.id === deviceRole.data?.spaceId)?.kind ?? "KASBKOR"}`) })}
          </p>
        )}
        <button className="btn-ghost" onClick={() => lock.mutate()}>
          {t("nav.lock")} <kbd className="text-xs">Ctrl+L</kbd>
        </button>
      </nav>
      <main id="main" tabIndex={-1} className="min-w-0 flex-1 overflow-y-auto p-8 outline-none">
        {role === "ACCOUNTANT" && (
          <p role="note" data-testid="role-read-only" className="card mb-5 border-warn py-3 text-sm text-warn">
            {t("role.readOnly")}
          </p>
        )}
        {active && screen === "home" && (seller ? <KkSellerScreen spaceId={active} /> : kasbkor ? <KkHomeScreen spaceId={active} /> : musofir ? <MfHomeScreen spaceId={active} /> : <HomeScreen spaceId={active} />)}
        {active && seller && screen === "kkSellerCredit" && <KkSellerCreditScreen spaceId={active} />}
        {active && mfSpaceId && screen === "twoShores" && <TwoShoresScreen mfSpaceId={mfSpaceId} uySpaceId={active} />}
        {active && seller && screen === "kkShift" && <KkShiftScreen spaceId={active} />}
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
        {active && kasbkor && screen === "kkEquipment" && <KkEquipmentScreen spaceId={active} />}
        {active && kasbkor && screen === "kkLabor" && <KkLaborScreen spaceId={active} />}
        {active && kasbkor && screen === "kkQuote" && <KkQuoteScreen spaceId={active} />}
        {active && kasbkor && screen === "kkClose" && <KkCloseScreen spaceId={active} />}
        {active && kasbkor && screen === "kkCash" && <KkCashScreen spaceId={active} />}
        {active && kasbkor && screen === "kkCredit" && <KkCreditScreen spaceId={active} />}
        {active && kasbkor && screen === "kkStock" && <KkStockScreen spaceId={active} />}
        {active && kasbkor && screen === "kkSuppliers" && <KkSuppliersScreen spaceId={active} />}
        {active && kasbkor && screen === "kkStaff" && <KkStaffScreen spaceId={active} />}
        {active && kasbkor && screen === "kkGate" && <KkGateScreen spaceId={active} />}
        {active && kasbkor && screen === "kkZakat" && <KkZakatScreen spaceId={active} />}
        {active && kasbkor && screen === "kkMeasure" && <KkMeasureScreen spaceId={active} />}
        {screen === "sync" && <SyncScreen />}
        {screen === "settings" && <SettingsScreen />}
      </main>
      <Mentor tipKey={seller && screen === "home" ? "mentor.kkSeller" : kasbkor && screen === "home" ? "mentor.kk" : musofir && screen === "home" ? "mentor.mf" : MENTOR[screen]} />
      {incomeOpen && active && !kasbkor && !musofir && <IncomeDialog spaceId={active} onClose={closeIncome} />}
      {offerOpen && <OfferCheckDialog onClose={closeOffer} />}
      {celebration && active && <CelebrationDialog spaceId={active} result={celebration} onClose={closeCelebration} />}
    </div>
  );
}
