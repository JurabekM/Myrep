import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type HustlePlanDto, commands } from "../../bindings/bindings";
import { financeKeys } from "../finance/queries";
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
  const [templateId, setTemplateId] = useState("");
  const templates = useQuery({
    queryKey: financeKeys.hustleTemplates,
    queryFn: () => commands.listHustleTemplates().then(unwrap),
  });
  const template = templates.data?.find((item) => item.id === templateId) ?? null;

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
      {templates.isSuccess ? (
        <div className="flex flex-col gap-2 rounded-lg border border-border bg-raised px-4 py-3">
          <label htmlFor="hustle-template" className="text-sm text-muted">
            {t("hustle.template")}
          </label>
          <select
            id="hustle-template"
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
            value={templateId}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setTemplateId(value);
              const chosen = templates.data.find((item) => item.id === value);
              if (chosen !== undefined && skill.trim() === "") {
                setSkill(chosen.name);
              }
            }}
          >
            <option value="">{t("hustle.templateNone")}</option>
            {templates.data.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {template !== null ? (
            <div className="flex flex-col gap-1 text-sm">
              <p className="text-muted">{template.story}</p>
              <p className="text-xs text-subtle">{t("hustle.templateHint")}</p>
              <ul className="list-disc pl-5 text-text" aria-label={t("hustle.templateLines")}>
                {template.capexLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <p className="text-warning">{template.demandQuestion}</p>
            </div>
          ) : null}
        </div>
      ) : null}
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
