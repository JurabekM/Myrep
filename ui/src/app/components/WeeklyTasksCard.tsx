import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { type TaskDto, commands } from "../../bindings/bindings";
import { formatIsoDate, languageOf, textOf } from "../content/format";
import { TaskList } from "../content/TaskList";
import { contentFetchers, contentKeys, useInvalidateContent } from "../content/queries";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, SecondaryButton } from "../finance/ui";
import { useUiStore } from "../store";

/** Bosh sahifa: joriy bobning shu haftalik vazifalari. Belgilash bobning o'zida ham ishlaydi. */
export function WeeklyTasksCard() {
  const { t, i18n } = useTranslation();
  const lang = languageOf(i18n.language);
  const setPage = useUiStore((state) => state.setPage);
  const invalidate = useInvalidateContent();
  const message = useErrorMessage();
  const weekly = useQuery({ queryKey: contentKeys.weekly, queryFn: contentFetchers.weekly });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <Card title={t("chapters.weekCardTitle")}>
      {weekly.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
      {weekly.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {weekly.isSuccess && weekly.data === null ? (
        <p className="text-sm text-muted">{t("chapters.weekCardEmpty")}</p>
      ) : null}
      {weekly.isSuccess && weekly.data !== null ? (
        <>
          <p className="text-sm text-muted">
            {textOf(weekly.data.chapterTitle, lang)} ·{" "}
            {t("chapters.weekStart", { date: formatIsoDate(weekly.data.weekStart) })}
          </p>
          <TaskList
            tasks={weekly.data.tasks}
            editable
            busy={busy}
            onToggle={(task, done) => {
              void toggle(task, done);
            }}
          />
        </>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
      <div>
        <SecondaryButton
          onClick={() => {
            setPage("chapters");
          }}
        >
          {t("chapters.weekCardAll")}
        </SecondaryButton>
      </div>
    </Card>
  );
}
