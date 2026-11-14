import { useTranslation } from "react-i18next";
import type { TaskDto } from "../../bindings/bindings";
import { languageOf, textOf } from "./format";

/**
 * Haftalik vazifalar ro'yxati. `editable` `false` bo'lsa (bob joriy emas) belgilar faqat ko'rsatiladi.
 * Belgini o'zgartirish backend'da: `onToggle` faqat chaqiradi, holatni o'zi hisoblamaydi.
 */
export function TaskList({
  tasks,
  editable,
  busy,
  onToggle,
}: {
  tasks: readonly TaskDto[];
  editable: boolean;
  busy: boolean;
  onToggle: (task: TaskDto, done: boolean) => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = languageOf(i18n.language);

  return (
    <ul className="flex flex-col gap-2">
      {tasks.map((task) => (
        <li key={task.id}>
          <label className="flex items-start gap-3 rounded-lg border border-border bg-app px-4 py-3">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-accent disabled:opacity-50"
              checked={task.done}
              disabled={!editable || busy}
              onChange={(event) => {
                onToggle(task, event.currentTarget.checked);
              }}
            />
            <span className="flex flex-col gap-1">
              <span className="text-sm text-text">{textOf(task.text, lang)}</span>
              {task.autoCompleted ? (
                <span className="text-xs text-subtle">{t("chapters.taskAuto")}</span>
              ) : null}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
}
