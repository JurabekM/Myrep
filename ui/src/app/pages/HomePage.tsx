import { useTranslation } from "react-i18next";
import { AppInfoCard } from "../components/AppInfoCard";

/** Bosh sahifa. Keyingi vazifalarda (D4, D5) bu yerga kartalar qo'shiladi. */
export function HomePage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-text">{t("home.greeting")}</h1>
        <p className="max-w-prose text-base text-muted">{t("home.subtitle")}</p>
      </header>

      <AppInfoCard />
    </div>
  );
}
