import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type BorrowCheckDto,
  type LoanDto,
  type LoansDto,
  commands,
} from "../../bindings/bindings";
import { AgreementWizard } from "../agreements/AgreementWizard";
import { PayoffOrderCard } from "../debts/PayoffOrderCard";
import { PayoffPlannerCard } from "../debts/PayoffPlannerCard";
import { SellableCard } from "../debts/SellableCard";
import { familyFetchers, familyKeys } from "../family/queries";
import { RecoveryCard } from "../debts/RecoveryCard";
import { useApplyAgreement } from "../agreements/queries";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const TYPES = ["RELATIVE", "FRIEND", "SHOP", "BANK", "OTHER"] as const;
type CounterpartyType = (typeof TYPES)[number];

function typeKey(value: string) {
  switch (value) {
    case "BANK":
      return "debts.type.BANK" as const;
    case "SHOP":
      return "debts.type.SHOP" as const;
    case "RELATIVE":
      return "debts.type.RELATIVE" as const;
    case "FRIEND":
      return "debts.type.FRIEND" as const;
    default:
      return "debts.type.OTHER" as const;
  }
}

function verdictKey(value: string) {
  switch (value) {
    case "OK":
      return "debts.verdict.OK" as const;
    case "CAUTION":
      return "debts.verdict.CAUTION" as const;
    default:
      return "debts.verdict.STOP" as const;
  }
}

/** bp → «35,0 %» (ko'rsatish uchun). */
export function burdenText(bp: number): string {
  return `${String(Math.floor(bp / 100))},${String(Math.floor((bp % 100) / 10))} %`;
}

/**
 * «Qarzlar» (SPEC 2D.5–2D.6, 2D.9): olingan va bergan qarzlar to'lash rejasi bilan, «to'xta va o'yla» tekshiruvi,
 * «qarzsiz kun», tilxat (D8A `LOAN` kelishuvi). Foiz maydoni yo'q; `STOP` taqiq emas — ongli qaror.
 */
export function DebtsPage() {
  const { t } = useTranslation();
  const loans = useQuery({
    queryKey: financeKeys.loans,
    queryFn: () => commands.getLoans().then(unwrap),
  });
  const [iou, setIou] = useState<string | null>(null);
  const [resetNotice, setResetNotice] = useState(false);
  const queryClient = useQueryClient();

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("nav.debts")} subtitle={t("debts.subtitle")} />
      {loans.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {loans.isSuccess ? (
        <>
          <Card title={t("debts.summaryTitle")}>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <Stat
                label={t("debts.totalOutstanding")}
                value={loans.data.totalOutstanding.formatted}
              />
              <Stat
                label={t("debts.totalReceivable")}
                value={loans.data.totalReceivable.formatted}
              />
              <Stat
                label={t("debts.monthlyBurden")}
                value={loans.data.monthlyBurden.formatted}
                hint={t("debts.monthlyIncomeHint", { amount: loans.data.monthlyIncome.formatted })}
              />
              <Stat
                label={t("debts.debtFreeDay")}
                value={loans.data.debtFreeDay ?? t("debts.noDebt")}
                hint={t("debts.debtFreeHint")}
              />
            </div>
          </Card>
          {resetNotice ? (
            <p
              className="rounded-lg border border-success/40 px-4 py-3 text-sm text-success"
              role="status"
            >
              {t("debts.recoveryReset")}
            </p>
          ) : null}
          <LoanList
            title={t("debts.takenTitle")}
            empty={t("debts.takenEmpty")}
            loans={loans.data.taken}
            onIou={(id) => {
              setIou(id);
            }}
            onReset={() => {
              setResetNotice(true);
              // Rejim Rustda STANDARD ga qaytdi — tiklash kartasi va byudjet keshini yangilaymiz.
              void queryClient.invalidateQueries({ queryKey: financeKeys.recovery });
            }}
          />
          <LoanList
            title={t("debts.givenTitle")}
            empty={t("debts.givenEmpty")}
            loans={loans.data.given}
          />
          <AddLoanCard />
          <PayoffOrderCard payoff={loans.data.payoff} />
          <SellableCard
            sellable={loans.data.sellable}
            outstanding={loans.data.totalOutstanding.formatted}
          />
          <RecoveryCard />
          <PayoffPlannerCard loans={loans.data.taken} />
        </>
      ) : null}
      {iou !== null ? (
        <IouOpener
          loanId={iou}
          onClose={() => {
            setIou(null);
          }}
        />
      ) : null}
    </div>
  );
}

