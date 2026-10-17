import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type BudgetDto, type RescueDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";
import { EnvelopesCard } from "./EnvelopesCard";
import { SubscriptionsCard } from "./SubscriptionsCard";
import { budgetFetchers, budgetKeys, useApplyBudget } from "./queries";

/**
 * «Byudjet»: qutqarilgan pul hisobi (domen hisoblaydi), «Kelajagim»ga o'tkazish, obunalar va konvertlar.
 * Pul hisobi faqat ko'rsatiladi; ko'proq sarflash ayblov emas — shunchaki holat (SPEC 2B.7).
 */
export function BudgetPage() {
  const { t } = useTranslation();
  const budget = useQuery({ queryKey: budgetKeys.overview, queryFn: budgetFetchers.overview });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("nav.budget")} subtitle={t("budget.subtitle")} />
      {budget.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {budget.isSuccess ? (
        <>
          <RescueCard rescue={budget.data.rescue} />
          <SubscriptionsCard subscriptions={budget.data.subscriptions} />
          <EnvelopesCard envelopes={budget.data.envelopes} />
        </>
      ) : null}
    </div>
  );
}

/** «Qutqarilgan pul» hisobi, «Kelajagim»ga o'tkazish va bazaviy davr. */
function RescueCard({ rescue }: { rescue: RescueDto }) {
  const { t } = useTranslation();
  const apply = useApplyBudget();
  const message = useErrorMessage();
  const [amount, setAmount] = useState("");
  const [baseline, setBaseline] = useState("");
  // Har forma o'z xatosini tugmasi ostida ko'rsatadi: xabar bosilgan joydan uzoqda qolmasin.
  const [transferError, setTransferError] = useState<string | null>(null);
  const [baselineError, setBaselineError] = useState<string | null>(null);
  const nothingToTransfer = rescue.available.minor === "0";

  async function run(
    action: () => Promise<BudgetDto>,
    onDone: () => void,
    setError: (value: string | null) => void,
  ) {
    setError(null);
    try {
      await apply(await action());
      onDone();
    } catch (caught) {
      setError(message(caught));
    }
  }

  function transfer(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(
      () => commands.transferToVaultFromRescue({ amount }).then(unwrap),
      () => {
        setAmount("");
      },
      setTransferError,
    );
  }

  function saveBaseline(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(
      () => commands.setBaselinePeriod({ periodStart: baseline }).then(unwrap),
      () => {
        setBaseline("");
      },
      setBaselineError,
    );
  }

  return (
    <Card title={t("budget.rescueTitle")}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat
          label={t("budget.havas")}
          value={rescue.havas.formatted}
          hint={t("budget.havasHint")}
        />
        <Stat label={t("budget.subscriptions")} value={rescue.subscriptions.formatted} />
        <Stat label={t("budget.envelopes")} value={rescue.envelopes.formatted} />
        <Stat label={t("budget.total")} value={rescue.total.formatted} />
        <Stat label={t("budget.transferred")} value={rescue.transferred.formatted} />
        <Stat
          label={t("budget.available")}
          value={rescue.available.formatted}
          hint={t("budget.availableHint")}
        />
      </div>
      {rescue.spentMore ? <p className="text-sm text-muted">{t("budget.spentMore")}</p> : null}
      {rescue.hasBaseline && rescue.baselineStart !== null ? (
        <p className="text-sm text-muted">
          {t("budget.baselineInfo", { start: rescue.baselineStart })}
        </p>
      ) : null}
      {rescue.hasBaseline ? null : <p className="text-sm text-muted">{t("budget.noBaseline")}</p>}

      <form className="flex flex-col gap-4" onSubmit={transfer}>
        <h3 className="text-sm font-medium text-text">{t("budget.transferTitle")}</h3>
        <Field
          id="budget-transfer"
          label={t("budget.transferAmount")}
          inputMode="numeric"
          value={amount}
          onChange={(event) => {
            setAmount(event.currentTarget.value);
          }}
        />
        <div>
          <PrimaryButton type="submit" disabled={amount.trim() === "" || nothingToTransfer}>
            {t("budget.transferAction")}
          </PrimaryButton>
        </div>
        {transferError !== null ? <Alert>{transferError}</Alert> : null}
      </form>

      <form className="flex flex-col gap-4" onSubmit={saveBaseline}>
        <h3 className="text-sm font-medium text-text">{t("budget.baselineTitle")}</h3>
        <Field
          id="budget-baseline"
          type="date"
          label={t("budget.baselineStart")}
          value={baseline}
          onChange={(event) => {
            setBaseline(event.currentTarget.value);
          }}
        />
        <div>
          <SecondaryButton type="submit" disabled={baseline === ""}>
            {t("budget.baselineAction")}
          </SecondaryButton>
        </div>
        {baselineError !== null ? <Alert>{baselineError}</Alert> : null}
      </form>
    </Card>
  );
}
