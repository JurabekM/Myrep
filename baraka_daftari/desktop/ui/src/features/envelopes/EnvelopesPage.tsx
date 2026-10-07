import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type EnvelopeDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';
import { useCategories } from '../../lib/hooks';

function EnvelopeCard({ e }: { e: EnvelopeDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [leftover, setLeftover] = useState('');
  const refresh = () => queryClient.invalidateQueries();
  const close = useMutation({
    mutationFn: () => unwrap(commands.closeEnvelopeWeek(e.id, leftover)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeEnvelope(e.id)),
    onSuccess: refresh,
  });
  return (
    <li className="rounded-lg border border-accent/30 p-4" data-testid={`env-${e.name}`}>
      <div className="flex items-baseline justify-between">
        <strong className="text-lg">{e.name}</strong>
        <span>{t('env.limit', { amount: e.limit.formatted })}</span>
      </div>
      <p className="mt-1">
        {t('env.spent', { spent: e.spent.formatted, bp: formatBp(e.used_bp) })}
      </p>
      <div className="mt-1 h-2 rounded bg-accent/10" aria-hidden="true">
        <div
          className="h-2 rounded bg-accent"
          style={{ width: `${String(Math.min(100, e.used_bp / 100))}%` }}
        />
      </div>
      <p className="mt-2 text-lg font-semibold" data-testid="env-fill">
        {t('env.fill', { amount: e.cash_to_fill.formatted })}
      </p>
      <p className="text-sm opacity-80">{t('env.remaining', { amount: e.remaining.formatted })}</p>
      {e.state === 'NEAR' && (
        <p role="status" className="text-sm">
          {t('env.near')}
        </p>
      )}
      {e.state === 'OVER' && (
        <p role="status" className="text-sm">
          {t('env.over')}
        </p>
      )}
      {e.closed_difference ? (
        <p className="mt-2 text-sm" data-testid="env-closed">
          {t('env.closed', {
            leftover: e.closed_leftover?.formatted ?? '',
            diff: e.closed_difference.formatted,
          })}
        </p>
      ) : null}
      <form
        className="mt-2 flex gap-2"
        onSubmit={(ev) => {
          ev.preventDefault();
          close.mutate();
        }}
      >
        <input
          aria-label={t('env.leftover')}
          placeholder={t('env.leftover')}
          className="flex-1 rounded border border-accent/50 bg-transparent p-1"
          value={leftover}
          onChange={(ev) => {
            setLeftover(ev.target.value);
          }}
        />
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={leftover.trim() === ''}
        >
          {t('env.close')}
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
      </form>
      {[close.error, remove.error].map((er, i) =>
        er ? (
          <p key={i} role="alert" className="text-sm">
            {errorMessage(t, er)}
          </p>
        ) : null,
      )}
    </li>
  );
}

/** «Konvertlar»: haftalik virtual konvertlar; karta bilan to'langan xarajat ham ayriladi. */
export function EnvelopesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['envelopes'],
    queryFn: () => unwrap(commands.listEnvelopes()),
  });
  const categories = useCategories();
  const [name, setName] = useState('');
  const [limit, setLimit] = useState('');
  const [target, setTarget] = useState('');
  const add = useMutation({
    mutationFn: () => {
      const isNec = ['ZARUR', 'KERAK', 'HAVAS'].includes(target);
      return unwrap(
        commands.addEnvelope(
          name,
          limit,
          !isNec && target !== '' ? target : null,
          isNec ? target : null,
        ),
      );
    },
    onSuccess: async () => {
      setName('');
      setLimit('');
      await queryClient.invalidateQueries();
    },
  });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t('nav.envelopes')}</h1>
      <p className="text-sm opacity-80">{t('env.hint')}</p>
      <ul className="grid gap-4 md:grid-cols-2">
        {list.data?.map((e) => (
          <EnvelopeCard key={e.id} e={e} />
        ))}
      </ul>
      {list.data?.length === 0 && <p className="opacity-70">{t('env.empty')}</p>}
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(ev) => {
          ev.preventDefault();
          add.mutate();
        }}
      >
        <input
          aria-label={t('env.name')}
          placeholder={t('env.name')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={name}
          onChange={(ev) => {
            setName(ev.target.value);
          }}
        />
        <input
          aria-label={t('env.weeklyLimit')}
          placeholder={t('env.weeklyLimit')}
          className="w-36 rounded border border-accent/50 bg-transparent p-1"
          value={limit}
          onChange={(ev) => {
            setLimit(ev.target.value);
          }}
        />
        <select
          aria-label={t('env.counts')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={target}
          onChange={(ev) => {
            setTarget(ev.target.value);
          }}
        >
          <option value="">{t('env.countsNone')}</option>
          <optgroup label={t('env.byNecessity')}>
            {['ZARUR', 'KERAK', 'HAVAS'].map((n) => (
              <option key={n} value={n}>
                {t(`necessity.${n}`)}
              </option>
            ))}
          </optgroup>
          <optgroup label={t('env.byCategory')}>
            {categories.data
              ?.filter((c) => !c.is_charity)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </optgroup>
        </select>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === '' || limit.trim() === ''}
        >
          {t('env.add')}
        </button>
      </form>
      <div role="alert" className="min-h-5 text-sm">
        {add.error ? errorMessage(t, add.error) : null}
      </div>
    </div>
  );
}
