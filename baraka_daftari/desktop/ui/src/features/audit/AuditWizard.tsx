import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type OverviewDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { WhoseMoney } from './WhoseMoney';

interface Props {
  month: string;
  overview: OverviewDto;
  onClose: () => void;
}

/**
 * Oylik audit ustasi: kategoriyalar bo'yicha bosqichma-bosqich.
 * Faqat klaviatura bilan: `Enter` — saqlab keyingisiga, `Shift+Enter` — orqaga, `Esc` — yopish.
 * Bo'sh qoldirilsa mavjud qiymat o'zgarmaydi; yozuvni olib tashlash uchun `0` kiriting.
 */
export function AuditWizard({ month, overview, onClose }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const categories = overview.categories;
  const [step, setStep] = useState(0);
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const save = useMutation({
    mutationFn: (v: { categoryId: string; amount: string }) =>
      unwrap(commands.auditSetCategory(month, v.categoryId, v.amount)),
  });

  useEffect(() => {
    inputRef.current?.focus();
  }, [step]);

  const current = categories[step];
  const isSummary = current === undefined;

  const advance = async (delta: 1 | -1) => {
    if (delta === 1 && current && value.trim() !== '') {
      await save.mutateAsync({ categoryId: current.category_id, amount: value });
    }
    setValue('');
    if (delta === 1 && step >= categories.length - 1) {
      await queryClient.invalidateQueries({ queryKey: ['audit', month] });
    }
    setStep((s) => Math.max(0, s + delta));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter' && !isSummary) {
      e.preventDefault();
      advance(e.shiftKey ? -1 : 1).catch(() => undefined);
    }
  };

  if (isSummary) {
    return (
      <div onKeyDown={onKeyDown} className="space-y-4">
        <h2 className="text-xl font-semibold">{t('audit.summary')}</h2>
        <p data-testid="unexplained" className="text-lg">
          {t('audit.unexplained', { amount: overview.unexplained.formatted })}
        </p>
        <p className="text-sm opacity-80">{t('audit.unexplainedHint')}</p>
        <WhoseMoney overview={overview} />
        <button
          type="button"
          autoFocus
          className="rounded bg-accent px-4 py-2 text-paper"
          onClick={onClose}
        >
          {t('audit.finish')}
        </button>
      </div>
    );
  }

  return (
    <div onKeyDown={onKeyDown} className="space-y-3">
      <p className="text-sm opacity-70">
        {t('audit.progress', { current: step + 1, total: categories.length })}
      </p>
      <label className="block">
        <span className="block text-xl font-semibold">{current.name}</span>
        <span className="block text-sm opacity-80">
          {t('audit.currentValue', { amount: current.amount.formatted })}
        </span>
        <input
          ref={inputRef}
          inputMode="decimal"
          autoComplete="off"
          className="mt-2 w-full rounded border border-accent bg-transparent p-2 text-xl"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
          }}
        />
      </label>
      <p className="text-xs opacity-70">{t('audit.keys')}</p>
      <div role="alert" className="min-h-6 text-sm">
        {save.error ? errorMessage(t, save.error) : null}
      </div>
    </div>
  );
}
