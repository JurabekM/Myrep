import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';
import { useCategories, useHome, useMembers } from '../../lib/hooks';

import { ConsentPanel, HavasStatus, ProposeForm, useHavas } from './Havas';

function MembersCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const members = useMembers();
  const [name, setName] = useState('');
  const [role, setRole] = useState('ADULT');
  const [pin, setPin] = useState('');
  const add = useMutation({
    mutationFn: () => unwrap(commands.addMember(name, role, pin === '' ? null : pin)),
    onSuccess: async () => {
      setName('');
      setPin('');
      await queryClient.invalidateQueries();
    },
    onError: () => {
      setPin('');
    },
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('family.members')}</h2>
      <ul className="mt-2 text-sm">
        {members.data?.map((m) => (
          <li key={m.id}>
            {m.name} · {t(`role.${m.role}`)} {m.has_pin ? '🔒' : ''}
          </li>
        ))}
      </ul>
      <form
        className="mt-3 flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <input
          aria-label={t('family.name')}
          placeholder={t('family.name')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
        <select
          aria-label={t('family.role')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={role}
          onChange={(e) => {
            setRole(e.target.value);
          }}
        >
          {['ADULT', 'CHILD', 'VIEWER'].map((r) => (
            <option key={r} value={r}>
              {t(`role.${r}`)}
            </option>
          ))}
        </select>
        <input
          type="password"
          inputMode="numeric"
          maxLength={6}
          aria-label={t('family.pin')}
          placeholder={t('family.pin')}
          className="w-28 rounded border border-accent/50 bg-transparent p-1 text-center"
          value={pin}
          onChange={(e) => {
            setPin(e.target.value.replace(/\D/g, ''));
          }}
        />
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === ''}
        >
          {t('family.add')}
        </button>
      </form>
      <div role="alert" className="min-h-5 text-sm">
        {add.error ? errorMessage(t, add.error) : null}
      </div>
    </section>
  );
}

function TreatsCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const treats = useQuery({ queryKey: ['treats'], queryFn: () => unwrap(commands.listTreats()) });
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [weekday, setWeekday] = useState('5');
  const refresh = () => queryClient.invalidateQueries();
  const add = useMutation({
    mutationFn: () => unwrap(commands.addTreat(name, amount, Number(weekday))),
    onSuccess: async () => {
      setName('');
      setAmount('');
      await refresh();
    },
  });
  const log = useMutation({
    mutationFn: (id: string) => unwrap(commands.logTreat(id)),
    onSuccess: refresh,
  });
  const toggle = useMutation({
    mutationFn: (v: { id: string; active: boolean }) =>
      unwrap(commands.setTreatActive(v.id, v.active)),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => unwrap(commands.removeTreat(id)),
    onSuccess: refresh,
  });
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('treats.title')}</h2>
      <p className="text-sm opacity-80">{t('treats.hint')}</p>
      <ul className="mt-2 space-y-2">
        {treats.data?.map((tr) => (
          <li key={tr.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className={tr.active ? '' : 'opacity-50'}>
              {tr.name} · {tr.amount.formatted} · {t(`weekday.${String(tr.weekday)}`)}
            </span>
            {tr.due_today && !tr.logged_today && tr.active && (
              <button
                type="button"
                className="rounded bg-accent px-2 py-0.5 text-paper"
                onClick={() => {
                  log.mutate(tr.id);
                }}
              >
                {t('treats.logToday')}
              </button>
            )}
            {tr.logged_today && <span>✓ {t('treats.logged')}</span>}
            <button
              type="button"
              className="underline"
              onClick={() => {
                toggle.mutate({ id: tr.id, active: !tr.active });
              }}
            >
              {tr.active ? t('treats.pause') : t('treats.resume')}
            </button>
            <button
              type="button"
              className="underline"
              onClick={() => {
                remove.mutate(tr.id);
              }}
            >
              {t('obl.remove')}
            </button>
          </li>
        ))}
      </ul>
      <form
        className="mt-3 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate();
        }}
      >
        <input
          aria-label={t('treats.name')}
          placeholder={t('treats.name')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
        <input
          aria-label={t('treats.amount')}
          placeholder={t('treats.amount')}
          className="w-32 rounded border border-accent/50 bg-transparent p-1"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
          }}
        />
        <select
          aria-label={t('treats.weekday')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={weekday}
          onChange={(e) => {
            setWeekday(e.target.value);
          }}
        >
          {[1, 2, 3, 4, 5, 6, 7].map((d) => (
            <option key={d} value={String(d)}>
              {t(`weekday.${String(d)}`)}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded border border-accent px-3 py-1"
          disabled={name.trim() === '' || amount.trim() === ''}
        >
          {t('treats.add')}
        </button>
      </form>
      <div role="alert" className="min-h-5 text-sm">
        {[add.error, log.error].map((e) => (e ? errorMessage(t, e) : null))}
      </div>
    </section>
  );
}

function HabitsCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const stats = useQuery({ queryKey: ['habits'], queryFn: () => unwrap(commands.habitStats()) });
  const categories = useCategories();
  const [pick, setPick] = useState('');
  const set = useMutation({
    mutationFn: (v: { id: string; on: boolean }) => unwrap(commands.setHabit(v.id, v.on)),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const habitIds = new Set(stats.data?.map((h) => h.category_id));
  const candidates = categories.data?.filter((c) => !habitIds.has(c.id) && !c.is_charity) ?? [];
  return (
    <section className="rounded-lg border border-accent/30 p-5">
      <h2 className="font-semibold">{t('habits.title')}</h2>
      <p className="text-sm opacity-80">{t('habits.hint')}</p>
      <ul className="mt-2 space-y-1 text-sm">
        {stats.data?.map((h) => (
          <li key={h.category_id} className="flex flex-wrap items-center gap-2">
            <strong>{h.name}</strong>
            <span>
              {t('habits.projection', { month: h.month.formatted, year: h.year.formatted })}
            </span>
            <button
              type="button"
              className="underline"
              onClick={() => {
                set.mutate({ id: h.category_id, on: false });
              }}
            >
              {t('habits.stop')}
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-2 flex gap-2">
        <select
          aria-label={t('habits.pick')}
          className="rounded border border-accent/50 bg-transparent p-1"
          value={pick}
          onChange={(e) => {
            setPick(e.target.value);
          }}
        >
          <option value="">{t('habits.pick')}</option>
          {candidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          disabled={pick === ''}
          onClick={() => {
            set.mutate({ id: pick, on: true });
            setPick('');
          }}
        >
          {t('habits.track')}
        </button>
      </div>
    </section>
  );
}

/** «Oila»: a'zolar, havas chegarasi, juma shirinligi, odatlar va oila kengashi. */
export function FamilyPage() {
  const { t } = useTranslation();
  const setPage = useNav((s) => s.setPage);
  const home = useHome();
  const havas = useHavas(home.data?.month);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('nav.family')}</h1>
        <button
          type="button"
          className="rounded bg-accent px-4 py-2 text-paper"
          onClick={() => {
            setPage('council');
          }}
        >
          {t('council.start')}
        </button>
      </div>
      <section className="space-y-3 rounded-lg border border-accent/30 p-5">
        <h2 className="font-semibold">{t('havas.title')}</h2>
        {havas.data && <HavasStatus report={havas.data} />}
        {havas.data && <ConsentPanel report={havas.data} />}
        <ProposeForm />
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <MembersCard />
        <TreatsCard />
        <HabitsCard />
      </div>
    </div>
  );
}
