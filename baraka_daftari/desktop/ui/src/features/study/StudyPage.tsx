import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands, type JourneyDto, type PolicyDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { ChapterView } from './ChapterView';

function UnlockInfo({ journey }: { journey: JourneyDto }) {
  const { t } = useTranslation();
  const u = journey.unlock;
  if (u === null) return <p className="text-sm">{t('study.lastChapter')}</p>;
  if (u.unlocked) return <p className="text-sm">{t('study.unlockedSoon')}</p>;
  return (
    <p className="text-sm" data-testid="unlock-info">
      {u.weeks_in_window === 0
        ? t('study.unlockFirstWeek')
        : t('study.unlockProgress', { done: u.satisfied_weeks, needed: u.needed_weeks })}
    </p>
  );
}

function PolicyForm({ policy }: { policy: PolicyDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [window, setWindow] = useState(String(policy.window_weeks));
  const [weeks, setWeeks] = useState(String(policy.min_satisfied_weeks));
  const [tasks, setTasks] = useState(String(policy.min_tasks_per_week));
  const save = useMutation({
    mutationFn: () =>
      unwrap(
        commands.setUnlockPolicy({
          window_weeks: Number(window),
          min_satisfied_weeks: Number(weeks),
          min_tasks_per_week: Number(tasks),
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const field = (label: string, value: string, set: (v: string) => void, max: number) => (
    <label className="block">
      <span className="block text-sm">{label}</span>
      <input
        type="number"
        min={0}
        max={max}
        className="mt-1 w-24 rounded border border-accent/50 bg-transparent p-1"
        value={value}
        onChange={(e) => {
          set(e.target.value);
        }}
      />
    </label>
  );
  return (
    <details className="rounded border border-accent/30 p-3">
      <summary className="cursor-pointer text-sm">{t('study.policy')}</summary>
      <p className="mt-2 text-sm opacity-80">{t('study.policyHint')}</p>
      <form
        className="mt-2 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        {field(t('study.policyWindow'), window, setWindow, 6)}
        {field(t('study.policyWeeks'), weeks, setWeeks, 6)}
        {field(t('study.policyTasks'), tasks, setTasks, 3)}
        <button type="submit" className="rounded border border-accent px-3 py-1">
          {t('study.policySave')}
        </button>
      </form>
      {save.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, save.error)}
        </p>
      ) : null}
    </details>
  );
}

/** «Boblar»: ochilgan boblar ro'yxati, o'qish va ochilish sharti. */
export function StudyPage() {
  const { t } = useTranslation();
  const { chapterId } = useNav();
  const [picked, setPicked] = useState<string | null>(null);
  const journey = useQuery({ queryKey: ['journey'], queryFn: () => unwrap(commands.journey()) });
  if (journey.error) return <p role="alert">{errorMessage(t, journey.error)}</p>;
  if (!journey.data) return null;
  const j = journey.data;
  const selected = picked ?? chapterId ?? j.current_id;

  return (
    <div className="flex gap-8">
      <aside className="w-72 shrink-0 space-y-4">
        <h1 className="text-2xl font-semibold">{t('nav.study')}</h1>
        <ol className="space-y-1">
          {j.chapters.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                disabled={!c.opened}
                aria-current={c.id === selected ? 'true' : undefined}
                className={`w-full rounded px-3 py-2 text-left disabled:opacity-50 ${c.id === selected ? 'bg-accent text-paper' : 'hover:bg-accent/10'}`}
                onClick={() => {
                  setPicked(c.id);
                }}
              >
                <span className="block text-xs opacity-70">
                  {c.opened ? t('study.law', { n: c.law }) : t('study.locked')}
                </span>
                {c.title}
              </button>
            </li>
          ))}
        </ol>
        <UnlockInfo journey={j} />
        <PolicyForm key={JSON.stringify(j.policy)} policy={j.policy} />
      </aside>
      <div className="min-w-0 flex-1">
        <ChapterView key={selected} id={selected} />
      </div>
    </div>
  );
}
