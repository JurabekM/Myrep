import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { type AuditDto, type CategoryDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { categoryKey } from "../finance/labels";
import { fetchers, financeKeys, useInvalidateFinance } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";
import { useUiStore } from "../store";

/** Audit ustasi qadamlari: 0 — daromad va majburiyatlar, 1 — xarajatlar, 2 — izohsiz summa, 3 — yakun. */
const STEP_COUNT = 4;

/**
 * O'tgan oy uchun oylik audit ustasi (SPEC 2.3). Har qadam klaviatura bilan bajariladi:
 * birinchi boshqaruv fokusda turadi, Enter — tasdiqlaydi, Esc — bir qadam orqaga qaytaradi.
 */
export function AuditPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const setPage = useUiStore((state) => state.setPage);
  const audit = useQuery({ queryKey: financeKeys.audit, queryFn: fetchers.audit });
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Ochiq oyna (masalan, tez kiritish) bo'lsa, Esc uni yopadi — audit qadami o'zgarmaydi.
      if (
        event.key === "Escape" &&
        step > 0 &&
        document.querySelector('[role="dialog"]') === null
      ) {
        setStep((current) => Math.max(0, current - 1));
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [step]);

  if (audit.isPending) {
    return <p className="text-sm text-muted">{t("common.loading")}</p>;
  }
  if (audit.isError) {
    return <Alert>{t("errors.generic")}</Alert>;
  }
  const data = audit.data;

  /** Yangi holat keshga yoziladi (qayta so'rovsiz ko'rinadi), so'ng hamma moliya keshi yangilanadi. */
  function apply(next: AuditDto) {
    queryClient.setQueryData(financeKeys.audit, next);
    void invalidate();
  }

  async function run(action: () => Promise<AuditDto>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      apply(await action());
      return true;
    } catch (caught) {
      setError(message(caught));
      return false;
    } finally {
      setBusy(false);
    }
  }

  if (data.done) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader title={t("audit.title")} />
        <Card title={t("audit.done.title")}>
          <p className="text-base text-muted">{t("audit.done.text")}</p>
          <div>
            <PrimaryButton
              autoFocus
              onClick={() => {
                setPage("home");
              }}
            >
              {t("audit.done.home")}
            </PrimaryButton>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title={t("audit.title")}
        subtitle={t("audit.period", { start: data.periodStart })}
      />

      <p className="text-sm text-muted">
        {t("audit.stepLabel", { current: step + 1, total: STEP_COUNT })} ·{" "}
        {t(STEP_TITLES[step] ?? "audit.steps.summary")}
      </p>

      {step === 0 ? <SummaryStep data={data} /> : null}
      {step === 1 ? (
        <ExpensesStep
          data={data}
          busy={busy}
          onAdd={(amount, categoryId) =>
            run(() => commands.addAuditExpense(amount, categoryId, null).then(unwrap))
          }
        />
      ) : null}
      {step === 2 ? (
        <UnexplainedStep
          data={data}
          busy={busy}
          onMark={() => run(() => commands.markUnexplainedAsDaily().then(unwrap))}
        />
      ) : null}
      {step === 3 ? (
        <FinishStep
          data={data}
          busy={busy}
          onFinish={() => run(() => commands.finishAudit().then(unwrap))}
        />
      ) : null}

      {error !== null ? <Alert>{error}</Alert> : null}

      <div className="flex justify-between gap-2">
        <SecondaryButton
          disabled={step === 0 || busy}
          onClick={() => {
            setStep((current) => Math.max(0, current - 1));
          }}
        >
          {t("common.back")}
        </SecondaryButton>
        {step < STEP_COUNT - 1 ? (
          <PrimaryButton
            disabled={busy}
            autoFocus={step === 0}
            onClick={() => {
              setStep((current) => Math.min(STEP_COUNT - 1, current + 1));
            }}
          >
            {t("common.next")}
          </PrimaryButton>
        ) : null}
      </div>
    </div>
  );
}

const STEP_TITLES = [
  "audit.steps.summary",
  "audit.steps.expenses",
  "audit.steps.unexplained",
  "audit.steps.finish",
] as const;

/** Pul miqdori musbatmi: minor satr manfiy ishorasiz va nol emas. Faqat taqqoslash — hisob emas. */
function isPositive(money: { minor: string }): boolean {
  return !money.minor.startsWith("-") && money.minor !== "0";
}

