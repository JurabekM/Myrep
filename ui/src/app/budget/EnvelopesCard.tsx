import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type BudgetDto, type EnvelopeDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { fetchers, financeKeys } from "../finance/queries";
import { Alert, Card, Field, PrimaryButton, SecondaryButton } from "../finance/ui";
import { useApplyBudget } from "./queries";

/**
 * Haftalik konvertlar: shu haftaning qoldig'ini «Qutqarilgan pul» ga yozish (hafta uchun bir marta)
 * va yangi konvert qo'shish. Sarflangan summa — bog'langan kategoriya bo'yicha (backend).
 */
export function EnvelopesCard({ envelopes }: { envelopes: EnvelopeDto[] }) {
  const { t } = useTranslation();
  const apply = useApplyBudget();
  const message = useErrorMessage();
  const categories = useQuery({ queryKey: financeKeys.categories, queryFn: fetchers.categories });
  const [name, setName] = useState("");
  const [weeklyLimit, setWeeklyLimit] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<BudgetDto>, onDone?: () => void) {
    setError(null);
    try {
      await apply(await action());
      onDone?.();
    } catch (caught) {
      setError(message(caught));
    }
  }

  function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(
      () =>
        commands
          .addEnvelope({
            name,
            weeklyLimit,
            categoryId: category === "" ? null : category,
          })
          .then(unwrap),
      () => {
        setName("");
        setWeeklyLimit("");
        setCategory("");
      },
    );
  }

  return (
    <Card title={t("budget.envelopesTitle")}>
      {envelopes.length === 0 ? (
        <p className="text-sm text-muted">{t("budget.envelopeEmpty")}</p>
      ) : null}
      {envelopes.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {envelopes.map((env) => {
            const nothingLeft = env.leftoverThisWeek.minor === "0";
            return (
              <li
                key={env.id}
                className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-sm text-text">{env.name}</span>
                  <span className="text-xs text-subtle">
                    {t("budget.weeklyLimit")}: {env.weeklyLimit.formatted} ·{" "}
                    {t("budget.spentThisWeek")}: {env.spentThisWeek.formatted} ·{" "}
                    {t("budget.leftoverThisWeek")}: {env.leftoverThisWeek.formatted}
                  </span>
                </span>
                <span>
                  <SecondaryButton
                    disabled={env.closedThisWeek || nothingLeft}
                    onClick={() => {
                      void run(() => commands.closeEnvelopeWeek(env.id).then(unwrap));
                    }}
                  >
                    {env.closedThisWeek ? t("budget.weekClosed") : t("budget.closeWeek")}
                  </SecondaryButton>
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}

      <form className="flex flex-col gap-4" onSubmit={add}>
        <Field
          id="env-name"
          label={t("budget.name")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id="env-limit"
          label={t("budget.weeklyLimit")}
          inputMode="numeric"
          value={weeklyLimit}
          onChange={(event) => {
            setWeeklyLimit(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="env-category" className="text-sm text-muted">
            {t("budget.category")}
          </label>
          <select
            id="env-category"
            value={category}
            onChange={(event) => {
              setCategory(event.currentTarget.value);
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            <option value="">{t("budget.noCategory")}</option>
            {(categories.isSuccess ? categories.data : []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <PrimaryButton type="submit" disabled={name.trim() === "" || weeklyLimit.trim() === ""}>
            {t("budget.addEnvelope")}
          </PrimaryButton>
        </div>
      </form>

      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
