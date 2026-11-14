import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CategoryDto } from "../../bindings/bindings";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, PrimaryButton, SecondaryButton } from "../finance/ui";
import { useInvalidateFamily } from "./queries";

interface Row {
  key: number;
  date: string;
  categoryId: string;
  amount: string;
  note: string;
}

/** Hafta varag'i: shu haftaning xarajatlarini bir jadvalda, ketma-ket kiritish (DESKTOP_PROMPT 7). */
export function WeekSheetCard({
  weekStart,
  today,
  categories,
}: {
  weekStart: string;
  today: string;
  categories: readonly CategoryDto[];
}) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const [rows, setRows] = useState<Row[]>([
    { key: 1, date: today, categoryId: "", amount: "", note: "" },
  ]);
  const [nextKey, setNextKey] = useState(2);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function update(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    const filled = rows.filter((row) => row.amount.trim() !== "");
    if (filled.length === 0) {
      setError(t("family.weekEmpty"));
      return;
    }
    try {
      const saved = await commands
        .addExpenses(
          filled.map((row) => ({
            amount: row.amount,
            categoryId: row.categoryId === "" ? null : row.categoryId,
            note: row.note.trim() === "" ? null : row.note.trim(),
            isGift: false,
            isOstentation: false,
            fundedByDebt: false,
            occurredOn: row.date,
          })),
        )
        .then(unwrap);
      setStatus(t("family.weekSaved", { count: saved.length }));
      setRows([{ key: nextKey, date: today, categoryId: "", amount: "", note: "" }]);
      setNextKey(nextKey + 1);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("family.weekSheet")}>
      <p className="text-sm text-muted">{t("family.weekSheetHint")}</p>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          void save(event);
        }}
      >
        {rows.map((row) => (
          <div
            key={row.key}
            className="grid gap-2 sm:grid-cols-[auto_1fr_1fr_1fr_auto] sm:items-end"
          >
            <label className="flex flex-col gap-1 text-xs text-muted">
              {t("family.weekDate")}
              <input
                type="date"
                min={weekStart}
                max={today}
                value={row.date}
                onChange={(event) => {
                  update(row.key, { date: event.currentTarget.value });
                }}
                className="h-10 rounded-lg border border-border bg-app px-2 text-text outline-none focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted">
              {t("family.category")}
              <select
                value={row.categoryId}
                onChange={(event) => {
                  update(row.key, { categoryId: event.currentTarget.value });
                }}
                className="h-10 rounded-lg border border-border bg-app px-2 text-text outline-none focus:border-accent"
              >
                <option value="">{t("family.noCategory")}</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted">
              {t("family.amount")}
              <input
                inputMode="numeric"
                value={row.amount}
                onChange={(event) => {
                  update(row.key, { amount: event.currentTarget.value });
                }}
                className="h-10 rounded-lg border border-border bg-app px-2 text-text outline-none focus:border-accent"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted">
              {t("family.note")}
              <input
                value={row.note}
                onChange={(event) => {
                  update(row.key, { note: event.currentTarget.value });
                }}
                className="h-10 rounded-lg border border-border bg-app px-2 text-text outline-none focus:border-accent"
              />
            </label>
            <SecondaryButton
              disabled={rows.length === 1}
              onClick={() => {
                setRows((current) => current.filter((item) => item.key !== row.key));
              }}
            >
              {t("family.weekRemoveRow")}
            </SecondaryButton>
          </div>
        ))}
        <div className="flex flex-wrap gap-2">
          <SecondaryButton
            onClick={() => {
              setRows((current) => [
                ...current,
                { key: nextKey, date: today, categoryId: "", amount: "", note: "" },
              ]);
              setNextKey(nextKey + 1);
            }}
          >
            {t("family.weekAddRow")}
          </SecondaryButton>
          <PrimaryButton type="submit">{t("family.weekSave")}</PrimaryButton>
        </div>
      </form>
      {status !== null ? <p className="text-sm text-muted">{status}</p> : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
