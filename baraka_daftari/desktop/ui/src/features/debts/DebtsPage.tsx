import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type DebtDto } from '../../bindings';
import { errorMessage, formatBp, formatMilli, unwrap } from '../../lib/api';

import { AddDebt } from './AddDebt';
import { Contributors } from './Contributors';
import { Planner } from './Planner';
import { RecoveryCard } from './RecoveryCard';
import { Sellables } from './Sellables';
import { ReceiptPanel } from './ReceiptPanel';
import { GoalsSection, ReceivablesSection } from './ReceivablesGoals';

function Overview() {
  const { t } = useTranslation();
  const overview = useQuery({
    queryKey: ['debt-overview'],
    queryFn: () => unwrap(commands.debtOverview()),
  });
  const o = overview.data;
  if (!o) return null;
  return (
    <section className="rounded-lg border border-accent p-5" data-testid="debt-overview">
      <p className="text-sm italic opacity-80">{t('debts.wound')}</p>
      <p className="mt-2 text-4xl font-semibold" data-testid="debt-total">
        {o.total_remaining.formatted}
      </p>
      <ul className="mt-2 space-y-0.5 text-sm">
        <li>
          {t('debts.monthlyLoad', { amount: o.monthly_load.formatted })}
          {o.burden_bp !== null ? ` · ${t('debts.ofIncome', { bp: formatBp(o.burden_bp) })}` : ''}
        </li>
        <li>{t('debts.excessTotal', { amount: o.excess_total.formatted })}</li>
        {o.nasiya_remaining.minor !== '0' && (
          <li>{t('debts.nasiyaIncluded', { amount: o.nasiya_remaining.formatted })}</li>
        )}
        {o.receivables_outstanding.minor !== '0' && (
          <li>{t('debts.receivablesOut', { amount: o.receivables_outstanding.formatted })}</li>
        )}
      </ul>
      {o.has_markup_debt && (
        <p role="alert" className="mt-2 text-sm font-semibold">
          {t('debts.markupDebtNote')}
        </p>
      )}
    </section>
  );
}

function CostPanel({ d }: { d: DebtDto }) {
  const { t } = useTranslation();
  return (
    <div className="mt-2 rounded bg-accent/10 p-3 text-sm" data-testid={`cost-${d.creditor}`}>
      <h4 className="font-semibold">{t('debts.realCost')}</h4>
      <p>
        {t('debts.costLine', {
          principal: d.principal.formatted,
          total: d.cost.total.formatted,
          excess: d.cost.excess.formatted,
        })}
      </p>
      {d.cost.excess_bp > 0 && <p>{t('debts.costShare', { bp: formatBp(d.cost.excess_bp) })}</p>}
      {d.equivalences.map((e) => (
        <p key={e.goal_name} data-testid="equivalence">
          {t('debts.equals', { times: formatMilli(e.times_milli), goal: e.goal_name })}
        </p>
      ))}
    </div>
  );
}

