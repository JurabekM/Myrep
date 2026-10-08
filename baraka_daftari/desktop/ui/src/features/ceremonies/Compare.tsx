import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type CeremonyDto } from '../../bindings';
import { errorMessage, formatBp, formatMilli, unwrap } from '../../lib/api';

/** 2–3 stsenariyni yonma-yon solishtirish: umumiy narx, qarz, qaytarish muddati, muqobil maqsadlar. */
export function Compare({ plans }: { plans: CeremonyDto[] }) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState<string[]>([]);
  const [capacity, setCapacity] = useState('');
  const [percent, setPercent] = useState('');
  const run = useMutation({
    mutationFn: () => unwrap(commands.compareCeremonies(picked, capacity, percent)),
  });
  const toggle = (id: string) => {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < 3 ? [...p, id] : p));
  };
  const rows = run.data;
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="compare">
      <h2 className="font-semibold">{t('cer.compareTitle')}</h2>
      <p className="text-sm opacity-80">{t('cer.compareHint')}</p>
      <form
        className="mt-2 space-y-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          run.mutate();
        }}
      >
        <fieldset className="flex flex-wrap gap-3 text-sm">
          <legend className="sr-only">{t('cer.pick')}</legend>
          {plans.map((p) => (
            <label key={p.id} className="inline-flex items-center gap-1">
              <input
                type="checkbox"
                checked={picked.includes(p.id)}
                onChange={() => {
                  toggle(p.id);
                }}
              />
              {p.name}
            </label>
          ))}
        </fieldset>
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            {t('cer.capacity')}
            <input
              inputMode="decimal"
              className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
              value={capacity}
              onChange={(e) => {
                setCapacity(e.target.value);
              }}
            />
          </label>
          <label className="block text-sm">
            {t('cer.percent')}
            <input
              inputMode="decimal"
              className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
              value={percent}
              onChange={(e) => {
                setPercent(e.target.value);
              }}
            />
          </label>
          <button
            type="submit"
            className="rounded border border-accent px-3 py-1 disabled:opacity-50"
            disabled={picked.length < 2}
          >
            {t('cer.compare')}
          </button>
        </div>
      </form>
      {run.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, run.error)}
        </p>
      ) : null}
      {rows && (
        <table className="mt-3 w-full text-sm" data-testid="compare-table">
          <thead>
            <tr>
              <th className="text-left">{t('cer.metric')}</th>
              {rows.map((r) => (
                <th key={r.plan.id} className="text-right">
                  {r.plan.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <Row label={t('cer.total')} cells={rows.map((r) => r.plan.totals.total.formatted)} />
            <Row label={t('cer.cheaper')} cells={rows.map((r) => r.cheaper_than_max.formatted)} />
            <Row label={t('cer.debt')} cells={rows.map((r) => r.plan.totals.debt.formatted)} />
            <Row
              label={t('cer.debtShare')}
              cells={rows.map((r) => formatBp(r.plan.totals.debt_bp))}
            />
            <Row
              label={t('cer.repay')}
              testId="repay-row"
              cells={rows.map((r) =>
                r.repay_too_long
                  ? t('cer.tooLong')
                  : r.repay_months === null
                    ? '—'
                    : t('cer.months', { n: r.repay_months }),
              )}
            />
            <tr>
              <th className="text-left align-top font-normal">{t('cer.alternatives')}</th>
              {rows.map((r) => (
                <td key={r.plan.id} className="text-right">
                  {r.alternatives.length === 0
                    ? '—'
                    : r.alternatives.map((a) => (
                        <div key={a.goal_name}>
                          {t('cer.equals', {
                            times: formatMilli(a.times_milli),
                            goal: a.goal_name,
                          })}
                        </div>
                      ))}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      )}
    </section>
  );
}

function Row({ label, cells, testId }: { label: string; cells: string[]; testId?: string }) {
  return (
    <tr data-testid={testId}>
      <th className="text-left font-normal">{label}</th>
      {cells.map((c, i) => (
        <td key={i} className="text-right">
          {c}
        </td>
      ))}
    </tr>
  );
}
