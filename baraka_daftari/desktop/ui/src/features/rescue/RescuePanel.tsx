import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

export function useRescue() {
  return useQuery({ queryKey: ['rescue'], queryFn: () => unwrap(commands.rescueReport()) });
}

/**
 * Juma hisoboti: «Bu hafta qancha qutqardingiz?». Faqat havas hisobga kiradi; sadaqa va zarur xarajatni
 * kamaytirish «yutuq» emas. Manfiy holat ko'rsatilmaydi (0). Va'da yo'q.
 */
export function RescuePanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const rescue = useRescue();
  const transfer = useMutation({
    mutationFn: () => unwrap(commands.transferAllRescue()),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const r = rescue.data;
  if (!r) return null;
  const hasAvailable = r.available.minor !== '0';
  return (
    <div className="space-y-2">
      <p className="text-3xl font-semibold" data-testid="rescued">
        {r.rescued.formatted}
      </p>
      <p className="text-sm opacity-80">
        {t('rescue.compare', {
          week: r.week,
          before: r.baseline.formatted,
          now: r.current.formatted,
        })}
      </p>
      <p>{t('rescue.available', { amount: r.available.formatted })}</p>
      <button
        type="button"
        className="rounded bg-accent px-4 py-2 text-paper disabled:opacity-50"
        disabled={!hasAvailable || transfer.isPending}
        onClick={() => {
          transfer.mutate();
        }}
      >
        {t('rescue.transfer')}
      </button>
      <div role="alert" className="min-h-5 text-sm">
        {transfer.error ? errorMessage(t, transfer.error) : null}
      </div>
    </div>
  );
}
