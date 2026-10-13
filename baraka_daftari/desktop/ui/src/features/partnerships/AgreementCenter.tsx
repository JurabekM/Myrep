import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { unwrap } from '../../lib/api';

/**
 * Kelishuvlar markazi (D13A): barcha kelishuvlar jadvali — turi, holati, yangilash eslatmasi (30 kun ichida),
 * ochiq hodisalar, nizo va joriy oy ko'rigi holati. Holat bo'yicha filtr va nom bo'yicha qidiruv bor.
 */
export function AgreementCenter() {
  const { t } = useTranslation();
  const [status, setStatus] = useState('ALL');
  const [query, setQuery] = useState('');
  const rows = useQuery({
    queryKey: ['agreement-center'],
    queryFn: () => unwrap(commands.agreementsCenter()),
  });
  const all = rows.data ?? [];
  const statuses = [...new Map(all.map((r) => [r.status, r.status_label])).entries()];
  const needle = query.trim().toLowerCase();
  const shown = all.filter(
    (r) => (status === 'ALL' || r.status === status) && r.title.toLowerCase().includes(needle),
  );
  const reminder = (days: number | null) => {
    if (days === null) return null;
    return days < 0 ? t('center.reminderOverdue') : t('center.reminderSoon', { n: days });
  };
  return (
    <section className="space-y-3 rounded-lg border border-line p-4" data-testid="agreement-center">
      <h2 className="font-semibold">{t('center.title')}</h2>
      <div className="flex flex-wrap gap-3 text-sm">
        <label>
          {t('center.status')}
          <select
            className="ml-2 rounded border border-line-strong bg-transparent p-1"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
            }}
          >
            <option value="ALL">{t('center.all')}</option>
            {statuses.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('center.search')}
          <input
            className="ml-2 rounded border border-line-strong bg-transparent p-1"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
          />
        </label>
      </div>
      {shown.length === 0 ? (
        <p className="text-sm opacity-80">{t('center.empty')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line">
                <th className="p-1">{t('center.name')}</th>
                <th className="p-1">{t('center.kind')}</th>
                <th className="p-1">{t('center.state')}</th>
                <th className="p-1">{t('center.version')}</th>
                <th className="p-1">{t('center.review')}</th>
                <th className="p-1">{t('center.incidents')}</th>
                <th className="p-1">{t('center.dispute')}</th>
                <th className="p-1">{t('center.monthly')}</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={r.agreement_id}
                  className="border-b border-line"
                  data-testid={`center-row-${r.title}`}
                >
                  <td className="p-1">{r.title}</td>
                  <td className="p-1">{r.kind}</td>
                  <td className="p-1">{r.status_label}</td>
                  <td className="p-1">{`v${String(r.version)}`}</td>
                  <td className="p-1">
                    <span>{r.review_date ?? t('center.none')}</span>
                    {reminder(r.days_to_review) && (
                      <span className="ml-2 rounded bg-accent/10 px-1 text-xs" role="status">
                        {reminder(r.days_to_review)}
                      </span>
                    )}
                  </td>
                  <td className="p-1">{String(r.incidents)}</td>
                  <td className="p-1">{r.dispute_open ? t('center.yes') : t('center.none')}</td>
                  <td className="p-1">
                    {r.monthly_closed === null
                      ? t('center.none')
                      : r.monthly_closed
                        ? t('center.monthlyClosed')
                        : t('center.monthlyPending')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