function DebtCard({ d }: { d: DebtDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const [amount, setAmount] = useState('');
  const [open, setOpen] = useState(false);
  const [terms, setTerms] = useState(d.early_terms ?? '');
  const pay = useMutation({
    mutationFn: () => unwrap(commands.payDebt(d.id, amount)),
    onSuccess: async () => {
      setAmount('');
      await refresh();
    },
  });
  const saveTerms = useMutation({
    mutationFn: () => unwrap(commands.setDebtEarlyTerms(d.id, terms)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeDebt(d.id)),
    onSuccess: refresh,
  });
  const error = [pay.error, saveTerms.error, remove.error].find((e) => e !== null);
  return (
    <li className={`py-4 ${d.active ? '' : 'opacity-60'}`} data-testid={`debt-${d.creditor}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <strong>
          {d.creditor}{' '}
          <span className="text-sm font-normal opacity-70">
            · {t(`debts.creditorTypes.${d.creditor_type}`)}
            {d.reason ? ` · ${d.reason}` : ''}
          </span>
        </strong>
        <span className="font-semibold">
          {d.active ? d.remaining.formatted : t('debts.closed', { date: d.closed_on ?? '' })}
        </span>
      </div>
      <p className="text-sm opacity-80">
        {t('debts.line', {
          monthly: d.monthly.formatted,
          due: d.due_date,
          kind: t(`debts.kinds.${d.schedule_kind}`),
        })}
      </p>
      {d.next_due && d.active && (
        <p className={`text-sm ${d.overdue ? 'font-semibold' : ''}`} data-testid="next-due">
          {d.overdue
            ? t('debts.overdue', { date: d.next_due.due_on, amount: d.next_due.amount.formatted })
            : t('debts.nextDue', { date: d.next_due.due_on, amount: d.next_due.amount.formatted })}
        </p>
      )}
      {d.has_markup && (
        <p role="alert" className="text-sm font-semibold" data-testid="markup-flag">
          {t('debts.markupFlag', { amount: d.markup.formatted })}
        </p>
      )}
      <CostPanel d={d} />
      {d.check && (
        <p className="mt-1 text-xs opacity-70">
          {t('debts.checkSaved', {
            need: t(`debts.friction.needOptions.${d.check.need}`),
            alt: t(`debts.friction.alternatives.${d.check.alternative}`),
          })}
        </p>
      )}
      {d.active && (
        <form
          className="mt-2 flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (amount.trim() !== '') pay.mutate();
          }}
        >
          <input
            aria-label={t('debts.payAmount', { name: d.creditor })}
            placeholder={t('debts.payPlaceholder')}
            className="w-40 rounded border border-accent/50 bg-transparent p-1"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
            }}
          />
          <button type="submit" className="rounded border border-accent px-3 py-0.5">
            {t('debts.pay')}
          </button>
        </form>
      )}
      <div className="mt-2 flex flex-wrap gap-3 text-sm">
        <button
          type="button"
          className="underline"
          onClick={() => {
            setOpen((v) => !v);
          }}
        >
          {open ? t('debts.hideDetails') : t('debts.showDetails')}
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
      </div>
      {open && (
        <div className="mt-2 space-y-2">
          <table className="w-full text-sm">
            <caption className="sr-only">{t('debts.plan')}</caption>
            <tbody>
              {d.instalments.map((i) => (
                <tr key={`${i.due_on}-${i.amount.minor}`}>
                  <td>{i.due_on}</td>
                  <td className="text-right">{i.amount.formatted}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <form
            className="flex flex-wrap gap-2 text-sm"
            onSubmit={(e) => {
              e.preventDefault();
              saveTerms.mutate();
            }}
          >
            <label className="flex-1">
              {t('debts.earlyTerms')}
              <input
                className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
                value={terms}
                onChange={(e) => {
                  setTerms(e.target.value);
                }}
              />
            </label>
            <button type="submit" className="self-end rounded border border-accent px-3 py-0.5">
              {t('debts.saveTerms')}
            </button>
          </form>
          <p className="text-xs opacity-70">{t('debts.earlyDisclaimer')}</p>
          <Contributors debtId={d.id} />
          <ReceiptPanel kind="DEBT" id={d.id} />
        </div>
      )}
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

// ECharts og'ir: kalkulyator kerak bo'lgandagina yuklanadi (sovuq start tez bo'lishi uchun).
const Calculator = lazy(() => import('./Calculator').then((m) => ({ default: m.Calculator })));

export function DebtsPage() {
  const { t } = useTranslation();
  const [adding, setAdding] = useState(false);
  const list = useQuery({ queryKey: ['debts'], queryFn: () => unwrap(commands.listDebts()) });
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('nav.debts')}</h1>
        {!adding && (
          <button
            type="button"
            className="rounded bg-accent px-4 py-2 text-paper"
            onClick={() => {
              setAdding(true);
            }}
          >
            {t('debts.add')}
          </button>
        )}
      </div>
      <Overview />
      <RecoveryCard />
      {adding && (
        <AddDebt
          onDone={() => {
            setAdding(false);
          }}
        />
      )}
      <section className="rounded-lg border border-accent/30 p-5">
        <h2 className="font-semibold">{t('debts.inventory')}</h2>
        <p className="text-sm opacity-80">{t('debts.inventoryHint')}</p>
        <ul className="mt-2 divide-y divide-accent/20">
          {list.data?.map((d) => (
            <DebtCard key={d.id} d={d} />
          ))}
        </ul>
        {list.data?.length === 0 && <p className="mt-2 opacity-70">{t('debts.empty')}</p>}
        {list.error ? <p role="alert">{errorMessage(t, list.error)}</p> : null}
      </section>
      <Planner />
      <Suspense fallback={null}>
        <Calculator />
      </Suspense>
      <div className="grid gap-4 lg:grid-cols-2">
        <Sellables />
        <ReceivablesSection />
        <GoalsSection />
      </div>
    </div>
  );
}
