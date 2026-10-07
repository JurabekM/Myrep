import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type CommandError } from '../../bindings';

const PIN_RE = /^\d{6}$/;

function errorKey(e: CommandError): string {
  switch (e.kind) {
    case 'WrongPin':
      return 'lock.errors.wrongPin';
    case 'InvalidPin':
      return 'lock.errors.invalidPin';
    case 'Locked':
      return 'lock.errors.locked';
    case 'KeyringMissing':
      return 'lock.errors.keyringMissing';
    default:
      return 'lock.errors.internal';
  }
}

interface Props {
  /** `true` — birinchi ishga tushirish (PIN o'rnatish). */
  setup: boolean;
  /** Xato PIN'lardan keyingi kutish (soniya); 0 — kiritish mumkin. */
  retryAfterSecs: number;
}

/** PIN faqat Rustga yuboriladi va holatda uzoq saqlanmaydi (yuborilgach tozalanadi). */
export function LockScreen({ setup, retryAfterSecs }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pin, setPin] = useState('');
  const [confirm, setConfirm] = useState('');
  const [mismatch, setMismatch] = useState(false);

  const submit = useMutation({
    mutationFn: async (value: string): Promise<CommandError | null> => {
      const res = setup ? await commands.setupPin(value) : await commands.unlock(value);
      return res.status === 'error' ? res.error : null;
    },
    onSettled: async () => {
      setPin('');
      setConfirm('');
      await queryClient.invalidateQueries({ queryKey: ['vault-state'] });
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (setup && pin !== confirm) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    submit.mutate(pin);
  };

  const error = submit.data;
  const waiting = retryAfterSecs > 0;
  const canSubmit = PIN_RE.test(pin) && (!setup || PIN_RE.test(confirm)) && !waiting;

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-8">
      <h1 className="text-2xl font-semibold">{t('app.title')}</h1>
      <p className="mt-2 text-sm opacity-80">
        {setup ? t('lock.setupHint') : t('lock.unlockHint')}
      </p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <span className="block text-sm">{setup ? t('lock.newPin') : t('lock.pin')}</span>
          <input
            type="password"
            inputMode="numeric"
            autoComplete="off"
            autoFocus
            maxLength={6}
            className="mt-1 w-full rounded border border-accent bg-transparent p-2 text-center tracking-[0.5em]"
            value={pin}
            onChange={(e) => {
              setPin(e.target.value.replace(/\D/g, ''));
            }}
          />
        </label>
        {setup && (
          <label className="block">
            <span className="block text-sm">{t('lock.confirmPin')}</span>
            <input
              type="password"
              inputMode="numeric"
              autoComplete="off"
              maxLength={6}
              className="mt-1 w-full rounded border border-accent bg-transparent p-2 text-center tracking-[0.5em]"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value.replace(/\D/g, ''));
              }}
            />
          </label>
        )}
        <button
          type="submit"
          disabled={!canSubmit || submit.isPending}
          className="w-full rounded bg-accent px-4 py-2 text-paper disabled:opacity-50"
        >
          {setup ? t('lock.setup') : t('lock.unlock')}
        </button>
      </form>
      <div role="alert" className="mt-4 min-h-6 text-sm">
        {mismatch && t('lock.errors.mismatch')}
        {error && !mismatch && !waiting && t(errorKey(error))}
        {waiting && t('lock.errors.wait', { count: retryAfterSecs })}
      </div>
      <footer className="mt-8 text-xs opacity-70">{t('disclaimer')}</footer>
    </main>
  );
}
