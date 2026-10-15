import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton } from "../finance/ui";
import { familyFetchers, familyKeys, useInvalidateFamily } from "./queries";

/** Odatlar: faqat statistika — oyiga va yiliga qancha sarflangani. Ayblov va uyaltirish yo'q (SPEC 2B.9). */
export function HabitsCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const habits = useQuery({ queryKey: familyKeys.habits, queryFn: familyFetchers.habits });
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.addHabit(name).then(unwrap);
      setName("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("family.habitsTitle")}>
      <p className="text-sm text-muted">{t("family.habitsHint")}</p>
      {habits.isSuccess && habits.data.length === 0 ? (
        <p className="text-sm text-muted">{t("family.habitEmpty")}</p>
      ) : null}
      {habits.isSuccess && habits.data.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {habits.data.map((habit) => (
            <li
              key={habit.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-app px-4 py-3"
            >
              <span className="text-sm text-text">{habit.name}</span>
              <span className="flex flex-wrap gap-4 text-sm text-muted">
                <span>
                  {t("family.habitMonthly")}: {habit.monthly.formatted}
                </span>
                <span>
                  {t("family.habitYearly")}: {habit.yearly.formatted}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          void add(event);
        }}
      >
        <Field
          id="habit-name"
          label={t("family.habitName")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <div>
          <PrimaryButton type="submit" disabled={name.trim() === ""}>
            {t("family.habitAdd")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
