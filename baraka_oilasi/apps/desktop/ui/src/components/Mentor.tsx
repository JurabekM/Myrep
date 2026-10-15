import { useTranslation } from "react-i18next";

/** O'ng panel: Sobir hoji maslahati (placeholder) va disklеymer. `tipKey` — i18n kaliti. */
export function Mentor({ tipKey }: { tipKey: string }) {
  const { t } = useTranslation();
  return (
    <aside className="hidden w-72 shrink-0 flex-col gap-4 border-l border-line bg-sidebar p-5 xl:flex">
      <div className="card">
        <p className="mb-2 text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p className="text-sm leading-relaxed">{t(tipKey)}</p>
      </div>
      <p className="mt-auto text-xs text-ink-muted">{t("app.disclaimer")}</p>
    </aside>
  );
}
