import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type BuyoutRowDto, type PartnershipDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

function Bar({ providerBp }: { providerBp: number }) {
  const { t } = useTranslation();
  return (
    <div
      role="img"
      aria-label={t('partner.ownershipBar', {
        provider: formatBp(providerBp),
        worker: formatBp(10_000 - providerBp),
      })}
      className="flex h-3 w-full overflow-hidden rounded bg-accent/15"
    >
      <div className="bg-accent" style={{ width: `${String(providerBp / 100)}%` }} />
    </div>
  );
}

function Rows({ rows, title }: { rows: BuyoutRowDto[]; title: string }) {
  const { t } = useTranslation();
  return (
    <table className="w-full text-sm">
      <caption className="text-left font-medium">{title}</caption>
      <thead>
        <tr className="text-left">
          <th>{t('partner.period')}</th>
          <th className="text-right">{t('partner.applied')}</th>
          <th className="text-right">{t('partner.remaining')}</th>
          <th className="w-40">{t('partner.ownership')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.period}>
            <td>
              {r.period}
              {r.date ? ` · ${r.date}` : ''}
            </td>
            <td className="text-right">{r.applied.formatted}</td>
            <td className="text-right">{r.remaining.formatted}</td>
            <td>
              <Bar providerBp={r.provider_bp} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Bosqichma-bosqich sotib olish (kamayib boruvchi musharaka): jadval va qolgan ulush vizual ko'rsatiladi. */
export function Buyout({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const providers = p.parties.filter((x) => x.capital_total.minor !== '0');
  const [providerId, setProviderId] = useState(
    p.buyout?.provider_party_id ?? providers[0]?.id ?? '',
  );
  const [periods, setPeriods] = useState(String(p.buyout?.periods ?? 6));
  const [pay, setPay] = useState('');
  const plan = useMutation({
    mutationFn: () =>
      unwrap(commands.setBuyoutPlan(p.id, providerId, Number.parseInt(periods, 10) || 0, null)),
    onSuccess: refresh,
  });
  const record = useMutation({
    mutationFn: () => unwrap(commands.recordBuyoutPayment(p.id, pay)),
    onSuccess: async () => {
      setPay('');
      await refresh();
    },
  });
  const b = p.buyout;
  const error = [plan.error, record.error].find((e) => e !== null);
  return (
    <div className="rounded border border-accent/30 p-3" data-testid="buyout">
      <h4 className="font-semibold">{t('partner.buyoutTitle')}</h4>
      <p className="text-xs opacity-70">{t('partner.buyoutHint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-3 text-sm"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          plan.mutate();
        }}
      >
        <label className="block">
          {t('partner.buyoutSeller')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={providerId}
            onChange={(e) => {
              setProviderId(e.target.value);
            }}
          >
            {providers.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          {t('partner.buyoutPeriods')}
          <input
            inputMode="numeric"
            className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
            value={periods}
            onChange={(e) => {
              setPeriods(e.target.value);
            }}
          />
        </label>
        <button type="submit" className="rounded border border-accent px-3 py-1">
          {t('partner.buyoutPlan')}
        </button>
      </form>
      {b && (
        <div className="mt-3 space-y-3">
          <p className="text-sm">
            {t('partner.buyoutSummary', {
              seller: b.provider_name,
              stake: b.stake.formatted,
              total: b.total_value.formatted,
            })}
          </p>
          <Rows rows={b.planned} title={t('partner.planned')} />
          <form
            className="flex flex-wrap items-end gap-2 text-sm"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (pay.trim() !== '') record.mutate();
            }}
          >
            <label className="block">
              {t('partner.buyoutPay')}
              <input
                inputMode="decimal"
                className="mt-1 block w-36 rounded border border-accent/50 bg-transparent p-1"
                value={pay}
                onChange={(e) => {
                  setPay(e.target.value);
                }}
              />
            </label>
            <button type="submit" className="rounded border border-accent px-3 py-1">
              {t('partner.buyoutRecord')}
            </button>
          </form>
          {b.actual.length > 0 && <Rows rows={b.actual} title={t('partner.actual')} />}
          {b.completed && (
            <p role="status" className="font-semibold" data-testid="buyout-done">
              {t('partner.buyoutDone')}
            </p>
          )}
        </div>
      )}
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </div>
  );
}
