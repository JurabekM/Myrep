import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type MoneyDto } from '../bindings';

/** Frontend pul hisoblamaydi: summa string sifatida Rustga yuboriladi va tayyor `formatted` qaytadi. */
export function App() {
  const { t } = useTranslation();
  const [total, setTotal] = useState('100');

  const split = useMutation({
    mutationFn: async (): Promise<MoneyDto[]> => {
      const res = await commands.allocateDemo(total, [70, 20, 10]);
      if (res.status === 'error') throw new Error(res.error.message);
      return res.data;
    },
  });

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-semibold">{t('app.title')}</h1>
      <h2 className="mt-6 text-lg">{t('demo.heading')}</h2>
      <label className="mt-4 block">
        <span className="block text-sm">{t('demo.total')}</span>
        <input
          className="mt-1 w-full rounded border border-accent bg-transparent p-2"
          inputMode="numeric"
          value={total}
          onChange={(e) => {
            setTotal(e.target.value);
          }}
        />
      </label>
      <button
        type="button"
        className="mt-4 rounded bg-accent px-4 py-2 text-paper"
        onClick={() => {
          split.mutate();
        }}
      >
        {t('demo.run')}
      </button>
      {split.data && (
        <ul aria-label={t('demo.result')} className="mt-4 list-disc pl-6">
          {split.data.map((m, i) => (
            <li key={i}>{m.formatted}</li>
          ))}
        </ul>
      )}
      {split.error && (
        <p role="alert" className="mt-4">
          {t('demo.error')}: {split.error.message}
        </p>
      )}
      <footer className="mt-10 text-xs opacity-70">{t('disclaimer')}</footer>
    </main>
  );
}
