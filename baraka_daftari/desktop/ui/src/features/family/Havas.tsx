import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type HavasDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';
import { useMembers } from '../../lib/hooks';

export function useHavas(month: string | undefined) {
  return useQuery({
    queryKey: ['havas', month],
    queryFn: () => unwrap(commands.havasReport(month ?? '')),
    enabled: month !== undefined,
  });
}

/** Yumshoq ogohlantirish: hech narsa bloklanmaydi, ohang ayblamaydi. */
export function HavasStatus({ report }: { report: HavasDto }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2" data-testid="havas-status">
      <p className="text-sm opacity-80">{t('havas.spent', { amount: report.spent.formatted })}</p>
      {report.limit ? (
        <>
          <p className="text-lg font-semibold">
            {t('havas.limit', { amount: report.limit.formatted })} · {formatBp(report.used_bp ?? 0)}
          </p>
          <div className="h-2 rounded bg-accent/10" aria-hidden="true">
            <div
              className="h-2 rounded bg-accent"
              style={{ width: `${String(Math.min(100, (report.used_bp ?? 0) / 100))}%` }}
            />
          </div>
          {report.state === 'NEAR' && <p role="status">{t('havas.near')}</p>}
          {report.state === 'OVER' && <p role="status">{t('havas.over')}</p>}
        </>
      ) : (
        <p>{t('havas.noLimit')}</p>
      )}
      {report.debt_funded.minor !== '0' && (
        <p className="text-sm">⚑ {t('havas.debt', { amount: report.debt_funded.formatted })}</p>
      )}
      {report.gifts_excluded.minor !== '0' && (
        <p className="text-sm opacity-80">
          {t('havas.gifts', { amount: report.gifts_excluded.formatted })}
        </p>
      )}
      {report.ostentation.minor !== '0' && (
        <p className="text-sm opacity-80">
          {t('havas.ostentation', { amount: report.ostentation.formatted })}
        </p>
      )}
      {report.charity.minor !== '0' && (
        <p className="text-sm opacity-80">
          {t('havas.charity', { amount: report.charity.formatted })}
        </p>
      )}
    </div>
  );
}

function PinField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <input
      type="password"
      inputMode="numeric"
      autoComplete="off"
      maxLength={6}
      aria-label={label}
      placeholder={label}
      className="w-28 rounded border border-accent/50 bg-transparent p-1 text-center tracking-widest"
      value={value}
      onChange={(e) => {
        onChange(e.target.value.replace(/\D/g, ''));
      }}
    />
  );
}

/** Kutilayotgan taklif: har bir kattalar o'z PIN'i bilan rozilik beradi. */
export function ConsentPanel({ report }: { report: HavasDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pins, setPins] = useState<Record<string, string>>({});
  const consent = useMutation({
    mutationFn: (v: { memberId: string; pin: string }) =>
      unwrap(commands.consentLimit(report.pending?.limit_id ?? '', v.memberId, v.pin)),
    onSuccess: async (_d, v) => {
      setPins((p) => ({ ...p, [v.memberId]: '' }));
      await queryClient.invalidateQueries();
    },
    onError: (_e, v) => {
      setPins((p) => ({ ...p, [v.memberId]: '' }));
    },
  });
  const pending = report.pending;
  if (!pending) return null;
  return (
    <section className="rounded border border-accent/40 p-3" aria-label={t('havas.pendingTitle')}>
      <h3 className="font-semibold">
        {t('havas.pendingTitle')}: {pending.amount.formatted}
      </h3>
      <p className="text-sm opacity-80">{t('havas.pendingHint')}</p>
      <p className="mt-1 text-sm">{t('havas.agreed', { names: pending.consented.join(', ') })}</p>
      <ul className="mt-2 space-y-2">
        {pending.missing.map((m) => (
          <li key={m.id} className="flex items-center gap-2">
            <span className="w-32">{m.name}</span>
            <PinField
              label={t('havas.pinOf', { name: m.name })}
              value={pins[m.id] ?? ''}
              onChange={(v) => {
                setPins((p) => ({ ...p, [m.id]: v }));
              }}
            />
            <button
              type="button"
              className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
              disabled={(pins[m.id] ?? '').length !== 6 || consent.isPending}
              onClick={() => {
                consent.mutate({ memberId: m.id, pin: pins[m.id] ?? '' });
              }}
            >
              {t('havas.agree')}
            </button>
          </li>
        ))}
      </ul>
      <div role="alert" className="mt-1 min-h-5 text-sm">
        {consent.error ? errorMessage(t, consent.error) : null}
      </div>
    </section>
  );
}

/** Yangi chegara taklif qilish: taklif qiluvchi o'z PIN'i bilan. */
export function ProposeForm() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const members = useMembers();
  const adults = members.data?.filter((m) => m.role === 'ADULT' && m.has_pin) ?? [];
  const [memberId, setMemberId] = useState('');
  const [pin, setPin] = useState('');
  const [amount, setAmount] = useState('');
  const who = memberId || adults[0]?.id || '';
  const propose = useMutation({
    mutationFn: () => unwrap(commands.proposeLimit(who, pin, amount)),
    onSuccess: async () => {
      setAmount('');
      setPin('');
      await queryClient.invalidateQueries();
    },
    onError: () => {
      setPin('');
    },
  });
  return (
    <form
      className="flex flex-wrap items-center gap-2"
      aria-label={t('havas.propose')}
      onSubmit={(e) => {
        e.preventDefault();
        propose.mutate();
      }}
    >
      <select
        aria-label={t('havas.proposer')}
        className="rounded border border-accent/50 bg-transparent p-1"
        value={who}
        onChange={(e) => {
          setMemberId(e.target.value);
        }}
      >
        {adults.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
      <input
        aria-label={t('havas.amount')}
        placeholder={t('havas.amount')}
        className="w-40 rounded border border-accent/50 bg-transparent p-1"
        value={amount}
        onChange={(e) => {
          setAmount(e.target.value);
        }}
      />
      <PinField label={t('havas.yourPin')} value={pin} onChange={setPin} />
      <button
        type="submit"
        className="rounded border border-accent px-3 py-1 disabled:opacity-50"
        disabled={who === '' || pin.length !== 6 || amount.trim() === '' || propose.isPending}
      >
        {t('havas.propose')}
      </button>
      <div role="alert" className="w-full min-h-5 text-sm">
        {propose.error ? errorMessage(t, propose.error) : null}
      </div>
    </form>
  );
}
