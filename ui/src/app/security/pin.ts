/** PIN uzunligi: aniq 6 ta raqam (security crate bilan bir xil). */
export const PIN_LENGTH = 6;

/** Kiritilgan matndan faqat raqamlarni qoldiradi va uzunlikni chegaralaydi. */
export function sanitizePin(value: string): string {
  return value.replace(/\D/g, "").slice(0, PIN_LENGTH);
}

/** PIN to'g'ri formatdami: aniq `PIN_LENGTH` ta raqam. */
export function isValidPin(value: string): boolean {
  return value.length === PIN_LENGTH && /^\d+$/.test(value);
}
