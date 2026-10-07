import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands, type PriceItemDto } from '../../bindings';
import { errorMessage, formatBp, formatMilli, formatSignedBp, unwrap } from '../../lib/api';

function useRefresh() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}

function IndexCard() {
  const { t } = useTranslation();
  const book = useQuery({ queryKey: ['price-book'], queryFn: () => unwrap(commands.priceBook()) });
  const b = book.data;
  if (!b) return null;
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="inflation">
      <h2 className="font-semibold">{t('prices.index')}</h2>
      {b.inflation ? (
        <>
          <p className="mt-2 text-3xl font-semibold" data-testid="index-value">
            {formatSignedBp(b.inflation.index_bp)}
          </p>
          <p className="text-sm opacity-80">
            {t('prices.indexSpan', { days: b.inflation.span_days })}
          </p>
          <ul className="mt-2 space-y-0.5 text-sm">
            {b.inflation.items.map((i) => (
              <li key={i.name}>
                {i.name}: {formatSignedBp(i.change_bp)} ·{' '}
                {t('prices.weight', { w: formatBp(i.weight_bp) })}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-2 text-sm" data-testid="index-empty">
          {t('prices.indexEmpty')}
        </p>
      )}
      <p className="mt-3 text-sm" role="status" data-testid="weekly">
        {b.logged_this_week ? t('prices.loggedThisWeek') : t('prices.remind')}
        {b.streak_weeks > 0 ? ` ${t('prices.streak', { n: b.streak_weeks })}` : ''}
      </p>
    </section>
  );
}

function ItemRow({ it }: { it: PriceItemDto }) {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [price, setPrice] = useState('');
  const [place, setPlace] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const add = useMutation({
    mutationFn: () =>
      unwrap(commands.addPrice(it.id, price, null, place.trim() === '' ? null : place)),
    onSuccess: async () => {
      setPrice('');
      setPlace('');
      await refresh();
    },
  });
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removePriceItem(it.id)),
    onSuccess: refresh,
  });
  const history = useQuery({
    queryKey: ['price-history', it.id, it.points],
    queryFn: () => unwrap(commands.priceHistory(it.id)),
    enabled: showHistory,
  });
  const error = [add.error, remove.error].find((e) => e !== null);
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <strong>
          {it.name} <span className="text-sm font-normal opacity-70">/ {it.unit}</span>
        </strong>
        {it.change_bp !== null && (
          <span data-testid={`change-${it.name}`}>{formatSignedBp(it.change_bp)}</span>
        )}
      </div>
      <p className="text-sm opacity-80">
        {it.first && it.last && it.points >= 2
          ? t('prices.fromTo', {
              from: it.first.price.formatted,
              fromDate: it.first.observed_on,
              to: it.last.price.formatted,
              toDate: it.last.observed_on,
            })
          : it.last
            ? t('prices.onlyOne', { price: it.last.price.formatted, date: it.last.observed_on })
            : t('prices.noPrice')}
      </p>
      <form
        className="mt-2 flex flex-wrap gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (price.trim() !== '') add.mutate();
        }}
      >
        <input
          aria-label={t('prices.priceFor', { name: it.name })}
          placeholder={t('prices.price')}
          className="w-36 rounded border border-accent/50 bg-transparent p-1"
          value={price}
          onChange={(e) => {
            setPrice(e.target.value);
          }}
        />
        <input
          aria-label={t('prices.place')}
          placeholder={t('prices.place')}
          className="w-36 rounded border border-accent/50 bg-transparent p-1"
          value={place}
          onChange={(e) => {
            setPlace(e.target.value);
          }}
        />
        <button type="submit" className="rounded border border-accent px-3 py-0.5">
          {t('prices.log')}
        </button>
        <button
          type="button"
          className="rounded border border-accent/50 px-3 py-0.5"
          onClick={() => {
            setShowHistory((v) => !v);
          }}
        >
          {t('prices.history')}
        </button>
        <button
          type="button"
          className="rounded border border-accent/50 px-3 py-0.5"
          onClick={() => {
            remove.mutate();
          }}
        >
          {t('prices.remove')}
        </button>
      </form>
      {showHistory && (
        <ul className="mt-2 text-sm">
          {history.data?.map((p) => (
            <li key={p.id}>
              {p.observed_on} · {p.price.formatted}
              {p.place ? ` · ${p.place}` : ''}
            </li>
          ))}
        </ul>
      )}
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

