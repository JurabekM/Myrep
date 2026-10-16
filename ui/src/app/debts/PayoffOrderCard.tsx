import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { type LoansDto, type PayoffOrderDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import { Alert, Card, SecondaryButton, Stat } from "../finance/ui";

const STRATEGIES = ["SNOWBALL", "AVALANCHE"] as const;

function strategyKey(value: string) {
  return value === "AVALANCHE"
    ? ("payoffOrder.strategy.AVALANCHE" as const)
    : ("payoffOrder.strategy.SNOWBALL" as const);
}

/**
 * Yopish tartibi (SPEC 2D.6, D10 qoldig'i): qor to'pi (eng kichik qoldiq avval) yoki ko'chki (ustamali avval).
 * Qo'shimcha summa = 70/20/10 «qarz» ulushi − oylik yuk. Simulyatsiya Rustda (`payoff_order`), bu yerda faqat ko'rsatish.
 */
export function PayoffOrderCard({ payoff }: { payoff: PayoffOrderDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);

  async function choose(strategy: (typeof STRATEGIES)[number]) {
    setError(null);
    try {
      const next: LoansDto = unwrap(await commands.setPayoffStrategy(strategy));
      queryClient.setQueryData(financeKeys.loans, next);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("payoffOrder.title")}>
      <p className="text-sm text-muted">{t("payoffOrder.intro")}</p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t("payoffOrder.title")}>
        {STRATEGIES.map((strategy) => (
          <SecondaryButton
            key={strategy}
            role="radio"
            aria-checked={payoff.strategy === strategy}
            className="aria-checked:border-accent aria-checked:bg-accent/15 aria-checked:font-semibold aria-checked:text-accent"
            onClick={() => {
              void choose(strategy);
            }}
          >
            {t(strategyKey(strategy))}
          </SecondaryButton>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label={t("payoffOrder.extra")} value={payoff.extra.formatted} />
        <Stat
          label={t("payoffOrder.debtFree")}
          value={payoff.debtFreeDay ?? t("debts.noDebt")}
          hint={
            payoff.totalMonths > 0
              ? t("payoffOrder.monthsHint", { months: payoff.totalMonths })
              : undefined
          }
        />
        <Stat
          label={t("payoffOrder.alternative")}
          value={
            payoff.steps.length === 0
              ? "—"
              : t("payoffOrder.monthsValue", { months: payoff.alternativeTotalMonths })
          }
        />
      </div>
      {payoff.steps.length === 0 ? (
        <p className="text-sm text-muted">{t("payoffOrder.empty")}</p>
      ) : (
        <ol className="flex flex-col gap-2" aria-label={t("payoffOrder.orderLabel")}>
          {payoff.steps.map((step, index) => (
            <li
              key={step.loanId}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-app px-4 py-2 text-sm"
            >
              <span className="text-text">
                {index + 1}. {step.counterparty}
                {step.hasMarkup ? ` · ${t("debts.hasMarkup")}` : ""}
                {index === 0 ? ` · ${t("payoffOrder.focus")}` : ""}
              </span>
              <span className="text-muted">
                {step.outstanding.formatted} ·{" "}
                {t("payoffOrder.clearsOn", { months: step.monthsToClear, date: step.clearOn })}
              </span>
            </li>
          ))}
        </ol>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
