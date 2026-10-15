import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ru from "./ru.json";
import uzCyrl from "./uz-Cyrl.json";
import uz from "./uz.json";

// Matnlar `shared/i18n` dan `cargo xtask i18n` orqali generatsiya qilinadi.
export const LOCALES = ["uz", "uz-Cyrl", "ru"] as const;
export type LocaleTag = (typeof LOCALES)[number];

void i18n.use(initReactI18next).init({
  resources: {
    uz: { translation: uz },
    "uz-Cyrl": { translation: uzCyrl },
    ru: { translation: ru },
  },
  lng: "uz",
  fallbackLng: "uz",
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false, prefix: "{", suffix: "}" },
});

export default i18n;
