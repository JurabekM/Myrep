import type { AppError } from "../bindings";

type CoreResult<T> = { status: "ok"; data: T } | { status: "error"; error: AppError };

/** Yadro xatosi: barqaror `code` va ixtiyoriy `field`. */
export class CoreError extends Error {
  readonly code: string;
  readonly field: string | null;

  constructor(error: AppError) {
    super(error.code);
    this.code = error.code;
    this.field = error.field;
  }
}

/** tauri-specta natijasini ochadi: xato bo'lsa `CoreError` tashlaydi. */
export async function call<T>(result: Promise<CoreResult<T>>): Promise<T> {
  const r = await result;
  if (r.status === "ok") return r.data;
  throw new CoreError(r.error);
}

/** Xato uchun i18n kaliti (`error.<CODE>`, topilmasa — umumiy xabar). */
export function errorKey(error: unknown, exists: (key: string) => boolean): string {
  if (error instanceof CoreError) {
    const key = `error.${error.code}`;
    if (exists(key)) return key;
  }
  return "error.GENERIC";
}
