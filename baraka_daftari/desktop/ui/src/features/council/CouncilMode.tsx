import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { WhoseMoney } from '../audit/WhoseMoney';
import { ConsentPanel, HavasStatus, ProposeForm, useHavas } from '../family/Havas';
import { errorMessage, unwrap } from '../../lib/api';
import { useCategories, useHome, useMembers } from '../../lib/hooks';

const STEPS = ['review', 'categories', 'limit', 'minutes'] as const;
type Step = (typeof STEPS)[number];

function ReviewStep({ month }: { month: string }) {
  const { t } = useTranslation();
  const overview = useQuery({
    queryKey: ['audit', month],
    queryFn: () => unwrap(commands.auditOverview(month)),
  });
  const havas = useHavas(month);
  const o = overview.data;
  return (
    <div className="space-y-6">
      {o && (
        <dl className="grid max-w-2xl grid-cols-2 gap-x-8 gap-y-2 text-xl">
          <dt>{t('audit.income')}</dt>
          <dd className="text-right">{o.income.formatted}</dd>
          <dt>{t('audit.obligations')}</dt>
          <dd className="text-right">{o.obligations.formatted}</dd>
          <dt>{t('audit.expenses')}</dt>
          <dd className="text-right">{o.expenses.formatted}</dd>
          <dt>{t('audit.savings')}</dt>
          <dd className="text-right">{o.savings.formatted}</dd>
          <dt className="font-semibold">{t('audit.result')}</dt>
          <dd className="text-right font-semibold">{o.month_result.formatted}</dd>
          <dt className="font-semibold">{t('audit.unexplainedLabel')}</dt>
          <dd className="text-right font-semibold">{o.unexplained.formatted}</dd>
        </dl>
      )}
      {havas.data && <HavasStatus report={havas.data} />}
      {o && <WhoseMoney overview={o} />}
    </div>
  );
}

