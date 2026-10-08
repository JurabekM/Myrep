import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands, type CeremonyDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

import { Compare } from './Compare';

const KINDS = ['WEDDING', 'BESHIK', 'SUNNAT', 'MARAKA', 'OTHER'] as const;
const SOURCES = ['SAVINGS', 'FAMILY', 'EXPECTED_GIFTS', 'DEBT'] as const;

function useRefresh() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}

function NewPlan() {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [name, setName] = useState('');
  const [kind, setKind] = useState<(typeof KINDS)[number]>('WEDDING');
  const [date, setDate] = useState('');
  const create = useMutation({
    mutationFn: () => unwrap(commands.createCeremony(name, kind, date === '' ? null : date)),
    onSuccess: async () => {
      setName('');
      setDate('');
      await refresh();
    },
  });
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        create.mutate();
      }}
    >
      <label className="block text-sm">
        {t('cer.name')}
        <input
          className="mt-1 block w-56 rounded border border-accent/50 bg-transparent p-1"
          placeholder={t('cer.namePlaceholder')}
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('cer.kind')}
        <select
          className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
          value={kind}
          onChange={(e) => {
            setKind(e.target.value as (typeof KINDS)[number]);
          }}
        >
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {t(`cer.kinds.${k}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        {t('cer.date')}
        <input
          type="date"
          className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
          value={date}
          onChange={(e) => {
            setDate(e.target.value);
          }}
        />
      </label>
      <button
        type="submit"
        className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
        disabled={name.trim() === ''}
      >
        {t('cer.create')}
      </button>
      {create.error ? (
        <p role="alert" className="w-full text-sm">
          {errorMessage(t, create.error)}
        </p>
      ) : null}
    </form>
  );
}

function Discussion({ p }: { p: CeremonyDto }) {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const setPage = useNav((s) => s.setPage);
  const [note, setNote] = useState('');
  const save = useMutation({
    mutationFn: () => unwrap(commands.recordCeremonyDiscussion(p.id, note)),
    onSuccess: async () => {
      setNote('');
      await refresh();
    },
  });
  return (
    <div className="rounded border border-accent p-3" data-testid="discussion">
      <h3 className="font-semibold">{t('cer.discussTitle')}</h3>
      <p className="text-sm opacity-80">{t('cer.discussHint')}</p>
      <ul className="mt-1 list-disc pl-5 text-sm">
        {(['smaller', 'longer', 'gifts', 'sell', 'family'] as const).map((k) => (
          <li key={k}>{t(`cer.prompts.${k}`)}</li>
        ))}
      </ul>
      <p className="mt-1 text-xs italic opacity-70">{t('cer.proverb')}</p>
      {p.discussed ? (
        <p className="mt-2 text-sm" data-testid="discussed-note">
          {t('cer.discussed', { note: p.discussion_note ?? '' })}
        </p>
      ) : (
        <form
          className="mt-2 space-y-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <label className="block text-sm">
            {t('cer.discussNote')}
            <textarea
              className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
              rows={2}
              value={note}
              onChange={(e) => {
                setNote(e.target.value);
              }}
            />
          </label>
          <div className="flex gap-3">
            <button
              type="submit"
              className="rounded border border-accent px-3 py-1 disabled:opacity-50"
              disabled={note.trim() === ''}
            >
              {t('cer.discussDone')}
            </button>
            <button
              type="button"
              className="text-sm underline"
              onClick={() => {
                setPage('council');
              }}
            >
              {t('cer.openCouncil')}
            </button>
          </div>
        </form>
      )}
      {save.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, save.error)}
        </p>
      ) : null}
    </div>
  );
}

function PlanCard({ p }: { p: CeremonyDto }) {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [name, setName] = useState('');
  const [qty, setQty] = useState('1');
  const [price, setPrice] = useState('');
  const [source, setSource] = useState<(typeof SOURCES)[number]>('SAVINGS');
  const [target, setTarget] = useState('');
  const [saved, setSaved] = useState<string | null>(null);
  const addLine = useMutation({
    mutationFn: () =>
      unwrap(commands.addCeremonyLine(p.id, name, Number.parseInt(qty, 10) || 0, price, source)),
    onSuccess: async () => {
      setName('');
      setPrice('');
      await refresh();
    },
  });
  const removeLine = useMutation({
    mutationFn: (id: string) => unwrap(commands.removeCeremonyLine(id)),
    onSuccess: refresh,
  });
  const setDate = useMutation({
    mutationFn: (d: string) => unwrap(commands.setCeremonyDate(p.id, d === '' ? null : d)),
    onSuccess: refresh,
  });
  const status = useMutation({
    mutationFn: (s: 'DRAFT' | 'CONFIRMED') => unwrap(commands.setCeremonyStatus(p.id, s)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeCeremony(p.id)),
    onSuccess: refresh,
  });
  const goal = useMutation({
    mutationFn: () => unwrap(commands.openGiftGoal(p.id, target)),
    onSuccess: async () => {
      setTarget('');
      await refresh();
    },
  });
  const pdf = useMutation({
    mutationFn: () => unwrap(commands.exportCeremonyPdf(p.id)),
    onSuccess: (n) => {
      setSaved(n);
    },
  });
  const confirmed = p.status === 'CONFIRMED';
  const hasDebt = p.totals.debt.minor !== '0';
  const error = [
    addLine.error,
    removeLine.error,
    setDate.error,
    status.error,
    remove.error,
    goal.error,
    pdf.error,
  ].find((e) => e !== null);
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid={`plan-${p.name}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">
          {p.name}{' '}
          <span className="text-sm font-normal opacity-70">· {t(`cer.kinds.${p.kind}`)}</span>
        </h2>
        <span
          className={`rounded border px-2 text-sm ${confirmed ? 'border-current font-semibold' : 'border-accent/40'}`}
          data-testid="status"
        >
          {t(`cer.statuses.${p.status}`)}
        </span>
      </div>
      <label className="mt-2 block text-sm">
        {t('cer.date')}
        <input
          type="date"
          className="ml-2 rounded border border-accent/50 bg-transparent p-1"
          value={p.date ?? ''}
          onChange={(e) => {
            setDate.mutate(e.target.value);
          }}
        />
      </label>

      <table className="mt-3 w-full text-sm">
        <caption className="sr-only">{t('cer.lines')}</caption>
        <thead>
          <tr className="text-left">
            <th>{t('cer.lineName')}</th>
            <th className="text-right">{t('cer.qty')}</th>
            <th className="text-right">{t('cer.unit')}</th>
            <th className="text-right">{t('cer.lineTotal')}</th>
            <th>{t('cer.source')}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {p.lines.map((l) => (
            <tr key={l.id}>
              <td>{l.name}</td>
              <td className="text-right">{l.qty}</td>
              <td className="text-right">{l.unit_price.formatted}</td>
              <td className="text-right">{l.total.formatted}</td>
              <td className={l.funding === 'DEBT' ? 'font-semibold' : ''}>
                {t(`cer.sources.${l.funding}`)}
              </td>
              <td>
                <button
                  type="button"
                  className="text-xs underline"
                  aria-label={t('cer.removeLine', { name: l.name })}
                  onClick={() => {
                    removeLine.mutate(l.id);
                  }}
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form
        className="mt-2 flex flex-wrap items-end gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          addLine.mutate();
        }}
      >
        <label className="block text-sm">
          {t('cer.lineName')}
          <input
            className="mt-1 block w-44 rounded border border-accent/50 bg-transparent p-1"
            placeholder={t('cer.linePlaceholder')}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('cer.qty')}
          <input
            inputMode="numeric"
            className="mt-1 block w-16 rounded border border-accent/50 bg-transparent p-1"
            value={qty}
            onChange={(e) => {
              setQty(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('cer.unitPrice')}
          <input
            inputMode="decimal"
            className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
            value={price}
            onChange={(e) => {
              setPrice(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('cer.source')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={source}
            onChange={(e) => {
              setSource(e.target.value as (typeof SOURCES)[number]);
            }}
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {t(`cer.sources.${s}`)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1 disabled:opacity-50"
          disabled={name.trim() === '' || price.trim() === ''}
        >
          {t('cer.addLine')}
        </button>
      </form>

      <div className="mt-3 rounded bg-accent/10 p-3 text-sm" data-testid="totals">
        <p className="text-lg font-semibold">
          {t('cer.totalIs', { amount: p.totals.total.formatted })}
        </p>
        <ul>
          {(
            [
              ['SAVINGS', p.totals.savings],
              ['FAMILY', p.totals.family],
              ['EXPECTED_GIFTS', p.totals.expected_gifts],
              ['DEBT', p.totals.debt],
            ] as const
          ).map(([k, v]) => (
            <li key={k}>
              {t(`cer.sources.${k}`)}: {v.formatted}
            </li>
          ))}
        </ul>
        {hasDebt && (
          <p role="alert" className="mt-1 font-semibold" data-testid="debt-warning">
            {t('cer.debtWarning', {
              amount: p.totals.debt.formatted,
              bp: formatBp(p.totals.debt_bp),
            })}
          </p>
        )}
      </div>

      {hasDebt && (
        <div className="mt-3">
          <Discussion p={p} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        {confirmed ? (
          <button
            type="button"
            className="rounded border border-accent px-3 py-1"
            onClick={() => {
              status.mutate('DRAFT');
            }}
          >
            {t('cer.reopen')}
          </button>
        ) : (
          <button
            type="button"
            className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
            disabled={p.confirm_blocker !== null}
            onClick={() => {
              status.mutate('CONFIRMED');
            }}
          >
            {t('cer.confirm')}
          </button>
        )}
        {!confirmed && p.confirm_blocker && (
          <span className="text-sm" data-testid="blocker">
            {t(`cer.blockers.${p.confirm_blocker}`)}
          </span>
        )}
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          onClick={() => {
            pdf.mutate();
          }}
        >
          {t('cer.printBudget')}
        </button>
        <button
          type="button"
          className="text-sm underline"
          onClick={() => {
            remove.mutate();
          }}
        >
          {t('cer.remove')}
        </button>
      </div>
      {saved && (
        <p role="status" className="mt-1 text-sm">
          {t('receipt.saved', { name: saved })}
        </p>
      )}

      <form
        className="mt-4 flex flex-wrap items-end gap-2 border-t border-accent/20 pt-3"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          goal.mutate();
        }}
      >
        <div className="basis-full">
          <h3 className="font-medium">{t('cer.giftGoalTitle')}</h3>
          <p className="text-sm opacity-80">{t('cer.giftGoalHint')}</p>
        </div>
        <label className="block text-sm">
          {t('cer.giftTarget')}
          <input
            inputMode="decimal"
            className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1 disabled:opacity-50"
          disabled={target.trim() === ''}
        >
          {t('cer.giftOpen')}
        </button>
      </form>
      {error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}

export function CeremoniesPage() {
  const { t } = useTranslation();
  const list = useQuery({
    queryKey: ['ceremonies'],
    queryFn: () => unwrap(commands.listCeremonies()),
  });
  const plans = list.data ?? [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('nav.ceremonies')}</h1>
      <p className="text-sm opacity-80">{t('cer.intro')}</p>
      <section className="rounded-lg border border-accent/30 p-5">
        <NewPlan />
      </section>
      {plans.map((p) => (
        <PlanCard key={p.id} p={p} />
      ))}
      {plans.length === 0 && <p className="opacity-70">{t('cer.empty')}</p>}
      {plans.length >= 2 && <Compare plans={plans} />}
    </div>
  );
}