function SummaryStep({ data }: { data: AuditDto }) {
  const { t } = useTranslation();
  return (
    <Card>
      <div className="grid gap-6 sm:grid-cols-2">
        <Stat label={t("audit.income")} value={data.income.formatted} />
        <Stat label={t("audit.obligationsTotal")} value={data.obligationsTotal.formatted} />
        <Stat label={t("audit.expensesTotal")} value={data.expenses.formatted} />
        <Stat label={t("audit.netSavings")} value={data.netSavings.formatted} />
      </div>
      {data.lines.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border">
          {data.lines.map((line) => (
            <li key={line.title} className="flex items-center justify-between gap-4 py-2">
              <span className="text-sm text-text">{line.title}</span>
              <span className="text-sm text-muted">
                {line.amount.formatted}
                {isPositive(line.remainder)
                  ? ` · ${t("audit.remainder")}: ${line.remainder.formatted}`
                  : ""}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{t("audit.noObligations")}</p>
      )}
    </Card>
  );
}

function ExpensesStep({
  data,
  busy,
  onAdd,
}: {
  data: AuditDto;
  busy: boolean;
  onAdd: (amount: string, categoryId: string) => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState(data.categories[0]?.id ?? "");
  const label = (category: CategoryDto) => {
    const key = categoryKey(category.systemKey);
    return key !== null ? t(key) : category.name;
  };

  return (
    <Card title={t("audit.expenses.title")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
          event.preventDefault();
          if (amount.trim() === "" || categoryId === "") {
            return;
          }
          void onAdd(amount, categoryId).then((added) => {
            if (added) {
              setAmount("");
            }
          });
        }}
      >
        <Field
          id="audit-expense-amount"
          label={t("audit.expenses.amount")}
          value={amount}
          inputMode="decimal"
          autoComplete="off"
          autoFocus
          onChange={(event) => {
            setAmount(event.target.value);
          }}
        />
        <label className="flex flex-col gap-2 text-sm text-muted">
          {t("audit.expenses.category")}
          <select
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value);
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            {data.categories.map((category) => (
              <option key={category.id} value={category.id}>
                {label(category)}
              </option>
            ))}
          </select>
        </label>
        <div>
          <PrimaryButton type="submit" disabled={busy || amount.trim() === ""}>
            {t("audit.expenses.add")}
          </PrimaryButton>
        </div>
      </form>

      {data.spent.length === 0 ? (
        <p className="text-sm text-muted">{t("audit.expenses.empty")}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {data.spent.map((line) => (
            <li
              key={line.categoryId ?? "none"}
              className="flex items-center justify-between gap-4 py-2"
            >
              <span className="text-sm text-text">
                {line.name ?? t("audit.expenses.uncategorized")}
              </span>
              <span className="text-sm text-muted">{line.amount.formatted}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function UnexplainedStep({
  data,
  busy,
  onMark,
}: {
  data: AuditDto;
  busy: boolean;
  onMark: () => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const positive = isPositive(data.unexplained);
  return (
    <Card title={t("audit.unexplained.title")}>
      <Stat
        label={t("audit.unexplained.amount")}
        value={data.unexplained.formatted}
        hint={t("audit.unexplained.hint")}
      />
      {positive ? (
        <div className="flex flex-col gap-2 sm:flex-row">
          <PrimaryButton autoFocus disabled={busy} onClick={() => void onMark()}>
            {t("audit.unexplained.markDaily")}
          </PrimaryButton>
        </div>
      ) : (
        <p className="text-sm text-muted">{t("audit.unexplained.none")}</p>
      )}
    </Card>
  );
}

function FinishStep({
  data,
  busy,
  onFinish,
}: {
  data: AuditDto;
  busy: boolean;
  onFinish: () => Promise<boolean>;
}) {
  const { t } = useTranslation();
  return (
    <Card title={t("audit.finish.title")}>
      <div className="grid gap-6 sm:grid-cols-2">
        <Stat label={t("audit.income")} value={data.income.formatted} />
        <Stat label={t("audit.expensesTotal")} value={data.expenses.formatted} />
        <Stat label={t("audit.unexplainedLeft")} value={data.unexplained.formatted} />
      </div>
      <p className="text-sm text-muted">{t("audit.finish.text")}</p>
      <div>
        <PrimaryButton autoFocus disabled={busy} onClick={() => void onFinish()}>
          {t("audit.finish.submit")}
        </PrimaryButton>
      </div>
    </Card>
  );
}
