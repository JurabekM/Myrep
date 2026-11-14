import type { LocalizedDto } from "../../bindings/bindings";

/** Ilova tili: o'zbekcha (asosiy) yoki ruscha. Noma'lum til — o'zbekcha. */
export function languageOf(language: string): "uz" | "ru" {
  return language.startsWith("ru") ? "ru" : "uz";
}

/** Ko'p tilli matn tanlangan tilda. Ruscha bo'lmasa, backend o'zbekchani qaytargan. */
export function textOf(text: LocalizedDto, language: string): string {
  return languageOf(language) === "ru" ? text.ru : text.uz;
}

/** `YYYY-MM-DD` → `DD.MM.YYYY`. Shakl mos kelmasa, matn o'zgarishsiz qaytadi. */
export function formatIsoDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (match === null) {
    return iso;
  }
  const [, year = "", month = "", day = ""] = match;
  return `${day}.${month}.${year}`;
}
