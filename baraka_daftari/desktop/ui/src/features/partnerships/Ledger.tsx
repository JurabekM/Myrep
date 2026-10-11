import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto, type PeriodDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

function Distribution({ p }: { p: PeriodDto }) {
  const { t } = useTranslation();
  return (
    <ul className="mt-1 text-sm" data-testid={`dist-${String(p.period_no)}`}>
      {p.distribution.map((d) => (
        <li key={d.party_name}>
          {d.party_name} ({t(`partner.roles.${d.role}`)}): <strong>{d.amount.formatted}</strong>
          {d.buyout_delta.minor !== '0'
            ? ` · ${t('ledger.buyoutDelta', { amount: d.buyout_delta.formatted })}`
            : ''}
        </li>
      ))}
    </ul>
  );
}

function EntryRow({
  e,
  locked,
  readOnly,
}: {
  e: PeriodDto['entries'][number];
  locked: boolean;
  readOnly: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeVentureEntry(e.id)),
    onSuccess: refresh,
  });
  const attach = useMutation({
    mutationFn: () => unwrap(commands.attachEvidence(e.id)),
    onSuccess: refresh,
  });
  const exportEv = useMutation({ mutationFn: (id: string) => unwrap(commands.exportEvidence(id)) });
  const error = [remove.error, attach.error, exportEv.error].find((x) => x !== null);
  return (
    <li className="py-2 text-sm" data-testid={`entry-${e.description}`}>
      <div className="flex flex-wrap justify-between gap-2">
        <span>
          {e.occurred_on} · {t(`ledger.kinds.${e.kind}`)} · {e.description}
          {e.force_majeure && (
            <span className="ml-2 rounded border border-current px-1 text-xs font-semibold">
              {t('ledger.forceMajeure')}
            </span>
          )}
        </span>
        <strong>{e.amount.formatted}</strong>
      </div>
      {e.note && <p className="text-xs opacity-80">{e.note}</p>}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {e.attachments.map((a) => (
          <button
            key={a.id}
            type="button"
            className="underline"
            onClick={() => {
              exportEv.mutate(a.id);
            }}
          >
            {t('ledger.evidence', { name: a.filename })}
          </button>
        ))}
        {!locked && !readOnly && (
          <>
            <button
              type="button"
              className="underline"
              onClick={() => {
                attach.mutate();
              }}
            >
              {t('ledger.attach', { name: e.description })}
            </button>
            <button
              type="button"
              className="underline"
              onClick={() => {
                remove.mutate();
              }}
            >
              {t('debts.remove')}
            </button>
          </>
        )}
      </div>
      {error ? <p role="alert">{errorMessage(t, error)}</p> : null}
    </li>
  );
}

/**
 * Sheriklik kassa daftari: biznes puli uy pulidan ajratilgan; xonadon byudjetiga faqat taqsimlangan foyda
 * ulushi orqali bog'lanadi. Yopilgan davr o'zgarmaydi. Kapital egasi uchun faqat o'qish.
 */
