import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { formatBp, unwrap } from '../../lib/api';

/** Bosh sahifadagi qarz kartochkasi: faqat faol qarz (yoki berilgan qarz muddati) bo'lsa ko'rinadi. */
export function DebtSummary() {
  const { t } = useTranslation();
  const setPage = useNav((s) => s.setPage);
  const overview = useQuery({
    queryKey: ['debt-overview'],
    queryFn: () => unwrap(commands.debtOverview()),
  });
  const o = overview.data;
  if (!o || o.active_count === 0) return null;
  return (
    <section className="rounded-lg border border-accent p-5" data-testid="debt-slot">
      <h2 className="text-sm uppercase tracking-wide opacity-70">{t('debts.slotTitle')}</h2>
      <p className="mt-2 text-2xl font-semibold">{o.total_remaining.formatted}</p>
      <p className="text-sm opacity-80">
        {t('debts.monthlyLoad', { amount: o.monthly_load.formatted })}
        {o.burden_bp !== null ? ` · ${t('debts.ofIncome', { bp: formatBp(o.burden_bp) })}` : ''}
      </p>
      {o.any_overdue && (
        <p className="mt-1 text-sm font-semibold" role="status">
          {t('debts.overdueNote')}
        </p>
      )}
      <p className="mt-1 text-sm italic opacity-80">{t('debts.wound')}</p>
      <button
        type="button"
        className="mt-2 text-sm underline"
        onClick={() => {
          setPage('debts');
        }}
      >
        {t('debts.open')}
      </button>
    </section>
  );
}
