import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type DebtInput } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

const CREDITORS = ['BANK', 'SHOP', 'RELATIVE', 'FRIEND', 'OTHER'] as const;
const KINDS = ['MANUAL', 'ANNUITY', 'DIFFERENTIATED', 'FIXED_MARKUP'] as const;
const ALTERNATIVES = ['NONE', 'GUARD', 'RELATIVE', 'SELL_ITEM'] as const;

interface Row {
  due: string;
  amount: string;
}

/**
 * Yangi qarz ustasi. Avval «to'xta va o'yla» (zarurat/hashamat, foizsiz muqobil), keyin qarz va
 * **majburiy to'lov rejasi**; reja bo'lmasa saqlab bo'lmaydi. Mavjud qarzni kiritishda so'rov o'tkaziladi.
 */
export function AddDebt({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [existing, setExisting] = useState(false);
  const [step, setStep] = useState<'check' | 'details'>('check');
  const [need, setNeed] = useState<'NEED' | 'LUXURY'>('NEED');
  const [alternative, setAlternative] = useState<(typeof ALTERNATIVES)[number]>('NONE');
  const [creditor, setCreditor] = useState('');
  const [creditorType, setCreditorType] = useState<(typeof CREDITORS)[number]>('BANK');
  const [reason, setReason] = useState('');
  const [principal, setPrincipal] = useState('');
  const [kind, setKind] = useState<(typeof KINDS)[number]>('MANUAL');
  const [markup, setMarkup] = useState('0');
  const [months, setMonths] = useState('6');
  const [firstDue, setFirstDue] = useState('');
  const [rows, setRows] = useState<Row[]>([{ due: '', amount: '' }]);
  const [terms, setTerms] = useState('');

  const input = (): DebtInput => ({
    creditor,
    creditor_type: creditorType,
    reason: reason.trim() === '' ? null : reason,
    principal,
    schedule_kind: kind,
    fixed:
      kind === 'FIXED_MARKUP'
        ? { markup, months: Number.parseInt(months, 10) || 0, first_due: firstDue }
        : null,
    rows: kind === 'FIXED_MARKUP' ? [] : rows,
    borrowed_on: null,
    early_terms: terms.trim() === '' ? null : terms,
    check: existing ? null : { need, alternative },
  });

  const burden = useQuery({
    queryKey: [
      'debt-burden',
      step,
      JSON.stringify([principal, kind, markup, months, firstDue, rows]),
    ],
    queryFn: () => unwrap(commands.debtBurdenPreview(input())),
    enabled: step === 'details' && !existing && principal.trim() !== '',
    retry: false,
  });

  const save = useMutation({
    mutationFn: () => unwrap(commands.addDebt(input())),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      onDone();
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  const markupEntered = kind === 'FIXED_MARKUP' && /[1-9]/.test(markup);

  if (step === 'check' && !existing) {
    return (
      <div className="space-y-3 rounded-lg border border-accent p-5" data-testid="friction">
        <h3 className="font-semibold">{t('debts.friction.title')}</h3>
        <p className="text-sm opacity-80">{t('debts.friction.hint')}</p>
        <fieldset className="text-sm">
          <legend className="font-medium">{t('debts.friction.need')}</legend>
          {(['NEED', 'LUXURY'] as const).map((n) => (
            <label key={n} className="mr-4 inline-flex items-center gap-1">
              <input
                type="radio"
                name="need"
                checked={need === n}
                onChange={() => {
                  setNeed(n);
                }}
              />
              {t(`debts.friction.needOptions.${n}`)}
            </label>
          ))}
        </fieldset>
        <label className="block text-sm">
          {t('debts.friction.alternative')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={alternative}
            onChange={(e) => {
              setAlternative(e.target.value as (typeof ALTERNATIVES)[number]);
            }}
          >
            {ALTERNATIVES.map((a) => (
              <option key={a} value={a}>
                {t(`debts.friction.alternatives.${a}`)}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm">{t('debts.friction.burdenNext')}</p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded bg-accent px-3 py-1 text-paper"
            onClick={() => {
              setStep('details');
            }}
          >
            {t('debts.friction.continue')}
          </button>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={existing}
              onChange={(e) => {
                setExisting(e.target.checked);
              }}
            />
            {t('debts.existing')}
          </label>
          <button type="button" className="text-sm underline" onClick={onDone}>
            {t('debts.cancel')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="space-y-3 rounded-lg border border-accent p-5" onSubmit={submit}>
      <h3 className="font-semibold">{t('debts.addTitle')}</h3>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={existing}
          onChange={(e) => {
            setExisting(e.target.checked);
          }}
        />
        {t('debts.existing')}
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          {t('debts.creditor')}
          <input
            className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
            value={creditor}
            onChange={(e) => {
              setCreditor(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('debts.creditorType')}
          <select
            className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
            value={creditorType}
            onChange={(e) => {
              setCreditorType(e.target.value as (typeof CREDITORS)[number]);
            }}
          >
            {CREDITORS.map((c) => (
              <option key={c} value={c}>
                {t(`debts.creditorTypes.${c}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          {t('debts.principal')}
          <input
            inputMode="decimal"
            className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
            value={principal}
            onChange={(e) => {
              setPrincipal(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('debts.reason')}
          <input
            className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
            }}
          />
        </label>
      </div>

      <fieldset className="space-y-2 rounded border border-accent/30 p-3">
        <legend className="px-1 text-sm font-medium">{t('debts.plan')}</legend>
        <p className="text-sm opacity-80">{t('debts.planHint')}</p>
        <label className="block text-sm">
          {t('debts.scheduleKind')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as (typeof KINDS)[number]);
            }}
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t(`debts.kinds.${k}`)}
              </option>
            ))}
          </select>
        </label>
        {kind === 'FIXED_MARKUP' ? (
          <div className="flex flex-wrap gap-3">
            <label className="block text-sm">
              {t('debts.markup')}
              <input
                inputMode="decimal"
                className="mt-1 block w-32 rounded border border-accent/50 bg-transparent p-1"
                value={markup}
                onChange={(e) => {
                  setMarkup(e.target.value);
                }}
              />
            </label>
            <label className="block text-sm">
              {t('debts.months')}
              <input
                inputMode="numeric"
                className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
                value={months}
                onChange={(e) => {
                  setMonths(e.target.value);
                }}
              />
            </label>
            <label className="block text-sm">
              {t('debts.firstDue')}
              <input
                type="date"
                className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
                value={firstDue}
                onChange={(e) => {
                  setFirstDue(e.target.value);
                }}
              />
            </label>
          </div>
        ) : (
          <div className="space-y-1">
            {rows.map((r, i) => (
              <div key={i} className="flex flex-wrap gap-2">
                <input
                  type="date"
                  aria-label={t('debts.rowDue', { n: i + 1 })}
                  className="rounded border border-accent/50 bg-transparent p-1"
                  value={r.due}
                  onChange={(e) => {
                    setRows((p) => p.map((x, j) => (j === i ? { ...x, due: e.target.value } : x)));
                  }}
                />
                <input
                  inputMode="decimal"
                  aria-label={t('debts.rowAmount', { n: i + 1 })}
                  className="w-36 rounded border border-accent/50 bg-transparent p-1"
                  value={r.amount}
                  onChange={(e) => {
                    setRows((p) =>
                      p.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)),
                    );
                  }}
                />
                {rows.length > 1 && (
                  <button
                    type="button"
                    className="text-sm underline"
                    onClick={() => {
                      setRows((p) => p.filter((_, j) => j !== i));
                    }}
                  >
                    {t('debts.rowRemove')}
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="text-sm underline"
              onClick={() => {
                setRows((p) => [...p, { due: '', amount: '' }]);
              }}
            >
              {t('debts.rowAdd')}
            </button>
          </div>
        )}
        {markupEntered && (
          <p role="alert" className="text-sm font-semibold" data-testid="markup-warning">
            {t('debts.markupWarning')}
          </p>
        )}
      </fieldset>

      <label className="block text-sm">
        {t('debts.earlyTerms')}
        <input
          className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
          placeholder={t('debts.earlyTermsHint')}
          value={terms}
          onChange={(e) => {
            setTerms(e.target.value);
          }}
        />
      </label>

      {!existing && burden.data !== undefined && burden.data !== null && (
        <p className="text-sm" data-testid="burden-preview">
          {t('debts.friction.burden', { bp: formatBp(burden.data) })}
        </p>
      )}
      {save.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, save.error)}
        </p>
      ) : null}
      <div className="flex gap-3">
        <button
          type="submit"
          className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
          disabled={save.isPending || creditor.trim() === '' || principal.trim() === ''}
        >
          {t('debts.save')}
        </button>
        <button type="button" className="text-sm underline" onClick={onDone}>
          {t('debts.cancel')}
        </button>
      </div>
    </form>
  );
}
