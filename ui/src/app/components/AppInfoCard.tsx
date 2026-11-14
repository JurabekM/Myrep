import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";

/**
 * «Ilova ma'lumoti» kartasi. Ma'lumot Rust command'idan keladi (get_app_info),
 * frontend hech narsa hisoblamaydi — faqat ko'rsatadi.
 */
export function AppInfoCard() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["app-info"],
    queryFn: () => commands.getAppInfo(),
    staleTime: Number.POSITIVE_INFINITY,
  });

  return (
    <section
      aria-labelledby="app-info-heading"
      className="rounded-xl border border-border bg-surface p-6"
    >
      <h2 id="app-info-heading" className="text-sm font-medium text-muted">
        {t("home.appInfo.title")}
      </h2>

      {query.isPending && <p className="mt-4 text-sm text-subtle">{t("common.loading")}</p>}

      {query.isError && (
        <p role="alert" className="mt-4 text-sm text-text">
          {t("home.appInfo.error")}
        </p>
      )}

      {query.isSuccess && (
        <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-8 gap-y-3 text-sm">
          <dt className="text-subtle">{t("home.appInfo.version")}</dt>
          <dd className="font-medium text-text">{query.data.version}</dd>

          <dt className="text-subtle">{t("home.appInfo.platform")}</dt>
          <dd className="text-text">{`${query.data.platform} · ${query.data.arch}`}</dd>

          <dt className="text-subtle">{t("home.appInfo.build")}</dt>
          <dd className="text-text">
            {query.data.buildProfile === "release"
              ? t("home.appInfo.release")
              : t("home.appInfo.debug")}
          </dd>
        </dl>
      )}
    </section>
  );
}
