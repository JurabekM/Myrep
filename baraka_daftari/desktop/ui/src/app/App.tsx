import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { CouncilMode } from '../features/council/CouncilMode';
import { EnvelopesPage } from '../features/envelopes/EnvelopesPage';
import { ExpensesPage } from '../features/expenses/ExpensesPage';
import { FamilyPage } from '../features/family/FamilyPage';
import { AuditWizardPage } from '../features/audit/AuditPage';
import { HomePage } from '../features/home/HomePage';
import { IncomePage } from '../features/income/IncomePage';
import { QuickEntry } from '../features/income/QuickEntry';
import { RescuePage } from '../features/rescue/RescuePage';
import { StudyPage } from '../features/study/StudyPage';
import { ObligationsPage } from '../features/obligations/ObligationsPage';
import { SubscriptionsPage } from '../features/subscriptions/SubscriptionsPage';
import { VaultPage } from '../features/vault/VaultPage';

import { useNav, type Page } from './nav';

const PAGES: { id: Page; labelKey: string }[] = [
  { id: 'home', labelKey: 'nav.home' },
  { id: 'income', labelKey: 'nav.income' },
  { id: 'vault', labelKey: 'nav.vault' },
  { id: 'budget', labelKey: 'nav.budget' },
  { id: 'expenses', labelKey: 'nav.expenses' },
  { id: 'obligations', labelKey: 'nav.obligations' },
  { id: 'envelopes', labelKey: 'nav.envelopes' },
  { id: 'subscriptions', labelKey: 'nav.subscriptions' },
  { id: 'rescue', labelKey: 'nav.rescue' },
  { id: 'family', labelKey: 'nav.family' },
  { id: 'study', labelKey: 'nav.study' },
];

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
  }
}

/** Ilova qobig'i: chap navigatsiya + ish maydoni. `Ctrl+N` — tez kiritish. */
export function App() {
  const { t } = useTranslation();
  const { page, setPage, openQuickEntry } = useNav();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        openQuickEntry();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
    };
  }, [openQuickEntry]);

  // Oila kengashi — to'liq ekran rejimi (navigatsiyasiz).
  if (page === 'council') {
    return <CouncilMode />;
  }

  return (
    <div className="flex min-h-screen">
      <nav aria-label={t('nav.label')} className="w-52 shrink-0 border-r border-accent/30 p-4">
        <p className="mb-4 text-lg font-semibold">{t('app.title')}</p>
        <ul className="space-y-1">
          {PAGES.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                aria-current={page === p.id ? 'page' : undefined}
                className={`w-full rounded px-3 py-2 text-left ${page === p.id ? 'bg-accent text-paper' : 'hover:bg-accent/10'}`}
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
      </nav>
      <main className="flex-1 p-8">
        <CurrentPage page={page} />
        <footer className="mt-10 text-xs opacity-70">{t('disclaimer')}</footer>
      </main>
      <QuickEntry />
    </div>
  );
}
