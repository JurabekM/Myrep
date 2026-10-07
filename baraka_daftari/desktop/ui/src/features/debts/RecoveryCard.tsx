import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

/**
 * «Qarzdan chiqish» rejimi (70 / 20 / 10). 10% — baribir «Kelajagim»ga: qarz o'tmishga to'lov,
 * jamg'arma kelajakka to'lov. Jamg'arma ulushi 1% dan kam bo'lishi mumkin emas.
 */
export function RecoveryCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const setPage = useNav((s) => s.setPage);
  const refresh = () => queryClient.invalidateQueries();
  const status = useQuery({
    queryKey: ['recovery'],
    queryFn: () => unwrap(commands.recoveryStatus()),
  });
  const s = status.data;
  const [living, setLiving] = useState('70');
  const [extra, setExtra] = useState('20');
  const [savings, setSavings] = useState('10');
  useEffect(() => {
    if (s) {
      setLiving(String(s.living_bp / 100));
      setExtra(String(s.extra_bp / 100));
      setSavings(String(s.savings_bp / 100));
    }
  }, [s]);
  const toggle = useMutation({
    mutationFn: (mode: 'STANDARD' | 'DEBT_RECOVERY') => unwrap(commands.setBudgetMode(mode)),
    onSuccess: refresh,
  });
  const dismiss = useMutation({
    mutationFn: () => unwrap(commands.dismissRecoveryNotice()),
    onSuccess: refresh,
  });
  const pct = (v: string) => (Number.parseInt(v, 10) || 0) * 100;
  const save = useMutation({
    mutationFn: () => unwrap(commands.setRecoverySplit(pct(living), pct(extra), pct(savings))),
    onSuccess: refresh,
  });
  if (!s) return null;
  const recovery = s.mode === 'DEBT_RECOVERY';
  const savingsTooLow = pct(savings) < 100;
  const sumOk = pct(living) + pct(extra) + pct(savings) === 10_000;
  const error = [toggle.error, save.error, dismiss.error].find((e) => e !== null);
  return (
    <section className="rounded-lg border border-accent p-5" data-testid="recovery">
      <h2 className="font-semibold">{t('recovery.title')}</h2>
      <p className="mt-1 text-sm opacity-80">{t('recovery.hint')}</p>
      {s.reverted_notice && (
        <div role="status" className="mt-2 rounded bg-accent/10 p-3 text-sm" data-testid="reverted">
          <p className="font-semibold">{t('recovery.reverted')}</p>
          <p>{t('recovery.freed')}</p>
          <div className="mt-2 flex gap-3">
            <button
              type="button"
              className="rounded bg-accent px-3 py-1 text-paper"
              onClick={() => {
                dismiss.mutate();
                setPage('vault');
              }}
            >
              {t('recovery.toVault')}
            </button>
            <button
              type="button"
              className="underline"
              onClick={() => {
                dismiss.mutate();
              }}
            >
              {t('recovery.later')}
            </button>
          </div>
        </div>
      )}
      {s.suggest_recovery && (
        <p className="mt-2 text-sm font-medium" data-testid="suggest">
          {t('recovery.suggest')}
        </p>
      )}
      <p className="mt-2 text-sm">
        {t('recovery.current', { mode: t(`recovery.modes.${s.mode}`) })}
      </p>
      <div className="mt-2 flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          onClick={() => {
            toggle.mutate(recovery ? 'STANDARD' : 'DEBT_RECOVERY');
          }}
        >
          {recovery ? t('recovery.turnOff') : t('recovery.turnOn')}
        </button>
      </div>
      <form
        className="mt-3 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!savingsTooLow && sumOk) save.mutate();
        }}
      >
        {(
          [
            ['recovery.living', living, setLiving],
            ['recovery.extra', extra, setExtra],
            ['recovery.savings', savings, setSavings],
          ] as const
        ).map(([key, value, set]) => (
          <label key={key} className="block text-sm">
            {t(key)}
            <input
              inputMode="numeric"
              className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
              value={value}
              onChange={(e) => {
                set(e.target.value);
              }}
            />
          </label>
        ))}
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1 disabled:opacity-50"
          disabled={savingsTooLow || !sumOk}
        >
          {t('recovery.saveSplit')}
        </button>
      </form>
      {savingsTooLow && (
        <p role="alert" className="mt-1 text-sm font-semibold" data-testid="savings-warning">
          {t('recovery.savingsWarning')}
        </p>
      )}
      {!sumOk && !savingsTooLow && (
        <p role="alert" className="mt-1 text-sm">
          {t('recovery.sumWarning')}
        </p>
      )}
      <p className="mt-2 text-sm italic">{t('recovery.savingsWhy')}</p>
      {s.amounts && (
        <p className="mt-2 text-sm" data-testid="split-amounts">
          {t('recovery.amounts', {
            living: s.amounts.living.formatted,
            extra: s.amounts.extra.formatted,
            savings: s.amounts.savings.formatted,
            lp: formatBp(s.living_bp),
            ep: formatBp(s.extra_bp),
            sp: formatBp(s.savings_bp),
          })}
        </p>
      )}
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}
