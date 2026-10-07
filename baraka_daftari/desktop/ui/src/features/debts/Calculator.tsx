import { useMutation } from '@tanstack/react-query';
import { useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { BalanceChart } from './BalanceChart';
import { ScheduleTable } from './ScheduleTable';

/**
 * «Nima bo'ladi, agar...»: annuitet yoki differensial kredit (masalan, avtokredit 39 mln, 14 oy),
 * odatiy va qo'shimcha to'lovli jadval yonma-yon. Natija faqat taxminiy.
 */
export function Calculator() {
  const { t } = useTranslation();
  const [kind, setKind] = useState<'ANNUITY' | 'DIFFERENTIATED'>('ANNUITY');
  const [principal, setPrincipal] = useState('');
  const [percent, setPercent] = useState('');
  const [months, setMonths] = useState('14');
  const [extra, setExtra] = useState('');
  const [which, setWhich] = useState<'baseline' | 'accelerated'>('accelerated');
  const calc = useMutation({
    mutationFn: () =>
      unwrap(
        commands.loanCalculator(kind, principal, percent, Number.parseInt(months, 10) || 0, extra),
      ),
  });
  const r = calc.data;
  // Faqat grafik uchun: qoldiq qiymatlari (so'm). Hisob-kitob Rustda bajarilgan.
  const series = useMemo(
    () =>
      r
        ? [
            {
              name: t('calc.baseline'),
              values: r.baseline.schedule.map((x) => Number(x.balance.minor) / 100),
            },
            {
              name: t('calc.accelerated'),
              values: r.accelerated.schedule.map((x) => Number(x.balance.minor) / 100),
            },
          ]
        : [],
    [r, t],
  );
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="calculator">
      <h2 className="font-semibold">{t('calc.title')}</h2>
      <p className="text-sm opacity-80">{t('calc.hint')}</p>
      <form
        className="mt-3 flex flex-wrap items-end gap-3"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          calc.mutate();
        }}
      >
        <label className="block text-sm">
          {t('calc.kind')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as 'ANNUITY' | 'DIFFERENTIATED');
            }}
          >
            <option value="ANNUITY">{t('debts.kinds.ANNUITY')}</option>
            <option value="DIFFERENTIATED">{t('debts.kinds.DIFFERENTIATED')}</option>
          </select>
        </label>
        {(
          [
            ['calc.principal', principal, setPrincipal, 'w-36'],
            ['calc.percent', percent, setPercent, 'w-20'],
            ['calc.months', months, setMonths, 'w-20'],
            ['calc.extra', extra, setExtra, 'w-32'],
          ] as const
        ).map(([key, value, set, width]) => (
          <label key={key} className="block text-sm">
            {t(key)}
            <input
              inputMode="decimal"
              className={`mt-1 block ${width} rounded border border-accent/50 bg-transparent p-1`}
              value={value}
              onChange={(e) => {
                set(e.target.value);
              }}
            />
          </label>
        ))}
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={principal.trim() === '' || percent.trim() === ''}
        >
          {t('calc.run')}
        </button>
      </form>
      {calc.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, calc.error)}
        </p>
      ) : null}
      {r && (
        <div className="mt-4 space-y-3" data-testid="calc-result">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded bg-accent/10 p-3 text-sm">
              <h3 className="font-semibold">{t('calc.baseline')}</h3>
              <p>
                {t('calc.summary', {
                  months: r.baseline.months,
                  payment: r.baseline.first_payment.formatted,
                })}
              </p>
              <p>{t('calc.totalInterest', { amount: r.baseline.total_interest.formatted })}</p>
            </div>
            <div className="rounded bg-accent/10 p-3 text-sm">
              <h3 className="font-semibold">{t('calc.accelerated')}</h3>
              <p>
                {t('calc.summary', {
                  months: r.accelerated.months,
                  payment: r.accelerated.first_payment.formatted,
                })}
              </p>
              <p>{t('calc.totalInterest', { amount: r.accelerated.total_interest.formatted })}</p>
            </div>
          </div>
          <p className="font-semibold" data-testid="calc-saved">
            {t('calc.saved', { months: r.months_saved, amount: r.interest_saved.formatted })}
          </p>
          <p className="text-xs opacity-70">{t('calc.disclaimer')}</p>
          <BalanceChart series={series} label={t('calc.chart')} />
          <div className="flex gap-3 text-sm">
            {(['baseline', 'accelerated'] as const).map((w) => (
              <label key={w} className="inline-flex items-center gap-1">
                <input
                  type="radio"
                  name="calc-which"
                  checked={which === w}
                  onChange={() => {
                    setWhich(w);
                  }}
                />
                {t(`calc.${w}`)}
              </label>
            ))}
          </div>
          <ScheduleTable rows={r[which].schedule} />
        </div>
      )}
    </section>
  );
}
