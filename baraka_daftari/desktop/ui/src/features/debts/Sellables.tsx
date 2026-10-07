import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type SellableDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

function Row({ item }: { item: SellableDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const debts = useQuery({ queryKey: ['debts'], queryFn: () => unwrap(commands.listDebts()) });
  const [price, setPrice] = useState('');
  const [debtId, setDebtId] = useState('');
  const sell = useMutation({
    mutationFn: () => unwrap(commands.sellItem(item.id, price, debtId === '' ? null : debtId)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeSellable(item.id)),
    onSuccess: refresh,
  });
  const error = [sell.error, remove.error].find((e) => e !== null);
  return (
    <li className="py-2" data-testid={`sell-${item.name}`}>
      <div className="flex flex-wrap justify-between gap-2">
        <strong>{item.name}</strong>
        <span>
          {item.sold && item.sold_amount
            ? t('sell.soldFor', { amount: item.sold_amount.formatted })
            : item.estimated_price.formatted}
        </span>
      </div>
      {item.unused_since && (
        <p className="text-xs opacity-70">{t('sell.unusedSince', { date: item.unused_since })}</p>
      )}
      {!item.sold && (
        <form
          className="mt-1 flex flex-wrap items-end gap-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (price.trim() !== '') sell.mutate();
          }}
        >
          <input
            aria-label={t('sell.soldPrice', { name: item.name })}
            placeholder={t('sell.soldPlaceholder')}
            className="w-32 rounded border border-accent/50 bg-transparent p-1"
            value={price}
            onChange={(e) => {
              setPrice(e.target.value);
            }}
          />
          <select
            aria-label={t('sell.toDebt', { name: item.name })}
            className="rounded border border-accent/50 bg-transparent p-1"
            value={debtId}
            onChange={(e) => {
              setDebtId(e.target.value);
            }}
          >
            <option value="">{t('sell.noDebt')}</option>
            {debts.data
              ?.filter((d) => d.active)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.creditor}
                </option>
              ))}
          </select>
          <button type="submit" className="rounded border border-accent px-3 py-0.5">
            {t('sell.sold')}
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
      )}
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

/** «Sotiladigan buyumlar»: sotilgan buyum tushumi bir bosishda qarzga qo'shimcha to'lov bo'ladi. */
export function Sellables() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['sellables'],
    queryFn: () => unwrap(commands.listSellables()),
  });
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [since, setSince] = useState('');
  const add = useMutation({
    mutationFn: () => unwrap(commands.addSellable(name, price, since === '' ? null : since)),
    onSuccess: async () => {
      setName('');
      setPrice('');
      setSince('');
      await queryClient.invalidateQueries();
    },
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="sellables">
      <h2 className="font-semibold">{t('sell.title')}</h2>
      <p className="text-sm opacity-80">{t('sell.hint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <label className="block text-sm">
          {t('sell.name')}
          <input
            className="mt-1 block w-40 rounded border border-accent/50 bg-transparent p-1"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('sell.price')}
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
          {t('sell.since')}
          <input
            type="date"
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={since}
            onChange={(e) => {
              setSince(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === '' || price.trim() === ''}
        >
          {t('sell.add')}
        </button>
      </form>
      {add.error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, add.error)}
        </p>
      ) : null}
      <ul className="mt-2 divide-y divide-accent/20">
        {list.data?.map((i) => (
          <Row key={i.id} item={i} />
        ))}
      </ul>
    </section>
  );
}
