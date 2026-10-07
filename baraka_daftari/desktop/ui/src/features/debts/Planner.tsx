import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

/**
 * Qarzdan chiqish rejalovchisi: odatiy va tezlashtirilgan grafik, yopish tartibi, «qarzsiz kun».
 * Natija taxminiy: muddatidan oldin to'lash shartlari (jarima, komissiya) shartnomaga bog'liq.
 */
export function Planner() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [monthly, setMonthly] = useState('');
  const [oneOff, setOneOff] = useState('');
  const sources = useQuery({
    queryKey: ['payoff-sources'],
    queryFn: () => unwrap(commands.payoffSources()),
  });
  const plan = useQuery({
    queryKey: ['payoff-plan', monthly, oneOff],
    queryFn: () => unwrap(commands.payoffPlan(monthly, oneOff)),
    retry: false,
    // Yozayotganda maydonlar yo'qolib ketmasligi uchun oldingi natija saqlanadi.
    placeholderData: keepPreviousData,
  });
  const reorder = useMutation({
    mutationFn: (ids: string[] | null) =>
      ids === null ? unwrap(commands.clearClosingOrder()) : unwrap(commands.setClosingOrder(ids)),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const p = plan.data;
  if (!p) {
    return plan.error ? (
      <p role="alert" className="text-sm">
        {errorMessage(t, plan.error)}
      </p>
    ) : null;
  }
  const src = sources.data;
  const name = (id: string) => p.lines.find((l) => l.id === id)?.creditor ?? id;
  const move = (i: number, dir: -1 | 1) => {
    const ids = [...p.order];
    const j = i + dir;
    const a = ids[i];
    const b = ids[j];
    if (a === undefined || b === undefined) return;
    ids[i] = b;
    ids[j] = a;
    reorder.mutate(ids);
  };
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="planner">
      <h2 className="font-semibold">{t('planner.title')}</h2>
      <p className="text-sm opacity-80">{t('planner.hint')}</p>

      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="block text-sm">
          {t('planner.monthly')}
          <input
            inputMode="decimal"
            className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
            value={monthly}
            onChange={(e) => {
              setMonthly(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('planner.oneOff')}
          <input
            inputMode="decimal"
            className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
            value={oneOff}
            onChange={(e) => {
              setOneOff(e.target.value);
            }}
          />
        </label>
      </div>
      {src && (
        <ul className="mt-2 space-y-0.5 text-xs opacity-80" data-testid="sources">
          {src.monthly_share && (
            <li>{t('planner.srcShare', { amount: src.monthly_share.formatted })}</li>
          )}
          <li>{t('planner.srcRescued', { amount: src.rescued_available.formatted })}</li>
          <li>{t('planner.srcSellable', { amount: src.sellable_listed.formatted })}</li>
        </ul>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-2" data-testid="plan-compare">
        <div className="rounded bg-accent/10 p-3 text-sm">
          <h3 className="font-semibold">{t('planner.baseline')}</h3>
          <p>{t('planner.months', { n: p.baseline_months })}</p>
          <p>{t('planner.debtFree', { date: p.debt_free_baseline ?? '—' })}</p>
        </div>
        <div className="rounded bg-accent/10 p-3 text-sm">
          <h3 className="font-semibold">{t('planner.accelerated')}</h3>
          <p>{t('planner.months', { n: p.accelerated_months })}</p>
          <p data-testid="debt-free-day">
            {t('planner.debtFree', { date: p.debt_free_accelerated ?? '—' })}
          </p>
        </div>
      </div>
      <p className="mt-2 font-semibold" data-testid="months-saved">
        {t('planner.saved', { n: p.months_saved })}
      </p>

      <h3 className="mt-4 font-medium">{t('planner.order')}</h3>
      <p className="text-xs opacity-70">
        {p.manual_order ? t('planner.orderManual') : t('planner.orderDefault')}
      </p>
      <ol className="mt-1 space-y-1">
        {p.order.map((id, i) => {
          const line = p.lines.find((l) => l.id === id);
          return (
            <li key={id} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="w-5">{i + 1}.</span>
              <span className="flex-1">
                {name(id)}
                {line
                  ? ` — ${t('planner.line', { a: line.baseline_months, b: line.accelerated_months })}`
                  : ''}
              </span>
              <button
                type="button"
                aria-label={t('planner.up', { name: name(id) })}
                className="rounded border border-accent/50 px-2"
                disabled={i === 0}
                onClick={() => {
                  move(i, -1);
                }}
              >
                ↑
              </button>
              <button
                type="button"
                aria-label={t('planner.down', { name: name(id) })}
                className="rounded border border-accent/50 px-2"
                disabled={i === p.order.length - 1}
                onClick={() => {
                  move(i, 1);
                }}
              >
                ↓
              </button>
            </li>
          );
        })}
      </ol>
      {p.manual_order && (
        <button
          type="button"
          className="mt-1 text-sm underline"
          onClick={() => {
            reorder.mutate(null);
          }}
        >
          {t('planner.resetOrder')}
        </button>
      )}
      <p className="mt-3 text-xs opacity-70">{t('planner.disclaimer')}</p>
      {reorder.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, reorder.error)}
        </p>
      ) : null}
    </section>
  );
}
