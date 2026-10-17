import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type HustlePlanDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, SecondaryButton } from "../finance/ui";

function scenarioKey(name: string) {
  switch (name) {
    case "PESSIMISTIC":
      return "hustle.scenario.PESSIMISTIC" as const;
    case "OPTIMISTIC":
      return "hustle.scenario.OPTIMISTIC" as const;
    default:
      return "hustle.scenario.AVERAGE" as const;
  }
}

/**
 * «Hunardan ishga» (SPEC 2E.4, D13): CAPEX, oylik kirim/xarajat, ulush → uch stsenariy va payback
 * («hisob-kitobni uch marta qildim»). Hisob Rustda; natijadan bir bosishda sheriklik qoralamasi.
 */
export function HustleCard({ onDraft }: { onDraft: (title: string) => void }) {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const [skill, setSkill] = useState("");
  const [capex, setCapex] = useState("");
  const [income, setIncome] = useState("");
  const [expense, setExpense] = useState("");
  const [share, setShare] = useState("100");
  const [plan, setPlan] = useState<HustlePlanDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function calculate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      setPlan(
        unwrap(
          await commands.hustlePlan({
            capex,
            monthlyIncome: income,
            monthlyExpense: expense,
            myShareBp: Math.round(Number(share) * 100),
          }),
        ),
      );
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("hustle.title")}>
      <p className="text-sm text-muted">{t("hustle.intro")}</p>
      <form className="grid gap-3 sm:grid-cols-5" onSubmit={(event) => void calculate(event)}>
        <Field
          id="hustle-skill"
          label={t("hustle.skill")}
          value={skill}
          onChange={(event) => {
            setSkill(event.currentTarget.value);
          }}
        />
        <Field
          id="hustle-capex"
          label={t("hustle.capex")}
          inputMode="numeric"
          value={capex}
          onChange={(event) => {
            setCapex(event.currentTarget.value);
          }}
        />
        <Field
          id="hustle-income"
          label={t("hustle.income")}
          inputMode="numeric"
          value={income}
          onChange={(event) => {
            setIncome(event.currentTarget.value);
          }}
        />
        <Field
          id="hustle-expense"
          label={t("hustle.expense")}
          inputMode="numeric"
          value={expense}
          onChange={(event) => {
            setExpense(event.currentTarget.value);
          }}
        />
        <Field
          id="hustle-share"
          label={t("hustle.share")}
          inputMode="decimal"
          value={share}
          onChange={(event) => {
            setShare(event.currentTarget.value);
          }}
        />
        <div className="flex items-end sm:col-span-5">
          <PrimaryButton
            type="submit"
            disabled={capex.trim() === "" || income.trim() === "" || expense.trim() === ""}
          >
            {t("hustle.calculate")}
          </PrimaryButton>
        </div>
      </form>
      {plan !== null ? (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm" aria-label={t("hustle.tableLabel")}>
              <thead className="bg-raised text-left text-xs text-subtle">
                <tr>
                  <th className="px-3 py-2">{t("hustle.colScenario")}</th>
                  <th className="px-3 py-2">{t("hustle.colIncome")}</th>
                  <th className="px-3 py-2">{t("hustle.colExpense")}</th>
                  <th className="px-3 py-2">{t("hustle.colNet")}</th>
                  <th className="px-3 py-2">{t("hustle.colMine")}</th>
                  <th className="px-3 py-2">{t("hustle.colPayback")}</th>
                </tr>
              </thead>
              <tbody>
                {plan.scenarios.map((row) => (
                  <tr key={row.name} className="border-t border-border text-text">
                    <td className="px-3 py-2">{t(scenarioKey(row.name))}</td>
                    <td className="px-3 py-2">{row.income.formatted}</td>
                    <td className="px-3 py-2">{row.expense.formatted}</td>
                    <td
                      className={`px-3 py-2 ${row.net.minor.startsWith("-") ? "text-danger" : ""}`}
                    >
                      {row.net.formatted}
                    </td>
                    <td className="px-3 py-2">{row.myNet.formatted}</td>
                    <td className="px-3 py-2">
                      {row.paybackMonths === null
                        ? t("hustle.noPayback")
                        : t("hustle.months", { months: row.paybackMonths })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <SecondaryButton
              onClick={() => {
                onDraft(skill.trim() === "" ? t("hustle.defaultTitle") : skill);
              }}
            >
              {t("hustle.toPartnership")}
            </SecondaryButton>
          </div>
        </>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