function CategoriesStep() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const categories = useCategories();
  const members = useMembers();
  const [by, setBy] = useState('');
  const changer = by || members.data?.find((m) => m.role === 'ADULT')?.id || '';
  const set = useMutation({
    mutationFn: (v: { id: string; nec: string }) =>
      unwrap(commands.setNecessity(v.id, v.nec, changer)),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  return (
    <div className="space-y-3">
      <p className="text-lg opacity-80">{t('council.categoriesHint')}</p>
      <label className="block text-lg">
        {t('council.changedBy')}{' '}
        <select
          className="rounded border border-accent/50 bg-transparent p-1"
          value={changer}
          onChange={(e) => {
            setBy(e.target.value);
          }}
        >
          {members.data
            ?.filter((m) => m.role === 'ADULT')
            .map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
        </select>
      </label>
      <table className="w-full max-w-3xl text-lg">
        <tbody>
          {categories.data?.map((c) => (
            <tr key={c.id} className="border-b border-accent/20">
              <td className="py-1">
                {c.name}
                {c.is_charity ? ` (${t('council.charity')})` : ''}
              </td>
              <td>
                <div role="group" aria-label={c.name} className="flex gap-1">
                  {(['ZARUR', 'KERAK', 'HAVAS'] as const).map((n) => (
                    <button
                      key={n}
                      type="button"
                      aria-pressed={c.necessity === n}
                      className={`rounded border border-accent px-3 py-0.5 ${c.necessity === n ? 'bg-accent text-paper' : ''}`}
                      onClick={() => {
                        set.mutate({ id: c.id, nec: n });
                      }}
                    >
                      {t(`necessity.${n}`)}
                    </button>
                  ))}
                </div>
              </td>
              <td className="pl-4 text-sm opacity-70">{c.last_change ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div role="alert" className="min-h-6 text-sm">
        {set.error ? errorMessage(t, set.error) : null}
      </div>
    </div>
  );
}

function LimitStep({ month }: { month: string }) {
  const { t } = useTranslation();
  const havas = useHavas(month);
  return (
    <div className="space-y-4 text-lg">
      <p className="opacity-80">{t('council.limitHint')}</p>
      {havas.data && <HavasStatus report={havas.data} />}
      {havas.data && <ConsentPanel report={havas.data} />}
      <ProposeForm />
    </div>
  );
}

function MinutesStep({ month }: { month: string }) {
  const { t } = useTranslation();
  const [saved, setSaved] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => unwrap(commands.exportCouncilPdf(month)),
    onSuccess: (name) => {
      setSaved(name);
    },
  });
  return (
    <div className="space-y-4 text-lg">
      <p>{t('council.minutesHint')}</p>
      <button
        type="button"
        className="rounded bg-accent px-6 py-3 text-paper disabled:opacity-50"
        disabled={save.isPending}
        onClick={() => {
          save.mutate();
        }}
      >
        {t('council.savePdf')}
      </button>
      {saved !== null && <p role="status">✓ {t('council.saved', { name: saved })}</p>}
      <div role="alert" className="min-h-6 text-sm">
        {save.error ? errorMessage(t, save.error) : null}
      </div>
    </div>
  );
}

/**
 * Oila kengashi: to'liq ekran, yirik shrift. Qadamlar: oyni ko'rib chiqish → toifalarni kelishish →
 * havas chegarasini har bir kattalar o'z PIN'i bilan tasdiqlashi → PDF bayonnoma.
 */
export function CouncilMode() {
  const { t } = useTranslation();
  const setPage = useNav((s) => s.setPage);
  const home = useHome();
  const [step, setStep] = useState<Step>('review');
  const [which, setWhich] = useState<'previous' | 'current'>('previous');
  const month = home.data
    ? which === 'previous'
      ? home.data.previous_month
      : home.data.month
    : undefined;
  const index = STEPS.indexOf(step);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPage('family');
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
    };
  }, [setPage]);

  return (
    <div
      className="min-h-screen bg-paper p-10 text-lg"
      role="region"
      aria-label={t('council.title')}
    >
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">{t('council.title')}</h1>
        <button
          type="button"
          className="underline"
          onClick={() => {
            setPage('family');
          }}
        >
          {t('council.exit')} (Esc)
        </button>
      </header>
      <ol className="mt-4 flex gap-4" aria-label={t('council.steps')}>
        {STEPS.map((s, i) => (
          <li
            key={s}
            aria-current={s === step ? 'step' : undefined}
            className={s === step ? 'font-semibold underline' : 'opacity-60'}
          >
            {i + 1}. {t(`council.step.${s}`)}
          </li>
        ))}
      </ol>
      <div className="mt-4 flex gap-2" role="group" aria-label={t('audit.month')}>
        {(['previous', 'current'] as const).map((w) => (
          <button
            key={w}
            type="button"
            aria-pressed={which === w}
            className={`rounded border border-accent px-3 py-1 ${which === w ? 'bg-accent text-paper' : ''}`}
            onClick={() => {
              setWhich(w);
            }}
          >
            {t(`audit.${w}`)}
          </button>
        ))}
      </div>
      <main className="mt-6">
        {month && step === 'review' && <ReviewStep month={month} />}
        {step === 'categories' && <CategoriesStep />}
        {month && step === 'limit' && <LimitStep month={month} />}
        {month && step === 'minutes' && <MinutesStep month={month} />}
      </main>
      <footer className="mt-8 flex justify-between">
        <button
          type="button"
          className="rounded border border-accent px-5 py-2 disabled:opacity-40"
          disabled={index === 0}
          onClick={() => {
            setStep(STEPS[index - 1] ?? 'review');
          }}
        >
          {t('council.back')}
        </button>
        <button
          type="button"
          className="rounded bg-accent px-5 py-2 text-paper disabled:opacity-40"
          disabled={index === STEPS.length - 1}
          onClick={() => {
            setStep(STEPS[index + 1] ?? 'minutes');
          }}
        >
          {t('council.next')}
        </button>
      </footer>
      <p className="mt-6 text-xs opacity-70">{t('disclaimer')}</p>
    </div>
  );
}
