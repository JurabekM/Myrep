import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type LumpSumPlanDto, commands } from "../../bindings/bindings";
import { unwrap } from "./command-error";
import { useErrorMessage } from "./errors";
import { Alert, Card, Field, PrimaryButton, Stat } from "./ui";

const CURRENCIES = ["UZS", "USD", "EUR", "RUB"] as const;
const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

/**
 * «Qal'a devori» (SPEC 2G.5, 7-qonun): katta summa (chet eldan qaytish, meros, mulk sotuvi) avval oilaning
 * 6 oylik zaxira kamomadiga, qolgani sarmoyaga. Chet el valyutasi — foydalanuvchi kiritgan kurs bilan.
 * Xarajat tarixi bo'lmasa — taxminiy oylik zarur xarajat so'raladi. Hisob Rustda.
 */
export function LumpSumCard() {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState<(typeof CURRENCIES)[number]>("USD");
  const [rate, setRate] = useState("");
  const [estimate, setEstimate] = useState("");
  const [plan, setPlan] = useState<LumpSumPlanDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsEstimate, setNeedsEstimate] = useState(false);

  async function calculate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      setPlan(
        unwrap(
          await commands.planLumpSum({
            amount,
            currency,
            rate: currency === "UZS" || rate.trim() === "" ? null : rate,
            reserveEstimate: estimate.trim() === "" ? null : estimate,
          }),
        ),
      );
    } catch (caught) {
      const text = message(caught);
      if (text === t("errors.reserveEstimateRequired")) {
        setNeedsEstimate(true);
      }
      setError(text);
    }
  }

  return (
    <Card title={t("lumpSum.title")}>
      <p className="text-sm text-muted">{t("lumpSum.intro")}</p>
      <form className="grid gap-3 sm:grid-cols-4" onSubmit={(event) => void calculate(event)}>
        <Field
          id="lump-amount"
          label={t("lumpSum.amount")}
          inputMode="numeric"
          value={amount}
          onChange={(event) => {
            setAmount(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="lump-currency" className="text-sm text-muted">
            {t("lumpSum.currency")}
          </label>
          <select
            id="lump-currency"
            className={SELECT_CLASS}
            value={currency}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setCurrency(CURRENCIES.find((c) => c === value) ?? "UZS");
            }}
          >
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        {currency !== "UZS" ? (
          <Field
            id="lump-rate"
            label={t("lumpSum.rate", { currency })}
            inputMode="numeric"
            value={rate}
            onChange={(event) => {
              setRate(event.currentTarget.value);
            }}
          />
        ) : null}
        {needsEstimate ? (
          <Field
            id="lump-estimate"
            label={t("lumpSum.estimate")}
            inputMode="numeric"
            value={estimate}
            onChange={(event) => {
              setEstimate(event.currentTarget.value);
            }}
          />
        ) : null}
        <div className="flex items-end">
          <PrimaryButton
            type="submit"
            disabled={amount.trim() === "" || (currency !== "UZS" && rate.trim() === "")}
          >
            {t("lumpSum.calculate")}
          </PrimaryButton>
        </div>
      </form>
      {plan !== null ? (
        <div className="flex flex-col gap-3" role="status">
          <div className="grid gap-3 sm:grid-cols-2">
            <Stat
              label={t("lumpSum.amountBase")}
              value={plan.amount.formatted}
              hint={
                plan.rateUsed !== null
                  ? t("lumpSum.rateLine", {
                      entered: plan.amountEntered.formatted,
                      rate: plan.rateUsed.formatted,
                    })
                  : undefined
              }
            />
            <Stat
              label={t("lumpSum.target")}
              value={plan.reserveTarget.formatted}
              hint={
                plan.reserveTargetSource === "HISTORY"
                  ? t("lumpSum.targetHistory")
                  : t("lumpSum.targetEstimate")
              }
            />
            <Stat label={t("lumpSum.toReserve")} value={plan.toReserve.formatted} />
            <Stat label={t("lumpSum.toInvest")} value={plan.toInvest.formatted} />
          </div>
          <p className="text-sm text-text">
            {plan.reserveFilled ? t("lumpSum.filled") : t("lumpSum.notFilled")}
          </p>
          <p className="text-xs text-subtle">{t("lumpSum.wall")}</p>
        </div>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
