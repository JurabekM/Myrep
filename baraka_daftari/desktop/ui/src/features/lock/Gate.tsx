import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';

import { commands, type VaultStateDto } from '../../bindings';

import { LockScreen } from './LockScreen';

const ACTIVITY_THROTTLE_MS = 15_000;

async function fetchState(): Promise<VaultStateDto> {
  const res = await commands.vaultState();
  if (res.status === 'error') throw new Error(res.error.kind);
  return res.data;
}

/** Ochiq bo'lmaguncha ilova kontentini ko'rsatmaydi. `Ctrl+L` — qulflash. */
export function Gate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ['vault-state'],
    queryFn: fetchState,
    // Rust avto-qulf qilganini ham ko'rish uchun; qulfda kutish soniyasi ham yangilanadi.
    refetchInterval: 3000,
  });
  const unlocked = data?.kind === 'Unlocked';

  useEffect(() => {
    if (!unlocked) return;
    let last = Date.now();
    const onActivity = () => {
      const now = Date.now();
      if (now - last < ACTIVITY_THROTTLE_MS) return;
      last = now;
      void commands.activity();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'l') {
        e.preventDefault();
        void commands
          .lock()
          .then(() => queryClient.invalidateQueries({ queryKey: ['vault-state'] }));
        return;
      }
      onActivity();
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onActivity);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onActivity);
    };
  }, [unlocked, queryClient]);

  if (!data) return null;
  if (data.kind === 'Unlocked') return <>{children}</>;
  return (
    <LockScreen
      setup={data.kind === 'Uninitialized'}
      retryAfterSecs={data.kind === 'Locked' ? data.retry_after_secs : 0}
    />
  );
}
