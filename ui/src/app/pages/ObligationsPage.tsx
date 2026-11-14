import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type DebtDto,
  type ObligationDto,
  type ObligationInputDto,
  commands,
} from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { OBLIGATION_KIND_KEYS, obligationKindKey } from "../finance/labels";
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

type ObligationKind = ObligationInputDto["kind"];
const KINDS = Object.keys(OBLIGATION_KIND_KEYS) as ObligationKind[];

/** Doimiy to'lovlar (ijara, kredit, kommunal, telefon, benzin) va nasiya daftari (do'kon qarzlari). */
export function ObligationsPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("obligations.title")} subtitle={t("obligations.subtitle")} />
      <ObligationsSection />
      <DebtsSection />
    </div>
  );
}

function ObligationsSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const list = useQuery({ queryKey: financeKeys.obligations, queryFn: fetchers.obligations });
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<ObligationKind>("RENT");
  const [amount, setAmount] = useState("");
  const [dueDay, setDueDay] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const next = unwrap(
        await commands.addObligation({
          title,
          kind,
          amount,
          dueDay: dueDay.trim() === "" ? null : Number(dueDay),
        }),
      );
      queryClient.setQueryData(financeKeys.obligations, next);
      setTitle("");
      setAmount("");
      setDueDay("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function deactivate(item: ObligationDto) {
    setError(null);
    try {
      const next = unwrap(await commands.setObligationActive(item.id, false));
      queryClient.setQueryData(financeKeys.obligations, next);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("obligations.list.title")}>
      {list.isPending ? <p className="text-sm text-muted">{t("common.loading")}</p> : null}
      {list.data?.length === 0 ? (
        <p className="text-sm text-muted">{t("obligations.list.empty")}</p>
      ) : null}
      {list.data !== undefined && list.data.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border">
          {list.data.map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-4 py-3">
              <span className="flex min-w-0 flex-col">
                <span className="truncate text-base text-text">{item.title}</span>
                <span className="text-xs text-subtle">
                  {t(obligationKindKey(item.kind))}
                  {item.dueDay !== null
                    ? ` · ${t("obligations.list.dueDay", { day: item.dueDay })}`
                    : ""}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-3">
                <span className="text-base font-medium text-text">{item.amount.formatted}</span>
                <SecondaryButton
                  onClick={() => {
                    void deactivate(item);
                  }}
                >
                  {t("obligations.list.deactivate")}
                </SecondaryButton>
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      <form
        className="flex flex-col gap-4 border-t border-border pt-4"
        onSubmit={(event) => void add(event)}
      >
        <h3 className="text-sm font-medium text-text">{t("obligations.add.title")}</h3>
        <Field
          id="obligation-title"
          label={t("obligations.add.name")}
          value={title}
          autoComplete="off"
          onChange={(event) => {
            setTitle(event.target.value);
          }}
        />
        <label className="flex flex-col gap-2 text-sm text-muted">
          {t("obligations.add.kind")}
          <select
            value={kind}
            onChange={(event) => {
              setKind(event.target.value as ObligationKind);
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            {KINDS.map((code) => (
              <option key={code} value={code}>
                {t(obligationKindKey(code))}
              </option>
            ))}
          </select>
        </label>
        <Field
          id="obligation-amount"
          label={t("obligations.add.amount")}
          value={amount}
          inputMode="decimal"
          autoComplete="off"
          onChange={(event) => {
            setAmount(event.target.value);
          }}
        />
        <Field
          id="obligation-due"
          label={t("obligations.add.dueDay")}
          value={dueDay}
          inputMode="numeric"
          autoComplete="off"
          onChange={(event) => {
            setDueDay(event.target.value);
          }}
        />
        {error !== null ? <Alert>{error}</Alert> : null}
        <div>
          <PrimaryButton type="submit" disabled={title.trim() === "" || amount.trim() === ""}>
            {t("obligations.add.submit")}
          </PrimaryButton>
        </div>
      </form>
    </Card>
  );
}

function DebtsSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const list = useQuery({ queryKey: financeKeys.debts, queryFn: fetchers.debts });
  const [creditor, setCreditor] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [payments, setPayments] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const next = unwrap(
        await commands.addDebt(creditor, amount, note.trim() === "" ? null : note),
      );
      queryClient.setQueryData(financeKeys.debts, next);
      setCreditor("");
      setAmount("");
      setNote("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function pay(debt: DebtDto) {
    setError(null);
    try {
      const next = unwrap(await commands.payDebt(debt.id, payments[debt.id] ?? ""));
      queryClient.setQueryData(financeKeys.debts, next);
      setPayments((current) => ({ ...current, [debt.id]: "" }));
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("obligations.debts.title")}>
      {list.data?.length === 0 ? (
        <p className="text-sm text-muted">{t("obligations.debts.empty")}</p>
      ) : null}
      {list.data !== undefined && list.data.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border">
          {list.data.map((debt) => (
            <li key={debt.id} className="flex flex-col gap-3 py-3">
              <div className="flex items-start justify-between gap-4">
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-base text-text">{debt.creditor}</span>
                  <span className="text-xs text-subtle">
                    {t("obligations.debts.principal", { amount: debt.principal.formatted })} ·{" "}
                    {debt.incurredOn}
                  </span>
                </span>
                <Stat
                  label={t("obligations.debts.outstanding")}
                  value={debt.outstanding.formatted}
                />
              </div>
              <form
                className="flex flex-wrap items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  void pay(debt);
                }}
              >
                <div className="min-w-0 flex-1">
                  <Field
                    id={`pay-${debt.id}`}
                    label={t("obligations.debts.payAmount")}
                    value={payments[debt.id] ?? ""}
                    inputMode="decimal"
                    autoComplete="off"
                    onChange={(event) => {
                      setPayments((current) => ({ ...current, [debt.id]: event.target.value }));
                    }}
                  />
                </div>
                <SecondaryButton type="submit" disabled={(payments[debt.id] ?? "").trim() === ""}>
                  {t("obligations.debts.pay")}
                </SecondaryButton>
              </form>
            </li>
          ))}
        </ul>
      ) : null}

      <form
        className="flex flex-col gap-4 border-t border-border pt-4"
        onSubmit={(event) => void add(event)}
      >
        <h3 className="text-sm font-medium text-text">{t("obligations.debts.add")}</h3>
        <Field
          id="debt-creditor"
          label={t("obligations.debts.creditor")}
          value={creditor}
          autoComplete="off"
          onChange={(event) => {
            setCreditor(event.target.value);
          }}
        />
        <Field
          id="debt-amount"
          label={t("obligations.debts.amount")}
          value={amount}
          inputMode="decimal"
          autoComplete="off"
          onChange={(event) => {
            setAmount(event.target.value);
          }}
        />
        <Field
          id="debt-note"
          label={t("obligations.debts.note")}
          value={note}
          autoComplete="off"
          onChange={(event) => {
            setNote(event.target.value);
          }}
        />
        {error !== null ? <Alert>{error}</Alert> : null}
        <div>
          <PrimaryButton type="submit" disabled={creditor.trim() === "" || amount.trim() === ""}>
            {t("obligations.debts.submit")}
          </PrimaryButton>
        </div>
      </form>
    </Card>
  );
}