function AddItemForm() {
  const { t } = useTranslation();
  const refresh = useRefresh();
  const [name, setName] = useState('');
  const [unit, setUnit] = useState('kg');
  const [weight, setWeight] = useState('10');
  const add = useMutation({
    mutationFn: () => {
      const pct = Number.parseInt(weight, 10);
      return unwrap(commands.addPriceItem(name, unit, Number.isNaN(pct) ? 0 : pct * 100));
    },
    onSuccess: async () => {
      setName('');
      await refresh();
    },
  });
  return (
    <form
      className="mt-3 flex flex-wrap items-end gap-2"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      <label className="block text-sm">
        {t('prices.itemName')}
        <input
          className="mt-1 block w-44 rounded border border-accent/50 bg-transparent p-1"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('prices.unit')}
        <input
          className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
          value={unit}
          onChange={(e) => {
            setUnit(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('prices.weightLabel')}
        <input
          inputMode="numeric"
          className="mt-1 block w-20 rounded border border-accent/50 bg-transparent p-1"
          value={weight}
          onChange={(e) => {
            setWeight(e.target.value);
          }}
        />
      </label>
      <button
        type="submit"
        className="rounded border border-accent px-3 py-1"
        disabled={name.trim() === ''}
      >
        {t('prices.addItem')}
      </button>
      {add.error ? (
        <p role="alert" className="w-full text-sm">
          {errorMessage(t, add.error)}
        </p>
      ) : null}
    </form>
  );
}

/** «Sichqon kemirgani»: yotgan jamg'arma kelajakda nimaga teng bo'ladi. Qo'rqitmaydi, tushuntiradi. */
function PurchasingCard({ items }: { items: PriceItemDto[] }) {
  const { t } = useTranslation();
  const setPage = useNav((s) => s.setPage);
  const [percent, setPercent] = useState('');
  const [years, setYears] = useState('3');
  const [itemId, setItemId] = useState('');
  const calc = useMutation({
    mutationFn: () =>
      unwrap(
        commands.purchasingPower(
          percent,
          Number.parseInt(years, 10) || 0,
          itemId === '' ? null : itemId,
        ),
      ),
  });
  const r = calc.data;
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid="mouse">
      <h2 className="font-semibold">{t('mouse.title')}</h2>
      <p className="mt-1 text-sm opacity-80">{t('mouse.hint')}</p>
      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          calc.mutate();
        }}
      >
        <label className="block text-sm">
          {t('mouse.percent')}
          <input
            inputMode="decimal"
            className="mt-1 block w-24 rounded border border-accent/50 bg-transparent p-1"
            value={percent}
            onChange={(e) => {
              setPercent(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('mouse.years')}
          <input
            inputMode="numeric"
            className="mt-1 block w-16 rounded border border-accent/50 bg-transparent p-1"
            value={years}
            onChange={(e) => {
              setYears(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('mouse.item')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={itemId}
            onChange={(e) => {
              setItemId(e.target.value);
            }}
          >
            <option value="">{t('mouse.noItem')}</option>
            {items
              .filter((i) => i.last !== null)
              .map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={percent.trim() === ''}
        >
          {t('mouse.calc')}
        </button>
      </form>
      {calc.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, calc.error)}
        </p>
      ) : null}
      {r && (
        <div className="mt-3 space-y-1" data-testid="mouse-result">
          <p>{t('mouse.nominal', { amount: r.nominal.formatted })}</p>
          <p className="font-semibold">
            {t('mouse.real', { years: r.years, amount: r.real.formatted })}
          </p>
          {r.example && (
            <p>
              {t('mouse.example', {
                years: r.years,
                now: formatMilli(r.example.quantity_now_milli),
                later: formatMilli(r.example.quantity_future_milli),
                name: r.example.name,
                unit: r.example.unit,
              })}
            </p>
          )}
        </div>
      )}
      <div className="mt-4 border-t border-accent/20 pt-3">
        <p className="text-sm">{t('mouse.next')}</p>
        <button
          type="button"
          className="mt-2 rounded bg-accent px-3 py-1 text-paper"
          onClick={() => {
            setPage('vault');
          }}
        >
          {t('mouse.toVault')}
        </button>
      </div>
    </section>
  );
}

export function PricesPage() {
  const { t } = useTranslation();
  const items = useQuery({
    queryKey: ['price-items'],
    queryFn: () => unwrap(commands.listPriceItems()),
  });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('nav.prices')}</h1>
      <p className="text-sm opacity-80">{t('prices.intro')}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <IndexCard />
        <PurchasingCard items={items.data ?? []} />
      </div>
      <section className="rounded-lg border border-accent/30 p-5">
        <h2 className="font-semibold">{t('prices.basket')}</h2>
        <AddItemForm />
        <ul className="mt-3 divide-y divide-accent/20">
          {items.data?.map((it) => (
            <ItemRow key={it.id} it={it} />
          ))}
        </ul>
        {items.data?.length === 0 && <p className="mt-3 opacity-70">{t('prices.empty')}</p>}
      </section>
    </div>
  );
}
