import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type ChapterDto,
  type ContentBlockDto,
  type TaskDto,
  commands,
} from "../../bindings/bindings";
import { formatIsoDate, languageOf, textOf } from "../content/format";
import { TaskList } from "../content/TaskList";
import { contentFetchers, contentKeys, useInvalidateContent } from "../content/queries";
import { CommandError, unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, PageHeader, PrimaryButton, SecondaryButton } from "../finance/ui";

/** «Daftar sahifasi»ning eng ko'p belgisi (backend bilan bir xil: DAFTAR_BODY_MAX_CHARS). */
const DAFTAR_MAX_CHARS = 5000;

/**
 * Bob sahifasi: qissa bloklari, qonun, haftalik vazifalar va «Daftar sahifasi».
 * Tasdiqlanmagan diniy blok release'da backend'dan kelmaydi; kelsa ham belgisi bilan ko'rsatiladi.
 */
export function ChapterPage({ chapterId, onBack }: { chapterId: string; onBack: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = languageOf(i18n.language);
  const invalidate = useInvalidateContent();
  const message = useErrorMessage();
  const chapter = useQuery({
    queryKey: contentKeys.chapter(chapterId),
    queryFn: () => contentFetchers.chapter(chapterId),
    retry: false,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Tahrirlanayotgan matn; `null` — saqlangan matn ko'rsatiladi. */
  const [draft, setDraft] = useState<string | null>(null);

  const locked = chapter.error instanceof CommandError && chapter.error.code === "CHAPTER_LOCKED";

  async function toggle(task: TaskDto, done: boolean) {
    setBusy(true);
    setError(null);
    try {
      await commands.setTaskDone(task.id, done).then(unwrap);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy(false);
    }
  }

  async function save(event: SyntheticEvent<HTMLFormElement>, body: string) {
    event.preventDefault();
    if (busy || body.trim() === "") {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await commands.saveDaftarPage(chapterId, body).then(unwrap);
      setDraft(null);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy(false);
    }
  }

  const back = (
    <div>
      <SecondaryButton onClick={onBack}>{t("chapters.back")}</SecondaryButton>
    </div>
  );

  if (locked) {
    return (
      <div className="flex flex-col gap-8">
        {back}
        <PageHeader title={t("chapters.lockedTitle")} subtitle={t("chapters.lockedText")} />
      </div>
    );
  }

  if (chapter.isError) {
    return (
      <div className="flex flex-col gap-8">
        {back}
        <Alert>{message(chapter.error)}</Alert>
      </div>
    );
  }

  if (chapter.isPending) {
    return (
      <div className="flex flex-col gap-8">
        {back}
        <p className="text-sm text-muted">{t("common.loading")}</p>
      </div>
    );
  }

  const data: ChapterDto = chapter.data;
  const body = draft ?? data.daftarPage?.body ?? "";

  return (
    <div className="flex flex-col gap-8">
      {back}
      <PageHeader
        title={textOf(data.title, lang)}
        subtitle={data.isCurrent ? t("chapters.current") : undefined}
      />

      <Card>
        {data.blocks.map((block, index) => (
          <BlockView key={index} block={block} lang={lang} />
        ))}
      </Card>

      <Card title={t("chapters.law")}>
        <p className="text-sm text-muted">{t("chapters.lawNumber", { number: data.law.number })}</p>
        <p className="text-base leading-relaxed text-text">{textOf(data.law.text, lang)}</p>
      </Card>

      <Card title={t("chapters.tasks")}>
        {data.isCurrent ? null : (
          <p className="text-sm text-muted">{t("chapters.tasksReadOnly")}</p>
        )}
        <TaskList
          tasks={data.weeklyTasks}
          editable={data.isCurrent}
          busy={busy}
          onToggle={(task, done) => {
            void toggle(task, done);
          }}
        />
      </Card>

      <Card title={t("chapters.daftarTitle")}>
        <p className="text-sm text-muted">{t("chapters.daftarHint")}</p>
        {data.daftarPage !== null ? (
          <p className="text-xs text-subtle">
            {t("chapters.daftarUpdated", { date: formatIsoDate(data.daftarPage.updatedOn) })}
          </p>
        ) : null}
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            void save(event, body);
          }}
        >
          <label htmlFor="daftar-body" className="sr-only">
            {t("chapters.daftarTitle")}
          </label>
          <textarea
            id="daftar-body"
            rows={6}
            maxLength={DAFTAR_MAX_CHARS}
            value={body}
            placeholder={t("chapters.daftarPlaceholder")}
            onChange={(event) => {
              setDraft(event.currentTarget.value);
            }}
            className="rounded-lg border border-border bg-app p-3 text-text outline-none transition-colors focus:border-accent"
          />
          <div>
            <PrimaryButton type="submit" disabled={busy || body.trim() === ""}>
              {t("chapters.daftarSave")}
            </PrimaryButton>
          </div>
        </form>
      </Card>

      {error !== null ? <Alert>{error}</Alert> : null}
      <p className="text-sm text-subtle">{t("common.disclaimer")}</p>
    </div>
  );
}

function BlockView({ block, lang }: { block: ContentBlockDto; lang: "uz" | "ru" }) {
  const { t } = useTranslation();
  switch (block.type) {
    case "paragraph":
      return <p className="text-base leading-relaxed text-text">{textOf(block.text, lang)}</p>;
    case "quote":
      return (
        <blockquote className="border-l-2 border-accent pl-4 text-base italic text-muted">
          {textOf(block.text, lang)}
        </blockquote>
      );
    case "religious":
      return (
        <figure className="flex flex-col gap-2 rounded-lg border border-border bg-raised p-4">
          <p className="text-base leading-relaxed text-text">{textOf(block.text, lang)}</p>
          <figcaption className="text-sm text-muted">
            {t("chapters.source")}: {textOf(block.source, lang)}
          </figcaption>
          {block.approved ? null : (
            <p className="text-xs text-danger">{t("chapters.reviewPending")}</p>
          )}
        </figure>
      );
  }
}
