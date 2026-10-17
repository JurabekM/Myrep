import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type RecoveryDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import { Alert, Card, Field, PrimaryButton, Stat } from "../finance/ui";

/**
 * «Qarz tiklash» rejimi va 70/20/10 taqsimoti (SPEC 2D, D10): daromad uch qismga — ehtiyoj, qarz, jamg'arma.
 * Jamg'arma ulushini 0 qilib bo'lmaydi (domen qoidasi, backend rad etadi). Qismlar Rustda hisoblanadi.
 */
export function RecoveryCard() {
  const { t } = useTranslation();
  const recovery = useQuery({
    queryKey: financeKeys.recovery,
    queryFn: () => commands.getRecovery().then(unwrap),
  });

  return (
    <Card title={t("recovery.title")}>
      <p className="text-sm text-muted">{t("recovery.intro")}</p>
      {recovery.isSuccess ? (
        <>
          <div className="grid gap-6 sm:grid-cols-3">
            <Stat label={t("recovery.needs")} value={recovery.data.parts[0]?.formatted ?? "—"} />
            <Stat label={t("recovery.debt")} value={recovery.data.parts[1]?.formatted ?? "—"} />
            <Stat
              label={t("recovery.savings")}
              value={recovery.data.parts[2]?.formatted ?? "—"}
              hint={t("recovery.incomeHint", { amount: recovery.data.income.formatted })}
            />
          </div>
          {/* Kalit: backend qiymati o'zgarsa forma qayta boshlanadi (effect'siz sinxronlash). */}
          <RecoveryForm
            key={`${recovery.data.mode}:${recovery.data.splitBp.join(",")}`}
            initial={recovery.data}
          />
        </>
      ) : null}
    </Card>
  );
}

function RecoveryForm({ initial }: { initial: RecoveryDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [mode, setMode] = useState<"STANDARD" | "DEBT_RECOVERY">(
    initial.mode === "DEBT_RECOVERY" ? "DEBT_RECOVERY" : "STANDARD",
  );
  const [needs, setNeeds] = useState(String((initial.splitBp[0] ?? 7000) / 100));
  const [debt, setDebt] = useState(String((initial.splitBp[1] ?? 2000) / 100));
  const [savings, setSavings] = useState(String((initial.splitBp[2] ?? 1000) / 100));
  const [error, setError] = useState<string | null>(null);

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const next: RecoveryDto = unwrap(
        await commands.setRecovery({
          mode,
          splitBp: [needs, debt, savings].map((value) => Math.round(Number(value) * 100)),
        }),
      );
      queryClient.setQueryData(financeKeys.recovery, next);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void save(event)}>
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={mode === "DEBT_RECOVERY"}
          onChange={(event) => {
            setMode(event.currentTarget.checked ? "DEBT_RECOVERY" : "STANDARD");
          }}
        />
        {t("recovery.modeToggle")}
      </label>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field
          id="recovery-needs"
          label={t("recovery.needsPercent")}
          inputMode="decimal"
          value={needs}
          onChange={(event) => {
            setNeeds(event.currentTarget.value);
          }}
        />
        <Field
          id="recovery-debt"
          label={t("recovery.debtPercent")}
          inputMode="decimal"
          value={debt}
          onChange={(event) => {
            setDebt(event.currentTarget.value);
          }}
        />
        <Field
          id="recovery-savings"
          label={t("recovery.savingsPercent")}
          inputMode="decimal"
          value={savings}
          onChange={(event) => {
            setSavings(event.currentTarget.value);
          }}
        />
      </div>
      <p className="text-xs text-subtle">{t("recovery.savingsRule")}</p>
      <div>
        <PrimaryButton type="submit">{t("recovery.save")}</PrimaryButton>
      </div>
      {error !== null ? <Alert>{error}</Alert> : null}
    </form>
  );
}
