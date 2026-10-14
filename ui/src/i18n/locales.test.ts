import { describe, expect, it } from "vitest";
import { DEFAULT_LANGUAGE } from "./index";
import ru from "./locales/ru/common.json";
import uz from "./locales/uz/common.json";

interface Messages {
  readonly [key: string]: string | Messages;
}

/** Ichma-ich tarjimalarni nuqta bilan tekislaydi: `nav.home` kabi kalit va matn juftlari. */
function flattenMessages(messages: Messages, prefix = ""): [string, string][] {
  const result: [string, string][] = [];
  for (const [key, value] of Object.entries(messages)) {
    const path = prefix === "" ? key : `${prefix}.${key}`;
    if (typeof value === "string") {
      result.push([path, value]);
    } else {
      result.push(...flattenMessages(value, path));
    }
  }
  return result;
}

describe("tarjima fayllari", () => {
  it("uz va ru bir xil kalitlar to'plamiga ega", () => {
    const uzKeys = flattenMessages(uz)
      .map(([key]) => key)
      .sort();
    const ruKeys = flattenMessages(ru)
      .map(([key]) => key)
      .sort();

    expect(ruKeys).toEqual(uzKeys);
  });

  it("hech bir tarjima qiymati bo'sh emas", () => {
    const empty = [...flattenMessages(uz), ...flattenMessages(ru)].filter(
      ([, value]) => value.trim() === "",
    );

    expect(empty).toEqual([]);
  });

  it("asosiy til o'zbekcha (lotin)", () => {
    expect(DEFAULT_LANGUAGE).toBe("uz");
  });

  it("o'zbekcha matnda kirill harflari yo'q (tilning o'z nomi bundan mustasno)", () => {
    const cyrillic = flattenMessages(uz).filter(
      ([key, value]) => key !== "settings.language.ru" && /[Ѐ-ӿ]/.test(value),
    );

    expect(cyrillic).toEqual([]);
  });
});
