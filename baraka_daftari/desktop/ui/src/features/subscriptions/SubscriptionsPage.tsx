import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type SubscriptionDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

const PERIODS = ['WEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY'] as const;

function Row({ s }: { s: SubscriptionDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const used = useMutation({
    mutationFn: () => unwrap(commands.markSubscriptionUsed(s.id)),
    onSuccess: refresh,
  });
  const needed = useMutation({
    mutationFn: (v: boolean | null) => unwrap(commands.setSubscriptionNeeded(s.id, v)),
    onSuccess: refresh,
  });
  const cancel = useMutation({
    mutationFn: () => unwrap(commands.cancelSubscription(s.id)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeSubscription(s.id)),
    onSuccess: refresh,
  });
  const error = [used.error, needed.error, cancel.error, remove.error].find((e) => e !== null);
  return (
    <li className={`py-3 ${s.active ? '' : 'opacity-60'}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <strong>{s.name}</strong>
        <span>
          {s.amount.formatted} · {t(`period.${s.period}`)}
        </span>
      </div>
      <p className="text-sm opacity-80">
        {t('subs.cost', { monthly: s.monthly.formatted, yearly: s.yearly.formatted })}
        {' · '}
        {s.last_used_on ? t('subs.lastUsed', { date: s.last_used_on }) : t('subs.neverUsed')}
      </p>
      {s.forgotten && (
        <p role="status" className="mt-1 text-sm font-semibold" data-testid="forgotten">
          {t('subs.forgotten')}
        </p>
      )}
      {s.active ? (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <button
            type="button"
            className="rounded border border-accent px-2 py-0.5"
            onClick={() => {
              used.mutate();
            }}
          >
            {t('subs.used')}
          </button>
          <span>{t('subs.needed')}</span>
          {([true, false] as const).map((v) => (
            <button
              key={String(v)}
              type="button"
              aria-pressed={s.needed === v}
              className={`rounded border border-accent px-2 py-0.5 ${s.needed === v ? 'bg-accent text-paper' : ''}`}
              onClick={() => {
                needed.mutate(s.needed === v ? null : v);
              }}
            >
              {v ? t('subs.yes') : t('subs.no')}
            </button>
          ))}
          <button
            type="button"
            className="rounded bg-accent px-2 py-0.5 text-paper"
            onClick={() => {
              cancel.mutate();
            }}
          >
            {t('subs.cancel')}
          </button>
          <button
            type="button"
            className="underline"
            onClick={() => {
              remove.mutate();
            }}
          >
            {t('obl.remove')}
          </button>
        </div>
      ) : (
        <p className="text-sm">{t('subs.cancelledOn', { date: s.cancelled_on ?? '' })}</p>
      )}
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

/** «Obunalar»: oylik va yillik narx, «kerakmi?», unutilgan obuna ogohlantirishi, bekor qilish. */
export function SubscriptionsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => unwrap(commands.listSubscriptions()),
  });
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>('MONTHLY');
  const add = useMutation({
    mutationFn: () => unwrap(commands.addSubscription(name, amount, period)),
    onSuccess: async () => {
      setName('');
      setAmount('');
      await queryClient.invalidateQueries();
    },
  });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t('nav.subscriptions')}</h1>
      <p className="text-sm opacity-80">{t('subs.hint')}</p>
      {list.data && (
        <p className="text-lg" data-testid="subs-total">
          {t('subs.total', {
            monthly: list.data.monthly_total.formatted,
            yearly: list.data.yearly_total.formatted,
          })}
        </p>
      )}
      <ul className="divide-y divide-accent/20">
        {list.data?.items.map((s) => (
          <Row key={s.id} s={s} />
        ))}
      </ul>
      {list.data?.items.length === 0 && <p className="opacity-70">{t('subs.empty')}</p>}
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <input
          aria-label={t('subs.name')}
          placeholder={t('subs.name')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
        <input
          aria-label={t('subs.amount')}
          placeholder={t('subs.amount')}
          className="w-36 rounded border border-accent/50 bg-transparent p-1"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
          }}
        />
        <select
          aria-label={t('subs.period')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={period}
          onChange={(e) => {
            setPeriod(e.target.value as (typeof PERIODS)[number]);
          }}
        >
          {PERIODS.map((p) => (
            <option key={p} value={p}>
              {t(`period.${p}`)}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === '' || amount.trim() === ''}
        >
          {t('subs.add')}
        </button>
      </form>
      <div role="alert" className="min-h-5 text-sm">
        {add.error ? errorMessage(t, add.error) : null}
      </div>
    </div>
  );
}
