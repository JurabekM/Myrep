import * as ToggleGroup from "@radix-ui/react-toggle-group";
import { useTranslation } from "react-i18next";
import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  isAppLanguage,
  setAppLanguage,
  type AppLanguage,
} from "../../i18n";

interface LanguageToggleProps {
  /** Ixcham rejim: yon panel uchun qisqa kodlar (UZ / RU). */
  compact?: boolean;
}

/** Til tanlagich. Bosilganda ilova tili darhol almashadi. */
export function LanguageToggle({ compact = false }: LanguageToggleProps) {
  const { t, i18n } = useTranslation();
  const current: AppLanguage = isAppLanguage(i18n.language) ? i18n.language : DEFAULT_LANGUAGE;

  return (
    <ToggleGroup.Root
      type="single"
      value={current}
      onValueChange={(value) => {
        if (isAppLanguage(value)) {
          void setAppLanguage(value);
        }
      }}
      aria-label={t("settings.language.title")}
      className={
        compact
          ? "grid grid-cols-2 gap-1 rounded-lg bg-app p-1"
          : "inline-flex gap-1 rounded-lg bg-app p-1"
      }
    >
      {SUPPORTED_LANGUAGES.map((language) => {
        const fullName = t(`settings.language.${language}`);
        return (
          <ToggleGroup.Item
            key={language}
            value={language}
            aria-label={compact ? language.toUpperCase() : fullName}
            title={fullName}
            className="h-8 rounded-md px-3 text-xs font-medium text-muted uppercase transition-colors hover:text-text data-[state=on]:bg-raised data-[state=on]:text-text"
          >
            {compact ? language : fullName}
          </ToggleGroup.Item>
        );
      })}
    </ToggleGroup.Root>
  );
}