function LoanList({
  title,
  empty,
  loans,
  onIou,
  onReset,
}: {
  title: string;
  empty: string;
  loans: LoanDto[];
  onIou?: (id: string) => void;
  onReset?: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const members = useQuery({ queryKey: familyKeys.members, queryFn: familyFetchers.members });
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [contributors, setContributors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function pay(loan: LoanDto) {
    setError(null);
    try {
      const next: LoansDto = unwrap(
        await commands.payLoan({
          loanId: loan.id,
          amount: amounts[loan.id] ?? "",
          paidOn: null,
          contributorId:
            (contributors[loan.id] ?? "") === "" ? null : (contributors[loan.id] ?? null),
        }),
      );
      queryClient.setQueryData(financeKeys.loans, next);
      if (next.recoveryModeReset) {
        onReset?.();
      }
      setAmounts((current) => ({ ...current, [loan.id]: "" }));
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={title}>
      {loans.length === 0 ? <p className="text-sm text-muted">{empty}</p> : null}
      {loans.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {loans.map((loan) => (
            <li
              key={loan.id}
              className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <span className="flex flex-col gap-1">
                  <span className="text-sm text-text">
                    {loan.counterparty} · {t(typeKey(loan.counterpartyType))}
                    {loan.hasMarkup ? ` · ${t("debts.hasMarkup")}` : ""}
                  </span>
                  <span className="text-xs text-subtle">
                    {t("debts.principalLine", {
                      amount: loan.principal.formatted,
                      count: loan.installments,
                    })}{" "}
                    · {t("debts.paidLine", { amount: loan.paid.formatted })}
                    {loan.reason !== null ? ` · ${loan.reason}` : ""}
                  </span>
                  <span className="text-xs text-subtle">
                    {loan.settled
                      ? t("debts.settled")
                      : t("debts.nextLine", {
                          date: loan.nextDueOn ?? "—",
                          amount: loan.nextAmount?.formatted ?? "—",
                          last: loan.lastDueOn,
                        })}
                    {loan.borrowVerdict !== null ? ` · ${t(verdictKey(loan.borrowVerdict))}` : ""}
                  </span>
                  {loan.contributions.length > 0 ? (
                    <span className="text-xs text-subtle">
                      {t("debts.contributions")}:{" "}
                      {loan.contributions.map((c) => `${c.name} ${c.total.formatted}`).join(", ")}
                    </span>
                  ) : null}
                </span>
                <span className="text-base font-semibold text-text">
                  {loan.outstanding.formatted}
                </span>
              </div>
              {!loan.settled ? (
                <form
                  className="flex flex-wrap items-end gap-2"
                  onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
                    event.preventDefault();
                    void pay(loan);
                  }}
                >
                  <div className="w-44">
                    <Field
                      id={`pay-${loan.id}`}
                      label={t("debts.payAmount")}
                      inputMode="numeric"
                      value={amounts[loan.id] ?? ""}
                      onChange={(event) => {
                        const value = event.currentTarget.value;
                        setAmounts((current) => ({ ...current, [loan.id]: value }));
                      }}
                    />
                  </div>
                  {loan.direction === "TAKEN" && members.isSuccess && members.data.length > 0 ? (
                    <div className="flex flex-col gap-2">
                      <label htmlFor={`contrib-${loan.id}`} className="text-sm text-muted">
                        {t("debts.contributor")}
                      </label>
                      <select
                        id={`contrib-${loan.id}`}
                        className={SELECT_CLASS}
                        value={contributors[loan.id] ?? ""}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setContributors((current) => ({ ...current, [loan.id]: value }));
                        }}
                      >
                        <option value="">{t("debts.contributorNone")}</option>
                        {members.data.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : null}
                  <PrimaryButton type="submit" disabled={(amounts[loan.id] ?? "").trim() === ""}>
                    {loan.direction === "TAKEN" ? t("debts.pay") : t("debts.receive")}
                  </PrimaryButton>
                  {onIou !== undefined ? (
                    <SecondaryButton
                      onClick={() => {
                        onIou(loan.id);
                      }}
                    >
                      {loan.agreementId === null ? t("debts.iouCreate") : t("debts.iouOpen")}
                    </SecondaryButton>
                  ) : null}
                </form>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

/** Tilxat: kelishuvni yaratadi (yoki mavjudini oladi) va ustani ochadi. */
function IouOpener({ loanId, onClose }: { loanId: string; onClose: () => void }) {
  const apply = useApplyAgreement();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [agreementId, setAgreementId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const state = { cancelled: false };
    void (async () => {
      try {
        const created = unwrap(await commands.createIou(loanId));
        await apply(created);
        await queryClient.invalidateQueries({ queryKey: financeKeys.loans });
        if (!state.cancelled) {
          setAgreementId(created.id);
        }
      } catch (caught) {
        if (!state.cancelled) {
          setError(message(caught));
        }
      }
    })();
    return () => {
      state.cancelled = true;
    };
  }, [loanId, apply, queryClient, message]);

  if (error !== null) {
    return <Alert>{error}</Alert>;
  }
  if (agreementId === null) {
    return null;
  }
  return <AgreementWizard id={agreementId} onClose={onClose} />;
}

function AddLoanCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [direction, setDirection] = useState<"TAKEN" | "GIVEN">("TAKEN");
  const [counterparty, setCounterparty] = useState("");
  const [type, setType] = useState<CounterpartyType>("RELATIVE");
  const [reason, setReason] = useState("");
  const [principal, setPrincipal] = useState("");
  const [installments, setInstallments] = useState("6");
  const [firstDue, setFirstDue] = useState("");
  const [hasMarkup, setHasMarkup] = useState(false);
  const [necessity, setNecessity] = useState(false);
  const [alternative, setAlternative] = useState(false);
  const [check, setCheck] = useState<BorrowCheckDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const count = Number(installments);

  async function runCheck() {
    setError(null);
    try {
      setCheck(unwrap(await commands.checkBorrow({ principal, installments: count })));
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const next = unwrap(
        await commands.addLoan({
          direction,
          counterparty,
          counterpartyType: type,
          reason: reason.trim() === "" ? null : reason,
          principal,
          hasMarkup: direction === "TAKEN" && hasMarkup,
          incurredOn: null,
          installments: count,
          firstDueOn: firstDue,
          frictionNecessity: direction === "TAKEN" ? necessity : null,
          frictionAlternative: direction === "TAKEN" ? alternative : null,
        }),
      );
      queryClient.setQueryData(financeKeys.loans, next);
      setCounterparty("");
      setReason("");
      setPrincipal("");
      setFirstDue("");
      setCheck(null);
    } catch (caught) {
      setError(message(caught));
    }
  }

  const canSubmit =
    counterparty.trim() !== "" &&
    principal.trim() !== "" &&
    firstDue !== "" &&
    Number.isInteger(count) &&
    count > 0;

  return (
    <Card title={t("debts.addTitle")}>
      <form className="flex flex-col gap-4" onSubmit={(event) => void add(event)}>
        <div className="flex flex-col gap-2">
          <label htmlFor="loan-direction" className="text-sm text-muted">
            {t("debts.direction")}
          </label>
          <select
            id="loan-direction"
            className={SELECT_CLASS}
            value={direction}
            onChange={(event) => {
              setDirection(event.currentTarget.value === "GIVEN" ? "GIVEN" : "TAKEN");
              setCheck(null);
            }}
          >
            <option value="TAKEN">{t("debts.taken")}</option>
            <option value="GIVEN">{t("debts.given")}</option>
          </select>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            id="loan-counterparty"
            label={direction === "TAKEN" ? t("debts.creditor") : t("debts.debtor")}
            value={counterparty}
            onChange={(event) => {
              setCounterparty(event.currentTarget.value);
            }}
          />
          <div className="flex flex-col gap-2">
            <label htmlFor="loan-type" className="text-sm text-muted">
              {t("debts.typeLabel")}
            </label>
            <select
              id="loan-type"
              className={SELECT_CLASS}
              value={type}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setType(TYPES.find((k) => k === value) ?? "OTHER");
              }}
            >
              {TYPES.map((k) => (
                <option key={k} value={k}>
                  {t(typeKey(k))}
                </option>
              ))}
            </select>
          </div>
          <Field
            id="loan-principal"
            label={t("debts.principal")}
            inputMode="numeric"
            value={principal}
            onChange={(event) => {
              setPrincipal(event.currentTarget.value);
              setCheck(null);
            }}
          />
          <Field
            id="loan-reason"
            label={t("debts.reason")}
            value={reason}
            onChange={(event) => {
              setReason(event.currentTarget.value);
            }}
          />
          <Field
            id="loan-installments"
            label={t("debts.installments")}
            type="number"
            min={1}
            max={120}
            value={installments}
            onChange={(event) => {
              setInstallments(event.currentTarget.value);
              setCheck(null);
            }}
          />
          <Field
            id="loan-first-due"
            label={t("debts.firstDue")}
            type="date"
            value={firstDue}
            onChange={(event) => {
              setFirstDue(event.currentTarget.value);
            }}
          />
        </div>
        {direction === "TAKEN" ? (
          <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
            <p className="text-sm font-medium text-text">{t("debts.frictionTitle")}</p>
            <p className="text-xs text-subtle">{t("debts.frictionHint")}</p>
            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={necessity}
                onChange={(event) => {
                  setNecessity(event.currentTarget.checked);
                }}
              />
              {t("debts.frictionNecessity")}
            </label>
            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={alternative}
                onChange={(event) => {
                  setAlternative(event.currentTarget.checked);
                }}
              />
              {t("debts.frictionAlternative")}
            </label>
            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={hasMarkup}
                onChange={(event) => {
                  setHasMarkup(event.currentTarget.checked);
                }}
              />
              {t("debts.hasMarkupLabel")}
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <SecondaryButton
                disabled={principal.trim() === "" || !Number.isInteger(count) || count <= 0}
                onClick={() => {
                  void runCheck();
                }}
              >
                {t("debts.checkBurden")}
              </SecondaryButton>
              {check !== null ? (
                <span
                  className={`text-sm ${check.verdict === "STOP" ? "text-danger" : "text-text"}`}
                >
                  {t(verdictKey(check.verdict))} —{" "}
                  {t("debts.burdenLine", {
                    burden: check.monthlyBurden.formatted,
                    percent: burdenText(check.burdenBp),
                  })}
                </span>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="text-xs text-subtle">{t("debts.givenNoInterest")}</p>
        )}
        <div>
          <PrimaryButton type="submit" disabled={!canSubmit}>
            {t("debts.add")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
