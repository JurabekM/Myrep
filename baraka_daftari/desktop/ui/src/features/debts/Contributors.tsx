import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

/** Qarzni bir necha kishi to'lashi: har bir a'zoning oylik ulushi va to'lagan jami (oilaviy yelkadoshlik). */
export function Contributors({ debtId }: { debtId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['contributors', debtId] });
  const list = useQuery({
    queryKey: ['contributors', debtId],
    queryFn: () => unwrap(commands.listContributors(debtId)),
  });
  const members = useQuery({
    queryKey: ['members'],
    queryFn: () => unwrap(commands.listMembers()),
  });
  const [memberId, setMemberId] = useState('');
  const [share, setShare] = useState('');
  const set = useMutation({
    mutationFn: () => unwrap(commands.setContributorShare(debtId, memberId, share)),
    onSuccess: async () => {
      setShare('');
      await refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => unwrap(commands.removeContributor(debtId, id)),
    onSuccess: refresh,
  });
  const error = [set.error, remove.error].find((e) => e !== null);
  return (
    <div className="rounded border border-accent/30 p-3" data-testid="contributors">
      <h4 className="font-semibold">{t('contrib.title')}</h4>
      <ul className="mt-1 space-y-1 text-sm">
        {list.data?.map((c) => (
          <li key={c.member_id} className="flex flex-wrap items-center gap-2">
            <span className="flex-1">
              {c.name}:{' '}
              {c.monthly_share
                ? t('contrib.share', { amount: c.monthly_share.formatted })
                : t('contrib.noShare')}
              {' · '}
              {t('contrib.paid', { amount: c.paid.formatted })}
            </span>
            {c.monthly_share && (
              <button
                type="button"
                className="text-xs underline"
                onClick={() => {
                  remove.mutate(c.member_id);
                }}
              >
                {t('contrib.removeShare')}
              </button>
            )}
          </li>
        ))}
      </ul>
      <form
        className="mt-2 flex flex-wrap items-end gap-2 text-sm"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (memberId !== '' && share.trim() !== '') set.mutate();
        }}
      >
        <label className="block">
          {t('contrib.member')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={memberId}
            onChange={(e) => {
              setMemberId(e.target.value);
            }}
          >
            <option value="" />
            {members.data?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          {t('contrib.monthly')}
          <input
            inputMode="decimal"
            className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
            value={share}
            onChange={(e) => {
              setShare(e.target.value);
            }}
          />
        </label>
        <button type="submit" className="rounded border border-accent px-3 py-0.5">
          {t('contrib.set')}
        </button>
      </form>
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </div>
  );
}
