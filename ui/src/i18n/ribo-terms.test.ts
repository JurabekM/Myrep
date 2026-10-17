import { describe, expect, it } from "vitest";
import chapters from "../../../spec/content/chapters.json";
import ru from "./locales/ru/common.json";
import uz from "./locales/uz/common.json";

/**
 * Ribo filtri (DESKTOP_PROMPT 8-bo'lim, MVP_PLAN 7-vazifa): ilovaning hech bir matnida foiz stavkasi
 * «muqobil daromad», «yechim» yoki reklama sifatida ko'rsatilmaydi. Qarz kategoriyasi nomi («Kredit») va
 * ta'limiy taqiq matnlari («Foizli qarz olinmaydi») ruxsat etilgan — ro'yxatda faqat targ'ib iboralari.
 */
const FORBIDDEN_PHRASES: readonly RegExp[] = [
  // o'zbekcha
  /foiz\s+stavka/i,
  /yillik\s+foiz/i,
  /depozit\s+foiz/i,
  /omonat\s+foiz/i,
  /muqobil\s+daromad/i,
  /kredit\s+ol(ing|ish)/i,
  /mikroqarz/i,
  /mikrozaym/i,
  /tez\s+pul/i,
  /onlayn\s+kredit/i,
  // ruscha
  /процентн\w*\s+ставк/i,
  /годовых/i,
  /процент\w*\s+по\s+вклад/i,
  /альтернативн\w+\s+доход/i,
  /возьми\w*\s+кредит/i,
  /оформи\w*\s+кредит/i,
  /микрозайм/i,
  /быстры\w*\s+деньги/i,
  /онлайн[- ]кредит/i,
];

/** Har qanday JSON daraxtidagi barcha satr qiymatlarini yo'li bilan qaytaradi. */
function collectStrings(value: unknown, path = ""): [string, string][] {
  if (typeof value === "string") {
    return [[path, value]];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectStrings(item, `${path}[${String(index)}]`));
  }
  if (value !== null && typeof value === "object") {
    return Object.entries(value).flatMap(([key, child]) =>
      collectStrings(child, path === "" ? key : `${path}.${key}`),
    );
  }
  return [];
}

function violations(source: string, value: unknown): string[] {
  return collectStrings(value)
    .filter(([, text]) => FORBIDDEN_PHRASES.some((pattern) => pattern.test(text)))
    .map(([path, text]) => `${source}:${path} — «${text}»`);
}

describe("ribo filtri: taqiqlangan iboralar", () => {
  it("o'zbekcha tarjimalarda yo'q", () => {
    expect(violations("uz", uz)).toEqual([]);
  });

  it("ruscha tarjimalarda yo'q", () => {
    expect(violations("ru", ru)).toEqual([]);
  });

  it("kontent (boblar, qonunlar, vazifalar) matnlarida yo'q", () => {
    expect(violations("chapters", chapters)).toEqual([]);
  });

  it("filtr haqiqatan ushlaydi (nazorat holati)", () => {
    const bait = { a: "Yillik foiz 24% — muqobil daromad!", b: "Возьмите кредит под 20% годовых" };
    expect(violations("bait", bait)).toHaveLength(2);
  });
});
