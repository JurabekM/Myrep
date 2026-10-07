import * as Dialog from '@radix-ui/react-dialog';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';
import { useDebounced } from '../../lib/useDebounced';

const SOURCES = ['DAILY_WORK', 'ORDER', 'SALARY', 'OTHER'] as const;
const CHANNELS = ['CASH', 'CARD'] as const;
/** Ixtiyoriy «ter / mol / tavakkal» testi; `RIBO` — foizli daromad, alohida ko'rsatiladi. */
const SOURCE_TYPES = ['TER', 'MOL', 'TAVAKKAL', 'RIBO'] as const;

/**
 * Tez kiritish (`Ctrl+N`): summa → Enter. Ilova darhol "shundan X so'm — kelajagingiz uchun"
 * deb ulushni taklif qiladi; Enter shu taklifni qabul qiladi. Summa matni Rustda parse qilinadi.
 */
export function QuickEntry() {
  const { t } = useTranslation();
  const { quickEntryOpen, closeQuickEntry } = useNav();
  return (
    <Dialog.Root
      open={quickEntryOpen}
      onOpenChange={(open) => {
        if (!open) closeQuickEntry();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-24 w-full max-w-md -translate-x-1/2 rounded-lg bg-paper p-6 shadow-xl">
          <Dialog.Title className="text-lg font-semibold">{t('quick.title')}</Dialog.Title>
          <Dialog.Description className="sr-only">{t('quick.description')}</Dialog.Description>
          <QuickEntryForm onDone={closeQuickEntry} />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function QuickEntryForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState('');
  const [source, setSource] = useState<(typeof SOURCES)[number]>('DAILY_WORK');
  const [channel, setChannel] = useState<(typeof CHANNELS)[number]>('CASH');
  const [sourceType, setSourceType] = useState('');
  const [shareText, setShareText] = useState<string | null>(null);

  const debounced = useDebounced(amount.trim());
  const suggestion = useQuery({
    queryKey: ['suggest', debounced],
    queryFn: () => unwrap(commands.suggestShare(debounced)),
    enabled: debounced !== '',
    retry: false,
  });

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        commands.recordIncome({
          amount,
          source,
          channel,
          share: shareText,
          source_type: sourceType === '' ? null : sourceType,
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      onDone();
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (amount.trim() !== '') save.mutate();
  };

  return (
    <form className="mt-4 space-y-4" onSubmit={onSubmit}>
      <label className="block">
        <span className="block text-sm">{t('quick.amount')}</span>
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

      <p className="min-h-6 text-sm" aria-live="polite" data-testid="share-suggestion">
        {suggestion.data && shareText === null
          ? t('quick.suggestion', { share: suggestion.data.share.formatted })
          : null}
      </p>

      <div className="flex gap-4">
        <label className="flex-1">
          <span className="block text-sm">{t('quick.source')}</span>
          <select
            className="mt-1 w-full rounded border border-accent bg-transparent p-2"
            value={source}
            onChange={(e) => {
              setSource(e.target.value as (typeof SOURCES)[number]);
            }}
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {t(`source.${s}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex-1">
          <span className="block text-sm">{t('quick.channel')}</span>
          <select
            className="mt-1 w-full rounded border border-accent bg-transparent p-2"
            value={channel}
            onChange={(e) => {
              setChannel(e.target.value as (typeof CHANNELS)[number]);
            }}
          >
            {CHANNELS.map((c) => (
              <option key={c} value={c}>
                {t(`channel.${c}`)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block">
        <span className="block text-sm">{t('incomeType.label')}</span>
        <select
          className="mt-1 w-full rounded border border-accent bg-transparent p-2"
          value={sourceType}
          onChange={(e) => {
            setSourceType(e.target.value);
          }}
        >
          <option value="">{t('incomeType.none')}</option>
          {SOURCE_TYPES.map((s) => (
            <option key={s} value={s}>
              {t(`incomeType.${s}`)}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="block text-sm">{t('quick.shareOverride')}</span>
        <input
          inputMode="decimal"
          autoComplete="off"
          placeholder={suggestion.data?.share.formatted ?? ''}
          className="mt-1 w-full rounded border border-accent/50 bg-transparent p-2"
          value={shareText ?? ''}
          onChange={(e) => {
            setShareText(e.target.value === '' ? null : e.target.value);
          }}
        />
      </label>

      <div role="alert" className="min-h-6 text-sm">
        {save.error ? errorMessage(t, save.error) : null}
      </div>
      <button
        type="submit"
        disabled={amount.trim() === '' || save.isPending}
        className="w-full rounded bg-accent px-4 py-2 text-paper disabled:opacity-50"
      >
        {t('quick.save')}
      </button>
    </form>
  );
}
