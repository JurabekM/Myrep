import type { TFunction } from "i18next";

/**
 * Butun son maydoni: faqat raqamlar, ko'pi bilan `maxDigits` ta. Noto'g'ri — 0 (yadro tegishli
 * xatoni qaytaradi: `INVALID_TIME`, `INVALID_WORK_DAYS`). Android `learning_screen.dart` bilan bir xil.
 */
export function parseCount(s: string, maxDigits: number): number {
  const v = s.trim();
  return new RegExp(`^\\d{1,${maxDigits}}$`).test(v) ? Number(v) : 0;
}

/**
 * Soat (≤ 3 raqam) va daqiqa (0–59) maydonlari → butun daqiqa (vaqt, pul emas). Bo'sh maydon — 0;
 * noto'g'ri qiymat — hammasi 0: yadro `INVALID_TIME` qaytaradi.
 */
export function toMinutes(hours: string, minutes: string): number {
  const h = hours.trim();
  const m = minutes.trim();
  if ((h !== "" && !/^\d{1,3}$/.test(h)) || (m !== "" && !/^\d{1,2}$/.test(m))) return 0;
  const mm = m === "" ? 0 : Number(m);
  if (mm > 59) return 0;
  return (h === "" ? 0 : Number(h)) * 60 + mm;
}

/** Daqiqani «2 soat 30 daqiqa» ko'rinishida ko'rsatadi. */
export function showMinutes(t: TFunction, total: number): string {
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h > 0 && m > 0) return t("learn.duration.hm", { h, m });
  if (h > 0) return t("learn.duration.h", { h });
  return t("learn.duration.m", { m });
}
