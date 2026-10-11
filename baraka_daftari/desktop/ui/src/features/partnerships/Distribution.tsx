import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

/** Foyda/zarar taqsimoti hisobi (SPEC 2E.1). Natijani Rust hisoblaydi; zarar manfiy ko'rsatiladi. */
export function Distribution({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<'PROFIT' | 'LOSS'>('PROFIT');
  const [amount, setAmount] = useState('');
  const [negligence, setNegligence] = useState(false);
  const [note, setNote] = useState('');
  const run = useMutation({
    mutationFn: () =>
      unwrap(
        commands.previewDistribution(
          p.id,
          outcome,
          amount,
          outcome === 'LOSS' && negligence ? note : null,
        ),
      ),
  });
  return (
    <div className="rounded border border-accent/30 p-3" data-testid="distribution">
      <h4 className="font-semibold">{t('partner.distTitle')}</h4>
      <p className="text-xs opacity-70">{t('partner.distHint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-3 text-sm"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          run.mutate();
        }}
      >
        <label className="block">
          {t('partner.distOutcome')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value as 'PROFIT' | 'LOSS');
            }}
          >
            <option value="PROFIT">{t('partner.profit')}</option>
            <option value="LOSS">{t('partner.loss')}</option>
          </select>
        </label>
        <label className="block">
          {t('partner.distAmount')}
          <input
            inputMode="decimal"
            className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
            }}
          />
        </label>
        {outcome === 'LOSS' && p.kind === 'MUDARABA' && (
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={negligence}
              onChange={(e) => {
                setNegligence(e.target.checked);
              }}
            />
            {t('partner.negligence')}
          </label>
        )}
        {outcome === 'LOSS' && negligence && (
          <label className="block">
            {t('partner.negligenceNote')}
            <input
              className="mt-1 block w-56 rounded border border-accent/50 bg-transparent p-1"
              value={note}
              onChange={(e) => {
                setNote(e.target.value);
              }}
            />
          </label>
        )}
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1 disabled:opacity-50"
          disabled={amount.trim() === ''}
        >
          {t('partner.distRun')}
        </button>
      </form>
      {run.error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, run.error)}
        </p>
      ) : null}
      {run.data && (
        <ul className="mt-2 text-sm" data-testid="dist-result">
          {run.data.map((r) => (
            <li key={r.name}>
              {r.name}: <strong>{r.amount.formatted}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
