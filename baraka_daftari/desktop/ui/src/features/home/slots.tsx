import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type HomeDto } from '../../bindings';
import { useNav } from '../../app/nav';
import { formatBp, unwrap } from '../../lib/api';
import { DebtSummary } from '../debts/DebtSummary';
import { RescuePanel } from '../rescue/RescuePanel';

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

function useJourney() {
  return useQuery({ queryKey: ['journey'], queryFn: () => unwrap(commands.journey()) });
}

/** Shu haftaning 3 ta vazifasi (joriy bob). */
function WeekTasksSlot() {
  const { t } = useTranslation();
  const openChapter = useNav((s) => s.openChapter);
  const { data } = useJourney();
  return (
    <Card title={t('home.weekTasks')}>
      {data && (
        <>
          <p className="text-sm opacity-80" data-testid="week-progress">
            {t('home.tasksProgress', { done: data.week_done, total: data.week_tasks.length })}
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {data.week_tasks.map((task) => (
              <li key={task.id} className={task.done ? 'line-through opacity-60' : ''}>
                {task.done ? '✓ ' : '○ '}
                {task.title}
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-2 text-sm underline"
            onClick={() => {
              openChapter(data.current_id);
            }}
          >
            {t('home.openTasks')}
          </button>
        </>
      )}
    </Card>
  );
}

/** Juma qissasi: har juma yangi bob ochilishi mumkin. */
function FridayChapterSlot() {
  const { t } = useTranslation();
  const openChapter = useNav((s) => s.openChapter);
  const { data } = useJourney();
  return (
    <Card title={t('home.fridayChapter')}>
      {data && (
        <>
          {data.opened_this_week && (
            <p className="mb-1 text-sm font-semibold" data-testid="new-chapter">
              {t('home.newChapter')}
            </p>
          )}
          <p className="text-lg font-semibold">{data.current_title}</p>
          <button
            type="button"
            className="mt-2 rounded bg-accent px-3 py-1 text-paper"
            onClick={() => {
              openChapter(data.current_id);
            }}
          >
            {t('home.readChapter')}
          </button>
        </>
      )}
    </Card>
  );
}

/** Juma hisoboti: «Bu hafta qancha qutqardingiz?» (D7). */
function RescueSlot() {
  const { t } = useTranslation();
  return (
    <Card title={t('home.rescue')}>
      <RescuePanel />
    </Card>
  );
}

/**
 * Slot arxitekturasi: bosh sahifa shu ro'yxat bo'yicha chiziladi. Keyingi vazifalar (D5: vazifa va
 * bob, D6: havas, ...) yangi slotni shu yerga qo'shadi, sahifaning o'zini o'zgartirmaydi.
 * Tartib muhim: birinchisi — "o'zingizga to'langan".
 */
/** Qarz ekrani byudjet va jamg'armadan ustun turadi (SPEC 2C.7): faol qarz bo'lsa bosh sahifada «o'zingizga to'ladingiz»dan keyin darhol (birinchi raqam o'zgarmaydi). */
function DebtSlot() {
  return <DebtSummary />;
}

export const homeSlots: { id: string; Component: ComponentType<SlotProps> }[] = [
  { id: 'self-paid', Component: SelfPaidSlot },
  { id: 'debts', Component: DebtSlot },
  { id: 'vault', Component: VaultSlot },
  { id: 'streak', Component: StreakSlot },
  { id: 'month-result', Component: ResultSlot },
  { id: 'rescue', Component: RescueSlot },
  { id: 'week-tasks', Component: WeekTasksSlot },
  { id: 'friday-chapter', Component: FridayChapterSlot },
];
