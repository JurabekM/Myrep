import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

export function IncomePage() {
  const { t } = useTranslation();
  const openQuickEntry = useNav((s) => s.openQuickEntry);
  const home = useQuery({ queryKey: ['home'], queryFn: () => unwrap(commands.homeSummary()) });
  const month = home.data?.month;
  const list = useQuery({
    queryKey: ['incomes', month],
    queryFn: () => unwrap(commands.listIncomes(month ?? '')),
    enabled: month !== undefined,
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('nav.income')}</h1>
        <button
          type="button"
          className="rounded bg-accent px-4 py-2 text-paper"
          onClick={openQuickEntry}
        >
          {t('income.add')}
        </button>
      </div>
      {home.error ? <p role="alert">{errorMessage(t, home.error)}</p> : null}
      <p className="mt-2 text-sm opacity-80">
        {t('income.monthTotal', { total: home.data?.income.formatted ?? '' })}
      </p>
      <ul className="mt-4 divide-y divide-accent/20">
        {list.data?.map((i) => (
          <li key={i.id} className="flex justify-between py-2">
            <span>
              {i.received_on} · {t(`source.${i.source}`, { defaultValue: i.source })} ·{' '}
              {t(`channel.${i.channel}`)}
            </span>
            <span className="font-medium">{i.amount.formatted}</span>
          </li>
        ))}
      </ul>
      {list.data?.length === 0 && <p className="mt-4 opacity-70">{t('income.empty')}</p>}
    </div>
  );
}
