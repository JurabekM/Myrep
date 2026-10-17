import { describe, expect, it } from "vitest";
import { formatIsoDate, languageOf, textOf } from "./format";

describe("kontent formatlari", () => {
  it("sana: YYYY-MM-DD → DD.MM.YYYY; noto'g'ri shakl o'zgarmaydi", () => {
    expect(formatIsoDate("2026-10-21")).toBe("21.10.2026");
    expect(formatIsoDate("21.10.2026")).toBe("21.10.2026");
    expect(formatIsoDate("bugun")).toBe("bugun");
  });

  it("til: ru-RU ruscha, boshqasi o'zbekcha", () => {
    expect(languageOf("ru-RU")).toBe("ru");
    expect(languageOf("uz")).toBe("uz");
    expect(languageOf("en")).toBe("uz");
  });

  it("matn: tanlangan til, ruscha bo'lmasa o'zbekcha", () => {
    const text = { uz: "Salom", ru: "Привет" };
    expect(textOf(text, "ru")).toBe("Привет");
    expect(textOf(text, "uz")).toBe("Salom");
    expect(textOf({ uz: "Salom", ru: "Salom" }, "ru")).toBe("Salom");
  });
});
