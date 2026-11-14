import type { ApiError } from "../../bindings/bindings";

/**
 * Buyruq xatosi. `code` — frontend tarjima kaliti shu koddan tanlanadi (`errors.ts`).
 * Xabarda pul summasi yoki PIN bo'lmaydi.
 */
export class CommandError extends Error {
  readonly code: string;
  readonly retryAfterSeconds: number | null;

  constructor(code: string, retryAfterSeconds: number | null = null) {
    super(code);
    this.name = "CommandError";
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** IPC natijasi: bindings `typedError` shu shaklda qaytaradi. */
export type CommandResult<T> = { status: "ok"; data: T } | { status: "error"; error: ApiError };

/** IPC natijasidan qiymatni oladi; xato bo'lsa — `CommandError` (TanStack Query uni `error` sifatida ko'radi). */
export function unwrap<T>(result: CommandResult<T>): T {
  if (result.status === "ok") {
    return result.data;
  }
  const { error } = result;
  switch (error.code) {
    case "LOCKED_OUT":
      throw new CommandError(error.code, error.retryAfterSeconds);
    case "RULE":
      throw new CommandError(error.rule);
    default:
      throw new CommandError(error.code);
  }
}
