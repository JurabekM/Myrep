import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type ReceivableDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { ReceiptPanel } from './ReceiptPanel';

function ReceivableRow({ r }: { r: ReceivableDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const [amount, setAmount] = useState('');
  const [open, setOpen] = useState(false);
  const back = useMutation({
    mutationFn: () => unwrap(commands.returnReceivable(r.id, amount)),
    onSuccess: async () => {
      setAmount('');
      await refresh();
    },
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeReceivable(r.id)),
    onSuccess: refresh,
  });
  const error = [back.error, remove.error].find((e) => e !== null);
  return (
    <li className="py-3" data-testid={`rec-${r.debtor}`}>
      <div className="flex flex-wrap justify-between gap-2">
        <strong>{r.debtor}</strong>
        <span>{r.outstanding.formatted}</span>
      </div>
      <p className="text-sm opacity-80">
        {t('rec.line', {
          amount: r.amount.formatted,
          returned: r.returned.formatted,
          date: r.due_on ?? t('rec.noDue'),
        })}
      </p>
      {r.due && (
        <p role="status" className="text-sm" data-testid="rec-due">
          {t('rec.dueGentle', { name: r.debtor })}
        </p>
      )}
      <form
        className="mt-1 flex flex-wrap gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (amount.trim() !== '') back.mutate();
        }}
      >
        <input
          aria-label={t('rec.returnAmount', { name: r.debtor })}
          className="w-36 rounded border border-accent/50 bg-transparent p-1"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
          }}
        />
        <button type="submit" className="rounded border border-accent px-3 py-0.5">
          {t('rec.returned')}
        </button>
        <button
          type="button"
          className="text-sm underline"
          onClick={() => {
            setOpen((v) => !v);
          }}
        >
          {t('rec.receipt')}
        </button>
        <button
          type="button"
          className="text-sm underline"
          onClick={() => {
            remove.mutate();
          }}
        >
          {t('debts.remove')}
        </button>
      </form>
      {open && <ReceiptPanel kind="RECEIVABLE" id={r.id} />}
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

/** Foydalanuvchi bergan qarzlar. Foiz maydoni YO'Q: qarzi hasana (SPEC 2D.5). */
export function ReceivablesSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['receivables'],
    queryFn: () => unwrap(commands.listReceivables()),
  });
  const [debtor, setDebtor] = useState('');
  const [amount, setAmount] = useState('');
  const [due, setDue] = useState('');
  const add = useMutation({
    mutationFn: () =>
      unwrap(
        commands.addReceivable({
          debtor,
          amount,
          given_on: null,
          due_on: due === '' ? null : due,
          note: null,
        }),
      ),
    onSuccess: async () => {
      setDebtor('');
      setAmount('');
      setDue('');
      await queryClient.invalidateQueries();
    },
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="receivables">
      <h2 className="font-semibold">{t('rec.title')}</h2>
      <p className="text-sm opacity-80">{t('rec.hint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <label className="block text-sm">
          {t('rec.debtor')}
          <input
            className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
            value={debtor}
            onChange={(e) => {
              setDebtor(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('rec.amount')}
          <input
            inputMode="decimal"
            className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('rec.due')}
          <input
            type="date"
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={due}
            onChange={(e) => {
              setDue(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={debtor.trim() === '' || amount.trim() === ''}
        >
          {t('rec.add')}
        </button>
      </form>
      {add.error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, add.error)}
        </p>
      ) : null}
      <ul className="mt-2 divide-y divide-accent/20">
        {list.data?.map((r) => (
          <ReceivableRow key={r.id} r={r} />
        ))}
      </ul>
    </section>
  );
}

/** Maqsadlar (to'yona o'rniga jamg'arma va h.k.): imkoniyat narxi taqqoslashi shularga tayanadi. */
export function GoalsSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const goals = useQuery({ queryKey: ['goals'], queryFn: () => unwrap(commands.listGoals()) });
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [add, setAdd] = useState<Record<string, string>>({});
  const create = useMutation({
    mutationFn: () => unwrap(commands.addGoal(name, target, null)),
    onSuccess: async () => {
      setName('');
      setTarget('');
      await refresh();
    },
  });
  const contribute = useMutation({
    mutationFn: (v: { id: string; amount: string }) =>
      unwrap(commands.contributeGoal(v.id, v.amount)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => unwrap(commands.removeGoal(id)),
    onSuccess: refresh,
  });
  const error = [create.error, contribute.error, remove.error].find((e) => e !== null);
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="goals">
      <h2 className="font-semibold">{t('goals.title')}</h2>
      <p className="text-sm opacity-80">{t('goals.hint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="block text-sm">
          {t('goals.name')}
          <input
            className="mt-1 block w-44 rounded border border-accent/50 bg-transparent p-1"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('goals.target')}
          <input
            inputMode="decimal"
            className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === '' || target.trim() === ''}
        >
          {t('goals.add')}
        </button>
      </form>
      <ul className="mt-2 divide-y divide-accent/20">
        {goals.data?.map((g) => (
          <li key={g.id} className="py-2">
            <div className="flex justify-between gap-2">
              <strong>{g.name}</strong>
              <span>
                {t('goals.progress', { saved: g.saved.formatted, target: g.target.formatted })}
              </span>
            </div>
            <form
              className="mt-1 flex gap-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                const v = add[g.id] ?? '';
                if (v.trim() !== '') contribute.mutate({ id: g.id, amount: v });
              }}
            >
              <input
                aria-label={t('goals.contribute', { name: g.name })}
                className="w-32 rounded border border-accent/50 bg-transparent p-1"
                value={add[g.id] ?? ''}
                onChange={(e) => {
                  setAdd((p) => ({ ...p, [g.id]: e.target.value }));
                }}
              />
              <button type="submit" className="rounded border border-accent px-3 py-0.5">
                {t('goals.addSaved')}
              </button>
              <button
                type="button"
                className="text-sm underline"
                onClick={() => {
                  remove.mutate(g.id);
                }}
              >
                {t('debts.remove')}
              </button>
            </form>
          </li>
        ))}
      </ul>
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}
