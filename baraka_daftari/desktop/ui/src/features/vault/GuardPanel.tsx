import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, formatX100, unwrap } from '../../lib/api';

/** To'liq maqsad (oy): SPEC 2C.3 — standart 6 oy, birinchi bosqich 3 oy. */
const FULL_MONTHS = 6;

/**
 * «Qorovul pul» (favqulodda zaxira) progressi va «O'sadigan pul» darvozasi (SPEC 2C.3–2C.4).
 * Taqiq yo'q, tushuntirish bor: qulfli bo'limda shartlar va har biri bo'yicha progress ko'rsatiladi.
 */
export function GuardPanel() {
  const { t } = useTranslation();
  const guard = useQuery({
    queryKey: ['guard'],
    queryFn: () => unwrap(commands.guardOverview()),
  });
  const g = guard.data;
  return (
    <section className="rounded-lg border border-accent/30 p-5 lg:col-span-2" data-testid="guard">
      <h2 className="font-semibold">{t('guard.title')}</h2>
      <p className="mt-1 text-sm opacity-80">{t('guard.hint')}</p>
      {g && (
        <>
          <p className="mt-3 text-2xl font-semibold" data-testid="guard-months">
            {t('guard.months', {
              have: formatX100(g.months_x100),
              need: FULL_MONTHS,
            })}
          </p>
          <div
            role="progressbar"
            aria-label={t('guard.title')}
            aria-valuemin={0}
            aria-valuemax={FULL_MONTHS * 100}
            aria-valuenow={Math.min(g.months_x100, FULL_MONTHS * 100)}
            className="mt-2 h-3 w-full overflow-hidden rounded bg-accent/15"
          >
            <div
              className="h-full bg-accent"
              style={{
                width: `${String(Math.min(100, Math.round((g.months_x100 / (FULL_MONTHS * 100)) * 100)))}%`,
              }}
            />
          </div>
          {g.basis_months === 0 ? (
            <p className="mt-2 text-sm" data-testid="guard-nodata">
              {t('guard.noData')}
            </p>
          ) : (
            <ul className="mt-2 space-y-1 text-sm">
              <li>
                {t('guard.amounts', { balance: g.balance.formatted, target: g.target.formatted })}
              </li>
              <li>{t('guard.need', { amount: g.monthly_need.formatted })}</li>
              <li data-testid="guard-milestone">
                {g.milestone_reached
                  ? t('guard.milestoneDone', { amount: g.milestone.formatted })
                  : t('guard.milestone', { amount: g.milestone.formatted })}
              </li>
              {!g.full_reached && <li>{t('guard.gap', { amount: g.gap.formatted })}</li>}
            </ul>
          )}
          <p className="mt-2 text-xs opacity-70">{t('guard.untouchable')}</p>
        </>
      )}
      <GateCard />
    </section>
  );
}

function GateCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const gate = useQuery({ queryKey: ['gate'], queryFn: () => unwrap(commands.gateStatus()) });
  const guard = useQuery({
    queryKey: ['guard'],
    queryFn: () => unwrap(commands.guardOverview()),
  });
  const [asking, setAsking] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const declare = useMutation({
    mutationFn: (plan: boolean) => unwrap(commands.setDebtPlanDeclaration(plan)),
    onSuccess: refresh,
  });
  const bypass = useMutation({
    mutationFn: () => unwrap(commands.bypassGate(understood)),
    onSuccess: async () => {
      setAsking(false);
      setUnderstood(false);
      await refresh();
    },
  });
  const revoke = useMutation({
    mutationFn: () => unwrap(commands.revokeGateBypass()),
    onSuccess: refresh,
  });
  const g = gate.data;
  if (!g) return null;
  const error = [declare.error, bypass.error, revoke.error].find((e) => e !== null);
  return (
    <div className="mt-5 border-t border-accent/20 pt-4" data-testid="gate">
      <h3 className="font-semibold">{t('gate.title')}</h3>
      <p className="mt-1 text-sm opacity-80">{t('gate.hint')}</p>
      {g.open ? (
        <div className="mt-3" data-testid="gate-open">
          <p>
            {g.bypassed ? t('gate.openBypassed') : t('gate.open')}
            {guard.data
              ? ` ${t('gate.growing', { amount: guard.data.growing_balance.formatted })}`
              : ''}
          </p>
          <p className="mt-1 text-sm opacity-80">{t('gate.growingHint')}</p>
          {g.bypassed && (
            <button
              type="button"
              className="mt-2 rounded border border-accent px-3 py-1"
              onClick={() => {
                revoke.mutate();
              }}
            >
              {t('gate.revoke')}
            </button>
          )}
        </div>
      ) : (
        <div className="mt-3" data-testid="gate-locked">
          <p className="font-medium">{t('gate.locked')}</p>
          <ul className="mt-2 space-y-1 text-sm">
            {g.reasons.map((r) => (
              <li key={r}>
                {t(`gate.reason.${r}`, {
                  have: formatX100(g.months_x100),
                  need: formatX100(g.required_x100),
                })}
              </li>
            ))}
          </ul>
          {!asking ? (
            <button
              type="button"
              className="mt-3 rounded border border-accent px-3 py-1"
              onClick={() => {
                setAsking(true);
              }}
            >
              {t('gate.bypass')}
            </button>
          ) : (
            <div
              className="mt-3 space-y-2 rounded border border-accent/40 p-3"
              role="group"
              aria-label={t('gate.bypass')}
            >
              <p className="text-sm">{t('gate.bypassWarning')}</p>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={understood}
                  onChange={(e) => {
                    setUnderstood(e.target.checked);
                  }}
                />
                {t('gate.bypassUnderstood')}
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
                  disabled={!understood || bypass.isPending}
                  onClick={() => {
                    bypass.mutate();
                  }}
                >
                  {t('gate.bypassConfirm')}
                </button>
                <button
                  type="button"
                  className="rounded border border-accent px-3 py-1"
                  onClick={() => {
                    setAsking(false);
                    setUnderstood(false);
                  }}
                >
                  {t('vault.cancel')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      <fieldset className="mt-4 text-sm">
        <legend className="font-medium">{t('gate.debtTitle')}</legend>
        <p className="opacity-80">{t('gate.debtHint')}</p>
        <p className="mt-1" data-testid="derived-debt">
          {g.has_interest_debt ? t('gate.derivedInterestDebt') : t('gate.derivedNoInterestDebt')}
        </p>
        <label className="mt-1 flex items-center gap-2">
          <input
            type="checkbox"
            checked={g.has_debt_plan}
            onChange={(e) => {
              declare.mutate(e.target.checked);
            }}
          />
          {t('gate.hasDebtPlan')}
        </label>
      </fieldset>
      {error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </div>
  );
}
