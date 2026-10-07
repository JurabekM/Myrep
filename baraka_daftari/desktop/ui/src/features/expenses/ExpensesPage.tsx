import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { unwrap } from '../../lib/api';
import { useCategories, useHome } from '../../lib/hooks';

import { CsvImport } from '../import/CsvImport';

import { WeekSheet } from './WeekSheet';

export function ExpensesPage() {
  const { t } = useTranslation();
  const home = useHome();
  const categories = useCategories();
  const weekStart = home.data?.week_start;
  const today = home.data?.today;
  const list = useQuery({
    queryKey: ['expenses', weekStart, today],
    queryFn: () => unwrap(commands.listExpenses(weekStart ?? '', today ?? '')),
    enabled: weekStart !== undefined && today !== undefined,
  });
  const name = (id: string) => categories.data?.find((c) => c.id === id)?.name ?? '';
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">{t('nav.expenses')}</h1>
      <WeekSheet />
      <CsvImport />
      <section>
        <h2 className="text-lg font-semibold">{t('sheet.thisWeek')}</h2>
        <ul className="mt-2 divide-y divide-accent/20">
          {list.data?.map((e) => (
            <li key={e.id} className="flex justify-between py-1 text-sm">
              <span>
                {e.date} · {name(e.category_id)}
                {e.note ? ` · ${e.note}` : ''}
                {e.is_gift ? ` · ${t('sheet.gift')}` : ''}
                {e.funded_by_debt ? ` · ⚑ ${t('sheet.debt')}` : ''}
              </span>
              <span className="font-medium">{e.amount.formatted}</span>
            </li>
          ))}
        </ul>
        {list.data?.length === 0 && <p className="mt-2 opacity-70">{t('sheet.empty')}</p>}
      </section>
    </div>
  );
}
