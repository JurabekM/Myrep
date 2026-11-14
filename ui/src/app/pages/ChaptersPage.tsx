import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChapterCardDto } from "../../bindings/bindings";
import { formatIsoDate, languageOf, textOf } from "../content/format";
import { contentFetchers, contentKeys } from "../content/queries";
import { Alert, PageHeader } from "../finance/ui";
import { ChapterPage } from "./ChapterPage";

/**
 * «Boblar» ekrani: ro'yxat va bitta bobni ochish. Yopiq bob bosilmaydi — ochilish shartini ko'rsatadi.
 * Ochiqlik qoidasi backend'da (odat asosida); bu yerda faqat ko'rsatiladi.
 */
export function ChaptersPage() {
  const { t, i18n } = useTranslation();
  const lang = languageOf(i18n.language);
  const [openId, setOpenId] = useState<string | null>(null);
  const chapters = useQuery({ queryKey: contentKeys.chapters, queryFn: contentFetchers.chapters });

  if (openId !== null) {
    return (
      <ChapterPage
        chapterId={openId}
        onBack={() => {
          setOpenId(null);
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("chapters.title")} subtitle={t("chapters.subtitle")} />

      {chapters.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
      {chapters.isError ? <Alert>{t("errors.generic")}</Alert> : null}

      {chapters.isSuccess ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {chapters.data.map((chapter) => (
            <li key={chapter.id}>
              <ChapterCard
                chapter={chapter}
                lang={lang}
                onOpen={() => {
                  setOpenId(chapter.id);
                }}
              />
            </li>
          ))}
        </ul>
      ) : null}

      <p className="text-sm text-subtle">{t("common.disclaimer")}</p>
    </div>
  );
}

function ChapterCard({
  chapter,
  lang,
  onOpen,
}: {
  chapter: ChapterCardDto;
  lang: "uz" | "ru";
  onOpen: () => void;
}) {
  const { t } = useTranslation();
  const title = textOf(chapter.title, lang);
  const heading = (
    <span className="flex flex-col gap-1">
      <span className="text-xs text-subtle">
        {t("chapters.lawNumber", { number: chapter.order })}
      </span>
      <span className="text-lg font-semibold tracking-tight text-text">{title}</span>
    </span>
  );

  if (chapter.unlocked) {
    return (
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full flex-col gap-4 rounded-xl border border-border bg-surface p-6 text-left transition-colors hover:bg-raised"
      >
        {heading}
        <span className="text-sm font-medium text-accent">{t("chapters.open")}</span>
      </button>
    );
  }

  return (
    <div
      aria-disabled="true"
      className="flex w-full flex-col gap-4 rounded-xl border border-border bg-surface p-6 opacity-80"
    >
      {heading}
      <div className="flex flex-col gap-1 text-sm text-muted">
        <span>{t("chapters.locked")}</span>
        {chapter.tasksRemaining > 0 ? (
          <span>{t("chapters.tasksRemaining", { count: chapter.tasksRemaining })}</span>
        ) : null}
        {chapter.notBefore !== null && chapter.unlockDate === null ? (
          <span>{t("chapters.notBefore", { date: formatIsoDate(chapter.notBefore) })}</span>
        ) : null}
        {chapter.unlockDate !== null ? (
          <span>{t("chapters.unlockOn", { date: formatIsoDate(chapter.unlockDate) })}</span>
        ) : null}
      </div>
    </div>
  );
}
