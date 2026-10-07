import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type ExpenseInput } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';
import { useCategories, useHome } from '../../lib/hooks';

interface Row {
  key: number;
  date: string;
  note: string;
  categoryId: string;
  amount: string;
  channel: 'CASH' | 'CARD';
  isGift: boolean;
  isOstentation: boolean;
  fundedByDebt: boolean;
}

/** Hafta kunlari: juma (hafta boshi) dan bugungacha. Sanalarni Rust beradi, bu yerda faqat qo'shiladi. */
function weekDays(weekStart: string, today: string): string[] {
  const out: string[] = [];
  const cursor = new Date(`${weekStart}T00:00:00Z`);
  for (let i = 0; i < 7; i += 1) {
    const iso = cursor.toISOString().slice(0, 10);
    if (iso > today) break;
    out.push(iso);
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return out;
}

let nextKey = 1;
const emptyRow = (date: string): Row => ({
  key: nextKey++,
  date,
  note: '',
  categoryId: '',
  amount: '',
  channel: 'CASH',
  isGift: false,
  isOstentation: false,
  fundedByDebt: false,
});

/**
 * «Hafta varag'i»: bir haftaning barcha xarajatlarini jadvalda ketma-ket kiritish.
 * Klaviatura: `Tab` — keyingi katak, amount katagida `Enter` — yangi qator, `Ctrl+Enter` — hammasini saqlash.
 * Izoh yozilganda kategoriya shu izohli oxirgi xarajatdan avtomatik to'ldiriladi.
 */
export function WeekSheet() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const home = useHome();
  const categories = useCategories();
  const today = home.data?.today ?? '';
  const days = home.data ? weekDays(home.data.week_start, home.data.today) : [];
  const [rows, setRows] = useState<Row[]>([]);
  const tableRef = useRef<HTMLTableElement>(null);

  const list = rows.length > 0 ? rows : today ? [emptyRow(today)] : [];
  const update = (key: number, patch: Partial<Row>) => {
    setRows(list.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  };

  const save = useMutation({
    mutationFn: () => {
      const items: ExpenseInput[] = list
        .filter((r) => r.amount.trim() !== '')
        .map((r) => ({
          date: r.date,
          category_id: r.categoryId,
          amount: r.amount,
          channel: r.channel,
          note: r.note.trim() === '' ? null : r.note,
          necessity: null,
          is_gift: r.isGift,
          is_ostentation: r.isOstentation,
          funded_by_debt: r.fundedByDebt,
        }));
      return unwrap(commands.addExpenses(items));
    },
    onSuccess: async () => {
      setRows([]);
      await queryClient.invalidateQueries();
    },
  });

  const addRow = () => {
    const last = list[list.length - 1];
    setRows([...list, emptyRow(last?.date ?? today)]);
    // Yangi qatorning birinchi katagiga fokus (render'dan keyin).
    setTimeout(() => {
      const inputs = tableRef.current?.querySelectorAll<HTMLInputElement>('input[data-col="note"]');
      inputs?.[inputs.length - 1]?.focus();
    }, 0);
  };

  const onAmountKey = (e: KeyboardEvent<HTMLInputElement>, isLast: boolean) => {
    if (e.key === 'Enter' && !e.ctrlKey) {
      e.preventDefault();
      if (isLast) addRow();
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      save.mutate();
    }
  };

  const autofill = async (row: Row) => {
    if (row.categoryId !== '' || row.note.trim() === '') return;
    const res = await commands.suggestCategory(row.note);
    if (res.status === 'ok' && res.data !== null) update(row.key, { categoryId: res.data });
  };

  const filled = list.filter((r) => r.amount.trim() !== '').length;

  return (
    <section aria-label={t('sheet.title')} onKeyDown={onKeyDown}>
      <h2 className="text-lg font-semibold">{t('sheet.title')}</h2>
      <p className="text-sm opacity-80">{t('sheet.hint')}</p>
      <table ref={tableRef} className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-left opacity-70">
            <th>{t('sheet.date')}</th>
            <th>{t('sheet.note')}</th>
            <th>{t('sheet.category')}</th>
            <th>{t('sheet.amount')}</th>
            <th>{t('sheet.channel')}</th>
            <th>{t('sheet.flags')}</th>
          </tr>
        </thead>
        <tbody>
          {list.map((r, i) => (
            <tr key={r.key} className="align-top">
              <td>
                <select
                  aria-label={t('sheet.date')}
                  className="rounded border border-accent/40 bg-transparent p-1"
                  value={r.date}
                  onChange={(e) => {
                    update(r.key, { date: e.target.value });
                  }}
                >
                  {days.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  data-col="note"
                  aria-label={t('sheet.note')}
                  className="w-full rounded border border-accent/40 bg-transparent p-1"
                  value={r.note}
                  onChange={(e) => {
                    update(r.key, { note: e.target.value });
                  }}
                  onBlur={() => {
                    void autofill(r);
                  }}
                />
              </td>
              <td>
                <select
                  aria-label={t('sheet.category')}
                  className="rounded border border-accent/40 bg-transparent p-1"
                  value={r.categoryId}
                  onChange={(e) => {
                    update(r.key, { categoryId: e.target.value });
                  }}
                >
                  <option value="">—</option>
                  {categories.data?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  aria-label={t('sheet.amount')}
                  inputMode="decimal"
                  className="w-28 rounded border border-accent/40 bg-transparent p-1 text-right"
                  value={r.amount}
                  onChange={(e) => {
                    update(r.key, { amount: e.target.value });
                  }}
                  onKeyDown={(e) => {
                    onAmountKey(e, i === list.length - 1);
                  }}
                />
              </td>
              <td>
                <select
                  aria-label={t('sheet.channel')}
                  className="rounded border border-accent/40 bg-transparent p-1"
                  value={r.channel}
                  onChange={(e) => {
                    update(r.key, { channel: e.target.value as Row['channel'] });
                  }}
                >
                  <option value="CASH">{t('channel.CASH')}</option>
                  <option value="CARD">{t('channel.CARD')}</option>
                </select>
              </td>
              <td className="space-x-2 whitespace-nowrap">
                {(
                  [
                    ['isGift', 'sheet.gift'],
                    ['isOstentation', 'sheet.ostentation'],
                    ['fundedByDebt', 'sheet.debt'],
                  ] as const
                ).map(([field, label]) => (
                  <label key={field} className="inline-flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={r[field]}
                      onChange={(e) => {
                        update(r.key, { [field]: e.target.checked });
                      }}
                    />
                    {t(label)}
                  </label>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-3">
        <button type="button" className="rounded border border-accent px-3 py-1" onClick={addRow}>
          {t('sheet.addRow')}
        </button>
        <button
          type="button"
          className="rounded bg-accent px-4 py-1 text-paper disabled:opacity-50"
          disabled={filled === 0 || save.isPending}
          onClick={() => {
            save.mutate();
          }}
        >
          {t('sheet.save', { count: filled })}
        </button>
        <span className="text-xs opacity-70">Ctrl+Enter</span>
      </div>
      <div role="alert" className="mt-2 min-h-6 text-sm">
        {save.error ? errorMessage(t, save.error) : null}
      </div>
    </section>
  );
}
