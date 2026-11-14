import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import ru from "./locales/ru/common.json";
import uz from "./locales/uz/common.json";

export const SUPPORTED_LANGUAGES = ["uz", "ru"] as const;
export type AppLanguage = (typeof SUPPORTED_LANGUAGES)[number];

/** Asosiy til — o'zbek (lotin). DESKTOP_PROMPT.md 2-bo'lim: i18n uz (asosiy), ru. */
export const DEFAULT_LANGUAGE: AppLanguage = "uz";

const STORAGE_KEY = "baraka.language";

// Tarjima kalitlari tekshiriladi: noto'g'ri kalit yozilsa, TypeScript xato beradi.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: { common: typeof uz };
  }
}

export function isAppLanguage(value: unknown): value is AppLanguage {
  return typeof value === "string" && (SUPPORTED_LANGUAGES as readonly string[]).includes(value);
}

function readStoredLanguage(): AppLanguage {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isAppLanguage(stored) ? stored : DEFAULT_LANGUAGE;
  } catch {
    // localStorage mavjud bo'lmasa (cheklangan muhit) standart tilga qaytiladi.
    return DEFAULT_LANGUAGE;
  }
}

function persistLanguage(language: AppLanguage): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Saqlab bo'lmasa ham til joriy seansda ishlayveradi.
  }
}

void i18next.use(initReactI18next).init({
  resources: { uz: { common: uz }, ru: { common: ru } },
  lng: readStoredLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  defaultNS: "common",
  // Resurslar ichki (sinxron): birinchi render kutmasdan tarjima tayyor bo'lsin.
  initAsync: false,
  react: { useSuspense: false },
  interpolation: { escapeValue: false }, // React o'zi matnni escape qiladi
  returnNull: false,
});

document.documentElement.lang = i18next.language;

i18next.on("languageChanged", (language) => {
  document.documentElement.lang = language;
  if (isAppLanguage(language)) {
    persistLanguage(language);
  }
});

/** Ilova tilini o'zgartiradi. Tanlov keyingi ishga tushirishda ham saqlanadi. */
export async function setAppLanguage(language: AppLanguage): Promise<void> {
  await i18next.changeLanguage(language);
}