export function Ledger({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const ledger = useQuery({
    queryKey: ['ledger', p.id],
    queryFn: () => unwrap(commands.ventureLedger(p.id)),
  });
  const [kind, setKind] = useState<'INCOME' | 'EXPENSE'>('INCOME');
  const [desc, setDesc] = useState('');
  const [amountText, setAmountText] = useState('');
  const [fm, setFm] = useState(false);
  const [note, setNote] = useState('');
  const [negligence, setNegligence] = useState('');
  const [saved, setSaved] = useState<string | null>(null);
  const add = useMutation({
    mutationFn: () =>
      unwrap(
        commands.addVentureEntry(p.id, {
          kind: fm ? 'EXPENSE' : kind,
          description: desc,
          amount: amountText,
          occurred_on: null,
          note: note.trim() === '' ? null : note,
          force_majeure: fm,
        }),
      ),
    onSuccess: async () => {
      setDesc('');
      setAmountText('');
      setNote('');
      setFm(false);
      await refresh();
    },
  });
  const close = useMutation({
    mutationFn: () =>
      unwrap(commands.closeVenturePeriod(p.id, null, negligence.trim() === '' ? null : negligence)),
    onSuccess: async () => {
      setNegligence('');
      await refresh();
    },
  });
  const report = useMutation({
    mutationFn: (id: string) => unwrap(commands.exportPeriodReport(id)),
    onSuccess: (n) => {
      setSaved(n);
    },
  });
  const l = ledger.data;
  if (!l?.active) return null;
  const error = [add.error, close.error, report.error].find((x) => x !== null);
  return (
    <section className="rounded border border-accent/30 p-3" data-testid="ledger">
      <h4 className="font-semibold">{t('ledger.title')}</h4>
      <p className="text-xs opacity-70">{t('ledger.separate')}</p>
      {l.read_only && (
        <p role="status" className="mt-1 text-sm font-medium" data-testid="read-only">
          {t('ledger.readOnly')}
        </p>
      )}
      {l.open && (
        <div className="mt-2">
          <h5 className="text-sm font-medium">
            {t('ledger.openPeriod', { n: l.open.period_no, from: l.open.start_date })}
          </h5>
          <ul className="divide-y divide-accent/20">
            {l.open.entries.map((e) => (
              <EntryRow key={e.id} e={e} locked={false} readOnly={l.read_only} />
            ))}
          </ul>
          <p className="mt-1 text-sm" data-testid="open-totals">
            {t('ledger.totals', {
              income: l.open.income.formatted,
              expenses: l.open.expenses.formatted,
              net: l.open.net.formatted,
            })}
          </p>
        </div>
      )}
      {!l.read_only && (
        <>
          <form
            className="mt-2 flex flex-wrap items-end gap-2 text-sm"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              add.mutate();
            }}
          >
            <label className="block">
              {t('ledger.kind')}
              <select
                className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
                value={fm ? 'EXPENSE' : kind}
                disabled={fm}
                onChange={(e) => {
                  setKind(e.target.value as 'INCOME' | 'EXPENSE');
                }}
              >
                <option value="INCOME">{t('ledger.kinds.INCOME')}</option>
                <option value="EXPENSE">{t('ledger.kinds.EXPENSE')}</option>
              </select>
            </label>
            <label className="block">
              {t('ledger.desc')}
              <input
                className="mt-1 block w-44 rounded border border-accent/50 bg-transparent p-1"
                value={desc}
                onChange={(e) => {
                  setDesc(e.target.value);
                }}
              />
            </label>
            <label className="block">
              {t('ledger.amount')}
              <input
                inputMode="decimal"
                className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
                value={amountText}
                onChange={(e) => {
                  setAmountText(e.target.value);
                }}
              />
            </label>
            <label className="block">
              {t('ledger.note')}
              <input
                className="mt-1 block w-44 rounded border border-accent/50 bg-transparent p-1"
                value={note}
                onChange={(e) => {
                  setNote(e.target.value);
                }}
              />
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={fm}
                onChange={(e) => {
                  setFm(e.target.checked);
                }}
              />
              {t('ledger.forceMajeureLabel')}
            </label>
            <button
              type="submit"
              className="rounded border border-accent px-3 py-1 disabled:opacity-50"
              disabled={desc.trim() === '' || amountText.trim() === ''}
            >
              {t('ledger.add')}
            </button>
          </form>
          {l.open && l.open.entries.length > 0 && (
            <form
              className="mt-3 flex flex-wrap items-end gap-2 text-sm"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                close.mutate();
              }}
            >
              {p.kind === 'MUDARABA' && (
                <label className="block">
                  {t('ledger.negligence')}
                  <input
                    className="mt-1 block w-56 rounded border border-accent/50 bg-transparent p-1"
                    value={negligence}
                    onChange={(e) => {
                      setNegligence(e.target.value);
                    }}
                  />
                </label>
              )}
              <button type="submit" className="rounded bg-accent px-3 py-1 text-paper">
                {t('ledger.close')}
              </button>
              <span className="text-xs opacity-70">{t('ledger.closeHint')}</span>
            </form>
          )}
        </>
      )}
      {l.closed.length > 0 && (
        <div className="mt-3">
          <h5 className="text-sm font-medium">{t('ledger.closedTitle')}</h5>
          {l.closed.map((c) => (
            <details
              key={c.id}
              className="mt-1 text-sm"
              data-testid={`closed-${String(c.period_no)}`}
            >
              <summary>
                {t('ledger.closedPeriod', {
                  n: c.period_no,
                  from: c.start_date,
                  to: c.end_date ?? '',
                  net: c.net.formatted,
                })}
              </summary>
              <ul className="divide-y divide-accent/20">
                {c.entries.map((e) => (
                  <EntryRow key={e.id} e={e} locked readOnly={l.read_only} />
                ))}
              </ul>
              <Distribution p={c} />
              <p className="text-xs opacity-70">{t('ledger.immutable')}</p>
              <button
                type="button"
                className="mt-1 underline"
                onClick={() => {
                  report.mutate(c.id);
                }}
              >
                {t('ledger.report')}
              </button>
            </details>
          ))}
        </div>
      )}
      {saved && (
        <p role="status" className="text-sm">
          {t('receipt.saved', { name: saved })}
        </p>
      )}
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}
