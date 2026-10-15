import { useState } from "react";
import { useTranslation } from "react-i18next";
import { type OfferCheckDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, PrimaryButton } from "../finance/ui";

const QUESTIONS = [
  "guaranteedProfit",
  "lossPossible",
  "realGoodsOrWork",
  "needsNewMembers",
  "rushPressure",
  "writtenContract",
] as const;
type Question = (typeof QUESTIONS)[number];

function questionKey(question: Question) {
  switch (question) {
    case "guaranteedProfit":
      return "offer.q.guaranteedProfit" as const;
    case "lossPossible":
      return "offer.q.lossPossible" as const;
    case "realGoodsOrWork":
      return "offer.q.realGoodsOrWork" as const;
    case "needsNewMembers":
      return "offer.q.needsNewMembers" as const;
    case "rushPressure":
      return "offer.q.rushPressure" as const;
    default:
      return "offer.q.writtenContract" as const;
  }
}

function verdictKey(verdict: string) {
  switch (verdict) {
    case "GREEN":
      return "offer.verdict.GREEN" as const;
    case "YELLOW":
      return "offer.verdict.YELLOW" as const;
    default:
      return "offer.verdict.RED" as const;
  }
}

/**
 * «Kafolatlangan foyda» detektori (SPEC 2E.5, D13): 6 savol → yashil / sariq / qizil, har bayroq izohi bilan.
 * Qaror jadvali Rustda (`offer_check`); natija saqlanmaydi.
 */
export function OfferCheckCard() {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const [answers, setAnswers] = useState<Record<Question, boolean>>({
    guaranteedProfit: false,
    lossPossible: true,
    realGoodsOrWork: true,
    needsNewMembers: false,
    rushPressure: false,
    writtenContract: true,
  });
  const [result, setResult] = useState<OfferCheckDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function check() {
    setError(null);
    try {
      setResult(unwrap(await commands.checkOffer(answers)));
    } catch (caught) {
      setError(message(caught));
    }
  }

  const tone =
    result === null
      ? ""
      : result.verdict === "GREEN"
        ? "border-success text-success"
        : result.verdict === "YELLOW"
          ? "border-warning text-warning"
          : "border-danger text-danger";

  return (
    <Card title={t("offer.title")}>
      <p className="text-sm text-muted">{t("offer.intro")}</p>
      <div className="flex flex-col gap-2">
        {QUESTIONS.map((question) => (
          <label key={question} className="flex items-center gap-2 text-sm text-text">
            <input
              type="checkbox"
              checked={answers[question]}
              onChange={(event) => {
                const checked = event.currentTarget.checked;
                setAnswers((current) => ({ ...current, [question]: checked }));
              }}
            />
            {t(questionKey(question))}
          </label>
        ))}
      </div>
      <div>
        <PrimaryButton
          onClick={() => {
            void check();
          }}
        >
          {t("offer.check")}
        </PrimaryButton>
      </div>
      {result !== null ? (
        <div className={`flex flex-col gap-2 rounded-lg border px-4 py-3 ${tone}`} role="status">
          <p className="text-base font-semibold">{t(verdictKey(result.verdict))}</p>
          {result.flags.length === 0 ? (
            <p className="text-sm">{t("offer.noFlags")}</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm">
              {result.flags.map((flag) => (
                <li key={flag.code}>
                  {flag.red ? "● " : "○ "}
                  {flag.explanation}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
