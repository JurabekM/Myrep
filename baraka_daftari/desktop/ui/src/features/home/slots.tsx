import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type HomeDto } from '../../bindings';
import { useNav } from '../../app/nav';
import { formatBp, unwrap } from '../../lib/api';

export interface SlotProps {
  home: HomeDto;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="text-sm uppercase tracking-wide opacity-70">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

/** Bosh ekrandagi BIRINCHI raqam: "O'zingizga qancha to'ladingiz?" */
function SelfPaidSlot({ home }: SlotProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const raise = useMutation({
    mutationFn: (bp: number) => unwrap(commands.setRule({ kind: 'PERCENT', value: String(bp) })),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  return (
    <Card title={t('home.selfPaid')}>
      <p className="text-4xl font-semibold" data-testid="self-paid">
        {home.self_paid.formatted}
      </p>
      <p className="mt-1 text-sm opacity-80">
        {t('home.ofIncome', { bp: formatBp(home.self_paid_bp), income: home.income.formatted })}
      </p>
      {home.rate_suggestion_bp !== null && (
        <div className="mt-3 rounded bg-accent/10 p-3 text-sm">
          <p>{t('home.raiseRate', { bp: formatBp(home.rate_suggestion_bp) })}</p>
          <button
            type="button"
            className="mt-2 rounded bg-accent px-3 py-1 text-paper"
            onClick={() => {
              if (home.rate_suggestion_bp !== null) raise.mutate(home.rate_suggestion_bp);
            }}
          >
            {t('home.raiseAccept')}
          </button>
        </div>
      )}
    </Card>
  );
}

function VaultSlot({ home }: SlotProps) {
  const { t } = useTranslation();
  const setPage = useNav((s) => s.setPage);
  return (
    <Card title={t('home.vault')}>
      <p className="text-2xl font-semibold" data-testid="vault-balance">
        {home.vault_balance.formatted}
      </p>
      {home.pending_withdrawals > 0 && (
        <p className="mt-1 text-sm">
          {t('home.pendingWithdrawals', { count: home.pending_withdrawals })}
        </p>
      )}
      <button
        type="button"
        className="mt-2 text-sm underline"
        onClick={() => {
          setPage('vault');
        }}
      >
        {t('home.openVault')}
      </button>
    </Card>
  );
}

function StreakSlot({ home }: SlotProps) {
  const { t } = useTranslation();
  return (
    <Card title={t('home.streak')}>
      <p className="text-2xl font-semibold" data-testid="streak">
        {t('home.weeks', { count: home.streak_weeks })}
      </p>
      <p className="mt-1 text-sm opacity-80">
        {t('home.streakDetails', { best: home.best_streak_weeks, days: home.saved_days })}
      </p>
    </Card>
  );
}

function ResultSlot({ home }: SlotProps) {
  const { t } = useTranslation();
  return (
    <Card title={t('home.monthResult')}>
      <p className="text-2xl font-semibold">{home.month_result.formatted}</p>
    </Card>
  );
}

/** D5 (kontent dvigateli) da to'ldiriladi; slot joyi hozirdan band. */
function PlaceholderSlot({ titleKey, textKey }: { titleKey: string; textKey: string }) {
  const { t } = useTranslation();
  return (
    <Card title={t(titleKey)}>
      <p className="text-sm opacity-70">{t(textKey)}</p>
    </Card>
  );
}

function WeekTasksSlot() {
  return <PlaceholderSlot titleKey="home.weekTasks" textKey="home.comingSoon" />;
}

function FridayChapterSlot() {
  return <PlaceholderSlot titleKey="home.fridayChapter" textKey="home.comingSoon" />;
}

/**
 * Slot arxitekturasi: bosh sahifa shu ro'yxat bo'yicha chiziladi. Keyingi vazifalar (D5: vazifa va
 * bob, D6: havas, ...) yangi slotni shu yerga qo'shadi, sahifaning o'zini o'zgartirmaydi.
 * Tartib muhim: birinchisi — "o'zingizga to'langan".
 */
export const homeSlots: { id: string; Component: ComponentType<SlotProps> }[] = [
  { id: 'self-paid', Component: SelfPaidSlot },
  { id: 'vault', Component: VaultSlot },
  { id: 'streak', Component: StreakSlot },
  { id: 'month-result', Component: ResultSlot },
  { id: 'week-tasks', Component: WeekTasksSlot },
  { id: 'friday-chapter', Component: FridayChapterSlot },
];
