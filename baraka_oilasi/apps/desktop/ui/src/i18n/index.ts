import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { loadPrefs, savePrefs } from "../lib/prefs";
import ru from "./ru.json";
import uzCyrl from "./uz-Cyrl.json";
import uz from "./uz.json";

// Matnlar `shared/i18n` dan `cargo xtask i18n` orqali generatsiya qilinadi.
export const LOCALES = ["uz", "uz-Cyrl", "ru"] as const;
export type LocaleTag = (typeof LOCALES)[number];

const isLocale = (l: string | null): l is LocaleTag => LOCALES.includes(l as LocaleTag);
const stored = loadPrefs().locale;

void i18n.use(initReactI18next).init({
  resources: {
    uz: { translation: uz },
    "uz-Cyrl": { translation: uzCyrl },
    ru: { translation: ru },
  },
  // Shu qurilmada oxirgi tanlangan til (qulf ekranida ham); bazadagi sozlama ochilgandan keyin keladi.
  lng: isLocale(stored) ? stored : "uz",
  fallbackLng: "uz",
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false, prefix: "{", suffix: "}" },
});

document.documentElement.lang = i18n.language;
i18n.on("languageChanged", (l) => {
  document.documentElement.lang = l;
  if (isLocale(l)) savePrefs({ locale: l });
});

export default i18n;
