import type { SecurityStatus } from "../../bindings/bindings";
import { commands } from "../../bindings/bindings";

/** Xavfsizlik holati uchun kesh kaliti. Qulflash/ochishdan keyin shu kalit qayta yuklanadi. */
export const SECURITY_STATUS_KEY = ["security-status"] as const;

/** Ochiq holatda avto-qulflashni ushlash uchun holat tekshiriladi (millisekund). */
export const STATUS_POLL_MS = 2000;

/** Holatni backend'dan oladi. Xato bo'lsa, TanStack Query uni `isError` sifatida ko'radi. */
export async function fetchSecurityStatus(): Promise<SecurityStatus> {
  const result = await commands.getSecurityStatus();
  if (result.status === "error") {
    throw new Error(result.error.code);
  }
  return result.data;
}
