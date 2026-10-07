import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { AuditWizard } from './AuditWizard';
import { WhoseMoney } from './WhoseMoney';

type Which = 'previous' | 'current';

/** "Byudjet" sahifasi: oy ko'rsatkichlari, "Kimning puli?" va audit ustasi. */
export function AuditWizardPage() {
  const { t } = useTranslation();
  const [which, setWhich] = useState<Which>('previous');
  const [running, setRunning] = useState(false);
  const home = useQuery({ queryKey: ['home'], queryFn: () => unwrap(commands.homeSummary()) });
  const month = home.data
    ? which === 'previous'
      ? home.data.previous_month
      : home.data.month
    : undefined;
  const overview = useQuery({
    queryKey: ['audit', month],
    queryFn: () => unwrap(commands.auditOverview(month ?? '')),
    enabled: month !== undefined,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('nav.budget')}</h1>
      {home.error ? <p role="alert">{errorMessage(t, home.error)}</p> : null}
      <div className="flex gap-2" role="group" aria-label={t('audit.month')}>
        {(['previous', 'current'] as const).map((w) => (
          <button
            key={w}
            type="button"
            aria-pressed={which === w}
            className={`rounded border border-accent px-3 py-1 ${which === w ? 'bg-accent text-paper' : ''}`}
            onClick={() => {
              setWhich(w);
              setRunning(false);
            }}
          >
            {t(`audit.${w}`)} {w === 'previous' ? home.data?.previous_month : home.data?.month}
          </button>
        ))}
      </div>

      {month && overview.data && running && (
        <AuditWizard
          key={month}
          month={month}
          overview={overview.data}
          onClose={() => {
            setRunning(false);
          }}
        />
      )}

      {overview.data && !running && (
        <>
          <dl className="grid max-w-xl grid-cols-2 gap-x-6 gap-y-1">
            <dt>{t('audit.income')}</dt>
            <dd className="text-right">{overview.data.income.formatted}</dd>
            <dt>{t('audit.obligations')}</dt>
            <dd className="text-right">{overview.data.obligations.formatted}</dd>
            <dt>{t('audit.expenses')}</dt>
            <dd className="text-right">{overview.data.expenses.formatted}</dd>
            <dt>{t('audit.savings')}</dt>
            <dd className="text-right">{overview.data.savings.formatted}</dd>
            <dt className="font-semibold">{t('audit.result')}</dt>
            <dd className="text-right font-semibold" data-testid="month-result">
              {overview.data.month_result.formatted}
            </dd>
            <dt className="font-semibold">{t('audit.unexplainedLabel')}</dt>
            <dd className="text-right font-semibold">{overview.data.unexplained.formatted}</dd>
          </dl>
          <button
            type="button"
            className="rounded bg-accent px-4 py-2 text-paper"
            onClick={() => {
              setRunning(true);
            }}
          >
            {t('audit.start')}
          </button>
          <WhoseMoney overview={overview.data} />
        </>
      )}
    </div>
  );
}
