import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type WithdrawalDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

function useInvalidate() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}

function RuleCard({
  rule,
}: {
  rule: { kind: 'Percent'; bp: number } | { kind: 'MonthlyFixed'; target: { formatted: string } };
}) {
  const { t } = useTranslation();
  const invalidate = useInvalidate();
  const [fixed, setFixed] = useState('');
  const setRule = useMutation({
    mutationFn: (v: { kind: string; value: string }) => unwrap(commands.setRule(v)),
    onSuccess: invalidate,
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('vault.rule')}</h2>
      <p className="mt-1 text-sm" data-testid="current-rule">
        {rule.kind === 'Percent'
          ? t('vault.rulePercent', { bp: formatBp(rule.bp) })
          : t('vault.ruleFixed', { amount: rule.target.formatted })}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {[500, 600, 700, 800, 900, 1000].map((bp) => (
          <button
            key={bp}
            type="button"
            className="rounded border border-accent px-3 py-1"
            onClick={() => {
              setRule.mutate({ kind: 'PERCENT', value: String(bp) });
            }}
          >
            {formatBp(bp)}
          </button>
        ))}
      </div>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setRule.mutate({ kind: 'MONTHLY_FIXED', value: fixed });
        }}
      >
        <input
          aria-label={t('vault.fixedLabel')}
          placeholder={t('vault.fixedLabel')}
          className="flex-1 rounded border border-accent/50 bg-transparent p-2"
          value={fixed}
          onChange={(e) => {
            setFixed(e.target.value);
          }}
        />
        <button type="submit" className="rounded border border-accent px-3 py-1">
          {t('vault.fixedSave')}
        </button>
      </form>
      {setRule.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, setRule.error)}
        </p>
      ) : null}
    </section>
  );
}

function OpeningBalanceCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidate();
  const [amount, setAmount] = useState('');
  const save = useMutation({
    mutationFn: () => unwrap(commands.setOpeningBalance(amount)),
    onSuccess: async () => {
      setAmount('');
      await invalidate();
    },
  });
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('vault.opening')}</h2>
      <p className="mt-1 text-sm opacity-80">{t('vault.openingHint')}</p>
      <form className="mt-3 flex gap-2" onSubmit={onSubmit}>
        <input
          aria-label={t('vault.openingLabel')}
          className="flex-1 rounded border border-accent/50 bg-transparent p-2"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
          }}
        />
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={amount.trim() === ''}
        >
          {t('vault.openingSave')}
        </button>
      </form>
      {save.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, save.error)}
        </p>
      ) : null}
    </section>
  );
}

function WithdrawalRow({ w }: { w: WithdrawalDto }) {
  const { t } = useTranslation();
  const invalidate = useInvalidate();
  const confirm = useMutation({
    mutationFn: () => unwrap(commands.confirmWithdrawal(w.id)),
    onSuccess: invalidate,
  });
  const cancel = useMutation({
    mutationFn: () => unwrap(commands.cancelWithdrawal(w.id)),
    onSuccess: invalidate,
  });
  return (
    <li className="py-3">
      <p>
        <strong>{w.amount.formatted}</strong> — {w.reason}
      </p>
      <p className="text-sm opacity-70">
        {t('vault.availableAt', { at: new Date(w.available_at).toLocaleString() })}
      </p>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          className="rounded bg-accent px-3 py-1 text-paper"
          onClick={() => {
            confirm.mutate();
          }}
        >
          {t('vault.confirm')}
        </button>
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          onClick={() => {
            cancel.mutate();
          }}
        >
          {t('vault.cancel')}
        </button>
      </div>
      {confirm.error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, confirm.error)}
        </p>
      ) : null}
    </li>
  );
}

function WithdrawalCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidate();
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const pending = useQuery({
    queryKey: ['withdrawals'],
    queryFn: () => unwrap(commands.listWithdrawals()),
  });
  const request = useMutation({
    mutationFn: () => unwrap(commands.requestWithdrawal(amount, reason)),
    onSuccess: async () => {
      setAmount('');
      setReason('');
      await invalidate();
    },
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('vault.withdraw')}</h2>
      <p className="mt-1 text-sm opacity-80">{t('vault.withdrawHint')}</p>
      <form
        className="mt-3 space-y-2"
        onSubmit={(e) => {
          e.preventDefault();
          request.mutate();
        }}
      >
        <input
          aria-label={t('vault.withdrawAmount')}
          placeholder={t('vault.withdrawAmount')}
          className="w-full rounded border border-accent/50 bg-transparent p-2"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
          }}
        />
        <input
          aria-label={t('vault.withdrawReason')}
          placeholder={t('vault.withdrawReason')}
          className="w-full rounded border border-accent/50 bg-transparent p-2"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
          }}
        />
        <button type="submit" className="rounded border border-accent px-3 py-1">
          {t('vault.withdrawRequest')}
        </button>
      </form>
      {request.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, request.error)}
        </p>
      ) : null}
      <ul className="mt-3 divide-y divide-accent/20">
        {pending.data?.map((w) => (
          <WithdrawalRow key={w.id} w={w} />
        ))}
      </ul>
    </section>
  );
}

export function VaultPage() {
  const { t } = useTranslation();
  const home = useQuery({ queryKey: ['home'], queryFn: () => unwrap(commands.homeSummary()) });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('nav.vault')}</h1>
      {home.data && (
        <>
          <p className="text-4xl font-semibold" data-testid="vault-page-balance">
            {home.data.vault_balance.formatted}
          </p>
          <p className="text-sm opacity-80">{t('vault.untouchable')}</p>
          <div className="grid gap-4 lg:grid-cols-2">
            <RuleCard rule={home.data.rule} />
            <OpeningBalanceCard />
            <WithdrawalCard />
          </div>
        </>
      )}
    </div>
  );
}
