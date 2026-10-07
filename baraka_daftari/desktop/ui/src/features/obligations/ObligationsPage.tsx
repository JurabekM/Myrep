import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type ObligationDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

const OWNERS = ['LANDLORD', 'BANK', 'STATE', 'FUEL', 'SHOP', 'OTHER'] as const;

function useRefresh() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}

function RecurringForm() {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDay, setDueDay] = useState('1');
  const [owner, setOwner] = useState<(typeof OWNERS)[number]>('LANDLORD');
  const add = useMutation({
    mutationFn: () =>
      unwrap(commands.addObligation({ name, amount, due_day: Number(dueDay), owner })),
    onSuccess: async () => {
      setName('');
      setAmount('');
      await refresh();
    },
  });
  return (
    <form
      className="mt-3 grid grid-cols-2 gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      <input
        aria-label={t('obl.name')}
        placeholder={t('obl.name')}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={name}
        onChange={(e) => {
          setName(e.target.value);
        }}
      />
      <input
        aria-label={t('obl.amount')}
        placeholder={t('obl.amount')}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={amount}
        onChange={(e) => {
          setAmount(e.target.value);
        }}
      />
      <input
        aria-label={t('obl.dueDay')}
        type="number"
        min={1}
        max={31}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={dueDay}
        onChange={(e) => {
          setDueDay(e.target.value);
        }}
      />
      <select
        aria-label={t('obl.owner')}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={owner}
        onChange={(e) => {
          setOwner(e.target.value as (typeof OWNERS)[number]);
        }}
      >
        {OWNERS.map((o) => (
          <option key={o} value={o}>
            {t(`owner.${o}`)}
          </option>
        ))}
      </select>
      <button type="submit" className="col-span-2 rounded bg-accent px-3 py-2 text-paper">
        {t('obl.add')}
      </button>
      {add.error ? (
        <p role="alert" className="col-span-2 text-sm">
          {errorMessage(t, add.error)}
        </p>
      ) : null}
    </form>
  );
}

function NasiyaForm() {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [creditor, setCreditor] = useState('');
  const [total, setTotal] = useState('');
  const add = useMutation({
    mutationFn: () => unwrap(commands.addNasiya(creditor, total)),
    onSuccess: async () => {
      setCreditor('');
      setTotal('');
      await refresh();
    },
  });
  return (
    <form
      className="mt-3 grid grid-cols-2 gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      <input
        aria-label={t('obl.creditor')}
        placeholder={t('obl.creditor')}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={creditor}
        onChange={(e) => {
          setCreditor(e.target.value);
        }}
      />
      <input
        aria-label={t('obl.nasiyaTotal')}
        placeholder={t('obl.nasiyaTotal')}
        className="rounded border border-accent/50 bg-transparent p-2"
        value={total}
        onChange={(e) => {
          setTotal(e.target.value);
        }}
      />
      <button type="submit" className="col-span-2 rounded bg-accent px-3 py-2 text-paper">
        {t('obl.addNasiya')}
      </button>
      {add.error ? (
        <p role="alert" className="col-span-2 text-sm">
          {errorMessage(t, add.error)}
        </p>
      ) : null}
    </form>
  );
}

function NasiyaRow({ o }: { o: ObligationDto }) {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [pay, setPay] = useState('');
  const payMut = useMutation({
    mutationFn: () => unwrap(commands.payNasiya(o.id, pay)),
    onSuccess: async () => {
      setPay('');
      await refresh();
    },
  });
  return (
    <li className="py-3">
      <p>
        <strong>{o.creditor}</strong> —{' '}
        {t('obl.remaining', { amount: o.remaining?.formatted ?? '' })}{' '}
        <span className="opacity-70">({t('obl.of', { amount: o.amount.formatted })})</span>
      </p>
      <form
        className="mt-1 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          payMut.mutate();
        }}
      >
        <input
          aria-label={t('obl.pay')}
          placeholder={t('obl.pay')}
          className="flex-1 rounded border border-accent/50 bg-transparent p-1"
          value={pay}
          onChange={(e) => {
            setPay(e.target.value);
          }}
        />
        <button type="submit" className="rounded border border-accent px-3 py-1">
          {t('obl.payButton')}
        </button>
      </form>
      {payMut.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, payMut.error)}
        </p>
      ) : null}
    </li>
  );
}

function RemoveButton({ id }: { id: string }) {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeObligation(id)),
    onSuccess: refresh,
  });
  return (
    <button
      type="button"
      className="text-sm underline"
      onClick={() => {
        remove.mutate();
      }}
    >
      {t('obl.remove')}
    </button>
  );
}

export function ObligationsPage() {
  const { t } = useTranslation();
  const list = useQuery({
    queryKey: ['obligations'],
    queryFn: () => unwrap(commands.listObligations()),
  });
  const recurring = list.data?.filter((o) => o.kind === 'RECURRING') ?? [];
  const nasiya = list.data?.filter((o) => o.kind === 'NASIYA') ?? [];
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">{t('nav.obligations')}</h1>
      <section>
        <h2 className="text-lg font-semibold">{t('obl.recurring')}</h2>
        <ul className="divide-y divide-accent/20">
          {recurring.map((o) => (
            <li key={o.id} className="flex items-center justify-between py-2">
              <span>
                {o.name} · {t(`owner.${o.owner}`)} · {t('obl.day', { day: o.due_day })}
              </span>
              <span className="flex items-center gap-4">
                <strong>{o.amount.formatted}</strong>
                <RemoveButton id={o.id} />
              </span>
            </li>
          ))}
        </ul>
        <RecurringForm />
      </section>
      <section>
        <h2 className="text-lg font-semibold">{t('obl.nasiya')}</h2>
        <ul className="divide-y divide-accent/20">
          {nasiya.map((o) => (
            <NasiyaRow key={o.id} o={o} />
          ))}
        </ul>
        <NasiyaForm />
      </section>
    </div>
  );
}
