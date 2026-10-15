import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { CouncilPage } from "../family/CouncilPage";
import { CsvImportWizard } from "../family/CsvImportWizard";
import { HabitsCard } from "../family/HabitsCard";
import { WeekSheetCard } from "../family/WeekSheetCard";
import { necessityKey } from "../family/necessity";
import { TreatsCard } from "../family/TreatsCard";
import { familyFetchers, familyKeys, useInvalidateFamily } from "../family/queries";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { fetchers, financeKeys } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";

/**
 * «Xarajatlar»: oy xulosasi (uch toifa, sadaqa, sovg'alar), xarajat qo'shish va ro'yxat, Juma shirinligi.
 * Toifa kategoriyadan olinadi (backend). Havas rangi neytral — qizil emas (SPEC 2B.2).
 */
export function ExpensesPage() {
  const { t } = useTranslation();
  const [councilOpen, setCouncilOpen] = useState(false);
  const [csvOpen, setCsvOpen] = useState(false);
  const summary = useQuery({ queryKey: familyKeys.summary, queryFn: familyFetchers.summary });
  const expenses = useQuery({ queryKey: familyKeys.expenses, queryFn: familyFetchers.expenses });
  const categories = useQuery({ queryKey: financeKeys.categories, queryFn: fetchers.categories });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("nav.expenses")} subtitle={t("family.summary")} />

      <div className="flex flex-wrap gap-2">
        <PrimaryButton
          onClick={() => {
            setCouncilOpen(true);
          }}
        >
          {t("family.council")}
        </PrimaryButton>
        <SecondaryButton
          onClick={() => {
            setCsvOpen(true);
          }}
        >
          {t("csv.open")}
        </SecondaryButton>
      </div>

      {summary.isSuccess ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <Stat label={t("family.zarur")} value={summary.data.zarur.formatted} />
          </Card>
          <Card>
            <Stat label={t("family.kerak")} value={summary.data.kerak.formatted} />
          </Card>
          <Card>
            <Stat
              label={t("family.havas")}
              value={summary.data.havas.formatted}
              hint={t("family.havasHint")}
            />
          </Card>
          <Card>
            <Stat
              label={t("family.sadaqa")}
              value={summary.data.sadaqa.formatted}
              hint={t("family.sadaqaHint")}
            />
          </Card>
        </section>
      ) : null}
      {summary.isError ? <Alert>{t("errors.generic")}</Alert> : null}

      <AddExpenseCard categoryNames={categories.isSuccess ? categories.data : []} />

      {summary.isSuccess ? (
        <WeekSheetCard
          weekStart={summary.data.weekStart}
          today={summary.data.today}
          categories={categories.isSuccess ? categories.data : []}
        />
      ) : null}

      <HabitsCard />

      <Card title={t("family.expensesList")}>
        {expenses.isSuccess && expenses.data.length === 0 ? (
          <p className="text-sm text-muted">{t("family.noExpenses")}</p>
        ) : null}
        {expenses.isSuccess && expenses.data.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {expenses.data.map((expense) => (
              <li
                key={expense.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-app px-4 py-3"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-sm text-text">
                    {expense.categoryName ?? t("family.noCategory")}
                  </span>
                  <span className="text-xs text-subtle">
                    {expense.occurredOn}
                    {expense.note !== null ? ` · ${expense.note}` : ""}
                  </span>
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted">
                    {t(necessityKey(expense.necessity))}
                  </span>
                  {expense.isGift ? (
                    <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted">
                      {t("family.flagGift")}
                    </span>
                  ) : null}
                  {expense.isOstentation ? (
                    <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted">
                      {t("family.flagOstentation")}
                    </span>
                  ) : null}
                  {expense.fundedByDebt ? (
                    <span className="rounded-md border border-danger px-2 py-0.5 text-xs text-danger">
                      {t("family.flagDebt")}
                    </span>
                  ) : null}
                  <span className="text-sm text-text">{expense.amount.formatted}</span>
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        {expenses.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      </Card>

      <TreatsCard />

      {csvOpen ? (
        <CsvImportWizard
          onClose={() => {
            setCsvOpen(false);
          }}
        />
      ) : null}

      {councilOpen ? (
        <CouncilPage
          onClose={() => {
            setCouncilOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}

/** Xarajat qo'shish formasi. Toifa kategoriyadan avtomatik olinadi; bayroqlar ixtiyoriy. */
function AddExpenseCard({
  categoryNames,
}: {
  categoryNames: readonly { id: string; name: string }[];
}) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [note, setNote] = useState("");
  const [isGift, setIsGift] = useState(false);
  const [isOstentation, setIsOstentation] = useState(false);
  const [fundedByDebt, setFundedByDebt] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands
        .addExpense({
          amount,
          categoryId: categoryId === "" ? null : categoryId,
          note: note.trim() === "" ? null : note.trim(),
          isGift,
          isOstentation,
          fundedByDebt,
          occurredOn: null,
        })
        .then(unwrap);
      setAmount("");
      setNote("");
      setIsGift(false);
      setIsOstentation(false);
      setFundedByDebt(false);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("family.addExpense")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          void add(event);
        }}
      >
        <Field
          id="expense-amount"
          label={t("family.amount")}
          inputMode="numeric"
          value={amount}
          onChange={(event) => {
            setAmount(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="expense-category" className="text-sm text-muted">
            {t("family.category")}
          </label>
          <select
            id="expense-category"
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.currentTarget.value);
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            <option value="">{t("family.noCategory")}</option>
            {categoryNames.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="expense-note"
          label={t("family.note")}
          value={note}
          onChange={(event) => {
            setNote(event.currentTarget.value);
          }}
        />
        <fieldset className="flex flex-col gap-2 text-sm text-text">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isGift}
              onChange={(event) => {
                setIsGift(event.currentTarget.checked);
              }}
            />
            {t("family.gift")}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isOstentation}
              onChange={(event) => {
                setIsOstentation(event.currentTarget.checked);
              }}
            />
            {t("family.ostentation")}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={fundedByDebt}
              onChange={(event) => {
                setFundedByDebt(event.currentTarget.checked);
              }}
            />
            {t("family.fundedByDebt")}
          </label>
        </fieldset>
        <div>
          <SecondaryButton type="submit" disabled={amount.trim() === ""}>
            {t("family.save")}
          </SecondaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
