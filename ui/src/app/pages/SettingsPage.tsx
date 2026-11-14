import { useTranslation } from "react-i18next";
import { AppInfoCard } from "../components/AppInfoCard";
import { LanguageToggle } from "../components/LanguageToggle";
import { ExchangeCard } from "../settings/ExchangeCard";

/** Sozlamalar: til, maxfiylik va ilova ma'lumoti. */
export function SettingsPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-text">{t("settings.title")}</h1>
      </header>

      <section
        aria-labelledby="language-heading"
        className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-6"
      >
        <div>
          <h2 id="language-heading" className="text-sm font-medium text-text">
            {t("settings.language.title")}
          </h2>
          <p className="mt-1 text-sm text-muted">{t("settings.language.hint")}</p>
        </div>
        <LanguageToggle />
      </section>

      <section
        aria-labelledby="privacy-heading"
        className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-6"
      >
        <h2 id="privacy-heading" className="text-sm font-medium text-text">
          {t("settings.privacy.title")}
        </h2>
        <p className="text-sm text-muted">{t("settings.privacy.text")}</p>
      </section>

      <ExchangeCard />

      <AppInfoCard />
    </div>
  );
}
