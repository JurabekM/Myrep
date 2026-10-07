import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

/**
 * Tray / `Ctrl+Alt+B` tez xarajat oynasi (mobildagi vidjetga muqobil).
 *
 * Xavfsizlik: daftar qulfli bo'lsa bu oyna **hech qanday summa yoki ma'lumot so'ramaydi va ko'rsatmaydi** —
 * faqat holat so'raladi (`vaultState`); boshqa so'rovlar `enabled: false`.
 */
export function QuickExpenseWindow() {
  const { t } = useTranslation();
  const state = useQuery({
    queryKey: ['vault-state'],
    queryFn: () => unwrap(commands.vaultState()),
    refetchInterval: 2000,
  });
  const unlocked = state.data?.kind === 'Unlocked';

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') void commands.hideQuickWindow();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  if (!state.data) return null;
  if (!unlocked) {
    return (
      <main className="p-6" data-testid="quick-locked">
        <h1 className="text-lg font-semibold">{t('quickWindow.title')}</h1>
        <p className="mt-3" role="status">
          {t('quickWindow.locked')}
        </p>
      </main>
    );
  }
  return <UnlockedForm />;
}

function UnlockedForm() {
  const { t } = useTranslation();
  const home = useQuery({ queryKey: ['home'], queryFn: () => unwrap(commands.homeSummary()) });
  const categories = useQuery({
    queryKey: ['categories'],
    queryFn: () => unwrap(commands.listCategories()),
  });
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const chosen = categoryId || categories.data?.[0]?.id || '';

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        commands.addExpenses([
          {
            date: home.data?.today ?? '',
            category_id: chosen,
            amount,
            channel: 'CASH',
            note: note.trim() === '' ? null : note,
            necessity: null,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
          },
        ]),
      ),
    onSuccess: async () => {
      setAmount('');
      setNote('');
      await commands.hideQuickWindow();
    },
  });

  const autofill = async () => {
    if (note.trim() === '' || categoryId !== '') return;
    const res = await commands.suggestCategory(note);
    if (res.status === 'ok' && res.data !== null) setCategoryId(res.data);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (amount.trim() !== '' && chosen !== '') save.mutate();
  };

  return (
    <main className="p-6">
      <h1 className="text-lg font-semibold">{t('quickWindow.title')}</h1>
      <form className="mt-3 space-y-3" onSubmit={onSubmit}>
        <label className="block">
          <span className="block text-sm">{t('sheet.amount')}</span>
          <input
            autoFocus
            inputMode="decimal"
            autoComplete="off"
            className="mt-1 w-full rounded border border-accent bg-transparent p-2 text-xl"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
            }}
          />
        </label>
        <label className="block">
          <span className="block text-sm">{t('sheet.note')}</span>
          <input
            className="mt-1 w-full rounded border border-accent/50 bg-transparent p-2"
            value={note}
            onChange={(e) => {
              setNote(e.target.value);
            }}
            onBlur={() => {
              void autofill();
            }}
          />
        </label>
        <label className="block">
          <span className="block text-sm">{t('sheet.category')}</span>
          <select
            className="mt-1 w-full rounded border border-accent/50 bg-transparent p-2"
            value={chosen}
            onChange={(e) => {
              setCategoryId(e.target.value);
            }}
          >
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <div role="alert" className="min-h-5 text-sm">
          {save.error ? errorMessage(t, save.error) : null}
        </div>
        <button
          type="submit"
          className="w-full rounded bg-accent px-4 py-2 text-paper disabled:opacity-50"
          disabled={amount.trim() === '' || save.isPending}
        >
          {t('quick.save')}
        </button>
      </form>
    </main>
  );
}
