import type { TFunction } from 'i18next';

import type { CommandError } from '../bindings';

type Result<T> = { status: 'ok'; data: T } | { status: 'error'; error: CommandError };

export class ApiError extends Error {
  constructor(public readonly error: CommandError) {
    super(error.kind);
  }
}

/** Rust commandlari natijasini ochadi; xatoda `ApiError` tashlaydi (TanStack Query ushlaydi). */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  const res = await call;
  if (res.status === 'error') throw new ApiError(res.error);
  return res.data;
}

/** Foydalanuvchiga ko'rsatiladigan xato matni. Server `Invalid.message` allaqachon o'zbekcha. */
export function errorMessage(t: TFunction, e: unknown): string {
  if (!(e instanceof ApiError)) return t('errors.Internal');
  const err = e.error;
  switch (err.kind) {
    case 'Invalid':
      return err.message;
    case 'Cooling':
      return t('errors.Cooling', { count: err.remaining_secs });
    case 'Locked':
      return t('errors.Locked', { count: err.retry_after_secs });
    default:
      return t(`errors.${err.kind}`);
  }
}

/** Bazis punktni ko'rsatish (500 → "5%", 550 → "5,5%"). Pul emas, faqat matn. */
export function formatBp(bp: number): string {
  const whole = Math.trunc(bp / 100);
  const frac = bp % 100;
  if (frac === 0) return `${String(whole)}%`;
  return `${String(whole)},${frac.toString().padStart(2, '0').replace(/0+$/, '')}%`;
}
