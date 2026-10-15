import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { CommandError } from "./command-error";

/**
 * Xato kodi → tarjima kaliti. Backend (`ApiError`, domen `DomainError`) kodlari shu yerda matnga aylanadi.
 * Noma'lum kod — umumiy xabar; xato matnida summa yoki PIN bo'lmaydi.
 */

export const RULE_ERROR_KEYS = {
  REASON_REQUIRED: "errors.reasonRequired",
  AMOUNT_NOT_POSITIVE: "errors.amountNotPositive",
  INSUFFICIENT_BALANCE: "errors.insufficientBalance",
  INITIAL_ALREADY_SET: "errors.initialAlreadySet",
  INCOME_ALREADY_SHARED: "errors.incomeAlreadyShared",
  SHARE_EXCEEDS_INCOME: "errors.shareExceedsIncome",
  INVALID_RULE: "errors.invalidRule",
  DEBT_OVERPAID: "errors.debtOverpaid",
  AUDIT_ALREADY_DONE: "errors.auditAlreadyDone",
  NOTHING_TO_MARK: "errors.nothingToMark",
  NOT_FOUND: "errors.notFound",
  INVALID_DAY: "errors.invalidDay",
  CHAPTER_LOCKED: "errors.chapterLocked",
  TASK_NOT_CURRENT: "errors.taskNotCurrent",
  BODY_REQUIRED: "errors.bodyRequired",
  BODY_TOO_LONG: "errors.bodyTooLong",
  NECESSITY_UNCHANGED: "errors.necessityUnchanged",
  PIN_NOT_SET: "errors.pinNotSet",
  INVALID_ROLE: "errors.invalidRole",
  PARSE_ERROR: "errors.parseError",
  CURRENCY_MISMATCH: "errors.currencyMismatch",
  RESCUE_EXCEEDS_AVAILABLE: "errors.rescueExceedsAvailable",
  ENVELOPE_WEEK_CLOSED: "errors.envelopeWeekClosed",
  SUBSCRIPTION_CANCELLED: "errors.subscriptionCancelled",
} as const;

/** Xato uchun tarjima kaliti. Ko'rsatiladigan matn `t()` orqali olinadi. */
export function errorKey(
  code: string,
): (typeof RULE_ERROR_KEYS)[keyof typeof RULE_ERROR_KEYS] | "errors.generic" {
  return code in RULE_ERROR_KEYS
    ? RULE_ERROR_KEYS[code as keyof typeof RULE_ERROR_KEYS]
    : "errors.generic";
}

/** Tarjima kaliti sifatida ishlatiladigan xato kaliti. */
export type FinanceErrorKey = ReturnType<typeof errorKey>;

/**
 * Xatodan ko'rsatiladigan matn. PIN xatolari (`WRONG_PIN`, `LOCKED_OUT`) va domen kodlari shu yerda hal bo'ladi.
 * Komponent ichida chaqiriladi: `const message = useErrorMessage();`.
 */
export function useErrorMessage(): (caught: unknown) => string {
  const { t } = useTranslation();
  return useCallback(
    (caught: unknown) => {
      if (!(caught instanceof CommandError)) {
        return t("errors.generic");
      }
      if (caught.code === "WRONG_PIN") {
        return t("security.wrongPin");
      }
      if (caught.code === "INVALID_PIN") {
        return t("security.invalidPin");
      }
      if (caught.code === "LOCKED_OUT") {
        return t("security.lockedOut", { seconds: caught.retryAfterSeconds ?? 0 });
      }
      return t(errorKey(caught.code));
    },
    [t],
  );
}
