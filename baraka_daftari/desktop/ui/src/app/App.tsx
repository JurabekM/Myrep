import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../bindings';

import { CouncilMode } from '../features/council/CouncilMode';
import { CeremoniesPage } from '../features/ceremonies/CeremoniesPage';
import { DebtsPage } from '../features/debts/DebtsPage';
import { EnvelopesPage } from '../features/envelopes/EnvelopesPage';
import { ExpensesPage } from '../features/expenses/ExpensesPage';
import { FamilyPage } from '../features/family/FamilyPage';
import { AuditWizardPage } from '../features/audit/AuditPage';
import { HomePage } from '../features/home/HomePage';
import { IncomePage } from '../features/income/IncomePage';
import { CraftsPage } from '../features/crafts/CraftsPage';
import { ExchangePage } from '../features/exchange/ExchangePage';
import { PartnershipsPage } from '../features/partnerships/PartnershipsPage';
import { PricesPage } from '../features/prices/PricesPage';
import { QuickEntry } from '../features/income/QuickEntry';
import { RescuePage } from '../features/rescue/RescuePage';
import { StudyPage } from '../features/study/StudyPage';
import { ObligationsPage } from '../features/obligations/ObligationsPage';
import { SubscriptionsPage } from '../features/subscriptions/SubscriptionsPage';
import { VaultPage } from '../features/vault/VaultPage';

import { CommandPalette } from './CommandPalette';
import { PAGE_LINKS, useNav, type Page } from './nav';

function CurrentPage({ page }: { page: Page }) {
  switch (page) {
    case 'home':
      return <HomePage />;
    case 'income':
      return <IncomePage />;
    case 'vault':
      return <VaultPage />;
    case 'budget':
      return <AuditWizardPage />;
    case 'obligations':
      return <ObligationsPage />;
    case 'study':
      return <StudyPage />;
    case 'expenses':
      return <ExpensesPage />;
    case 'family':
      return <FamilyPage />;
    case 'council':
      return <CouncilMode />;
    case 'subscriptions':
      return <SubscriptionsPage />;
    case 'envelopes':
      return <EnvelopesPage />;
    case 'rescue':
      return <RescuePage />;
    case 'prices':
      return <PricesPage />;
    case 'debts':
      return <DebtsPage />;
    case 'ceremonies':
      return <CeremoniesPage />;
    case 'partnerships':
      return <PartnershipsPage />;
    case 'crafts':
      return <CraftsPage />;
    case 'exchange':
      return <ExchangePage />;
  }
}

/** Ilova qobig'i: chap navigatsiya + ish maydoni. `Ctrl+N` — tez kiritish. */
export function App() {
  const { t } = useTranslation();
  const { page, setPage, openQuickEntry, openPalette } = useNav();
  const info = useQuery({ queryKey: ['app-info'], queryFn: () => commands.appInfo() });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;
      const key = e.key.toLowerCase();
      if (key === 'n') {
        e.preventDefault();
        openQuickEntry();
      } else if (key === 'k') {
        e.preventDefault();
        openPalette();
      } else if (key === 'p') {
        e.preventDefault();
        window.print();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
    };
  }, [openQuickEntry, openPalette]);

  // Oila kengashi — to'liq ekran rejimi (navigatsiyasiz).
  if (page === 'council') {
    return <CouncilMode />;
  }

  return (
    <div className="flex min-h-screen">
      <nav
        aria-label={t('nav.label')}
        className="w-56 shrink-0 border-r border-line bg-sidebar p-4"
      >
        <p className="mb-4 text-lg font-semibold">{t('app.title')}</p>
        <ul className="space-y-1">
          {PAGE_LINKS.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                aria-current={page === p.id ? 'page' : undefined}
                className={`w-full rounded px-3 py-2 text-left ${page === p.id ? 'bg-accent text-paper' : 'hover:bg-white/5'}`}
                onClick={() => {
                  setPage(p.id);
                }}
              >
                {t(p.labelKey)}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="mt-6 w-full rounded border border-accent px-3 py-2 text-left"
          onClick={openQuickEntry}
        >
          {t('nav.quickEntry')} <kbd className="ml-1 text-xs opacity-70">Ctrl+N</kbd>
        </button>
        {info.data?.quick_hotkey_registered === false && (
          <p role="note" className="mt-3 text-xs opacity-80">
            {t('hotkey.unavailable')}
          </p>
        )}
      </nav>
      <main className="flex-1 p-8">
        <CurrentPage page={page} />
        <footer className="mt-10 text-xs opacity-70">{t('disclaimer')}</footer>
      </main>
      <QuickEntry />
      <CommandPalette />
    </div>
  );
}
