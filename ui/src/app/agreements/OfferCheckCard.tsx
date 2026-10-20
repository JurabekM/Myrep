import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type OfferCheckDto, type OffersDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import { Alert, Card, Field, PrimaryButton, SecondaryButton, Stat } from "../finance/ui";

const QUESTIONS = [
  "guaranteed",
  "lossShared",
  "realGoods",
  "recruitment",
  "pressure",
  "writtenContract",
  "exitEasy",
  "license",
  "verifiedInPerson",
] as const;
type Question = (typeof QUESTIONS)[number];
const ANSWERS = ["YES", "NO", "UNKNOWN"] as const;
type Answer = (typeof ANSWERS)[number];
const CHECKLIST = ["goods", "contract", "license", "source", "exit"] as const;

function questionKey(question: Question) {
  switch (question) {
    case "guaranteed":
      return "offer.q.guaranteed" as const;
    case "lossShared":
      return "offer.q.lossShared" as const;
    case "realGoods":
      return "offer.q.realGoods" as const;
    case "recruitment":
      return "offer.q.recruitment" as const;
    case "pressure":
      return "offer.q.pressure" as const;
    case "writtenContract":
      return "offer.q.writtenContract" as const;
    case "exitEasy":
      return "offer.q.exitEasy" as const;
    case "license":
      return "offer.q.license" as const;
    default:
      return "offer.q.verifiedInPerson" as const;
  }
}

function answerKey(answer: Answer) {
  switch (answer) {
    case "YES":
      return "offer.answer.YES" as const;
    case "NO":
      return "offer.answer.NO" as const;
    default:
      return "offer.answer.UNKNOWN" as const;
  }
}

function checklistKey(item: (typeof CHECKLIST)[number]) {
  switch (item) {
    case "goods":
      return "offer.checklist.goods" as const;
    case "contract":
      return "offer.checklist.contract" as const;
    case "license":
      return "offer.checklist.license" as const;
    case "source":
      return "offer.checklist.source" as const;
    default:
      return "offer.checklist.exit" as const;
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

function levelKey(level: string) {
  switch (level) {
    case "NONE":
      return "offer.level.NONE" as const;
    case "CAUTION":
      return "offer.level.CAUTION" as const;
    default:
      return "offer.level.FLEE" as const;
  }
}

function categoryKey(category: string) {
  switch (category) {
    case "RIBO":
      return "offer.category.RIBO" as const;
    case "GHARAR":
      return "offer.category.GHARAR" as const;
    default:
      return "offer.category.QIMOR" as const;
  }
}

function decisionKey(decision: string) {
  switch (decision) {
    case "ACCEPTED":
      return "offer.decision.ACCEPTED" as const;
    case "POSTPONED":
      return "offer.decision.POSTPONED" as const;
    default:
      return "offer.decision.DECLINED" as const;
  }
}

/** bp → «5,2» ko'rinishidagi barobar matni (faqat ko'rsatish; hisob Rustda). */
function multipleText(bp: number) {
  return (bp / 10_000).toLocaleString("uz-UZ", { maximumFractionDigits: 1 });
}

function toneOf(verdict: string) {
  return verdict === "GREEN"
    ? "border-success text-success"
    : verdict === "YELLOW"
      ? "border-warning text-warning"
      : "border-danger text-danger";
}

/**
 * Taklif tekshiruvi (SPEC 2E.5 + 2G, 7-qonun): 9 savol «ha / yo'q / bilmayman», besh xavf belgisi va daraja
 * («bittasi — hushyor, ikkitasi — qoch»), toifalar (ribo / g'arar / qimor), va'da qilingan foydani yillikka
 * aylantirish (faqat ogohlantirish), «o'z ko'zim bilan ko'raman» ro'yxati, «to'xta, maslahatlash» qarori
 * (maslahatchi + 24 soat) va tarix. Qoidalar va hisob Rustda; natija saqlanadi.
 */
export function OfferCheckCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const offers = useQuery({
    queryKey: financeKeys.offers,
    queryFn: () => commands.listOfferChecks().then(unwrap),
  });
  const [answers, setAnswers] = useState<Record<Question, Answer>>({
    guaranteed: "UNKNOWN",
    lossShared: "UNKNOWN",
    realGoods: "UNKNOWN",
    recruitment: "UNKNOWN",
    pressure: "UNKNOWN",
    writtenContract: "UNKNOWN",
    exitEasy: "UNKNOWN",
    license: "UNKNOWN",
    verifiedInPerson: "UNKNOWN",
  });
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [promised, setPromised] = useState("");
  const [advisor, setAdvisor] = useState("");
  const [result, setResult] = useState<OfferCheckDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function check(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const promisedBp =
        promised.trim() === "" ? null : Math.round(Number(promised.replace(",", ".")) * 100);
      const checked = unwrap(
        await commands.checkOffer({
          title: title.trim() === "" ? null : title,
          answers,
          amount: amount.trim() === "" ? null : amount,
          promisedMonthlyBp: promisedBp !== null && Number.isFinite(promisedBp) ? promisedBp : null,
          advisor: advisor.trim() === "" ? null : advisor,
        }),
      );
      setResult(checked);
      await queryClient.invalidateQueries({ queryKey: financeKeys.offers });
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function decide(id: string, decision: string, advisorName: string | null) {
    setError(null);
    try {
      const next: OffersDto = unwrap(
        await commands.decideOffer({ id, decision, advisor: advisorName }),
      );
      queryClient.setQueryData(financeKeys.offers, next);
      const updated = next.items.find((item) => item.id === id) ?? null;
      if (result !== null && result.id === id) {
        setResult(updated);
      }
    } catch (caught) {
      setError(message(caught));
    }
  }

  const shown = result ?? offers.data?.items[0] ?? null;

  return (
    <Card title={t("offer.title")}>
      <p className="text-sm text-muted">{t("offer.intro")}</p>
      <form className="flex flex-col gap-4" onSubmit={(event) => void check(event)}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Field
            id="offer-title"
            label={t("offer.titleLabel")}
            value={title}
            onChange={(event) => {
              setTitle(event.currentTarget.value);
            }}
          />
          <Field
            id="offer-amount"
            label={t("offer.amount")}
            inputMode="numeric"
            value={amount}
            onChange={(event) => {
              setAmount(event.currentTarget.value);
            }}
          />
          <Field
            id="offer-promised"
            label={t("offer.promised")}
            inputMode="decimal"
            value={promised}
            onChange={(event) => {
              setPromised(event.currentTarget.value);
            }}
          />
          <Field
            id="offer-advisor"
            label={t("offer.advisor")}
            value={advisor}
            onChange={(event) => {
              setAdvisor(event.currentTarget.value);
            }}
          />
        </div>
        <div className="flex flex-col gap-2">
          {QUESTIONS.map((question) => (
            <fieldset
              key={question}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-app px-3 py-2"
            >
              <legend className="sr-only">{t(questionKey(question))}</legend>
              <span className="text-sm text-text">{t(questionKey(question))}</span>
              <span className="flex gap-3 text-sm text-muted">
                {ANSWERS.map((answer) => (
                  <label key={answer} className="flex items-center gap-1">
                    <input
                      type="radio"
                      name={`offer-${question}`}
                      value={answer}
                      checked={answers[question] === answer}
                      aria-label={`${t(questionKey(question))}: ${t(answerKey(answer))}`}
                      onChange={() => {
                        setAnswers((current) => ({ ...current, [question]: answer }));
                      }}
                    />
                    {t(answerKey(answer))}
                  </label>
                ))}
              </span>
            </fieldset>
          ))}
        </div>
        <div>
          <PrimaryButton type="submit">{t("offer.check")}</PrimaryButton>
        </div>
      </form>

      <div className="rounded-lg border border-border bg-raised px-4 py-3">
        <p className="text-sm font-medium text-text">{t("offer.checklist.title")}</p>
        <p className="text-xs text-subtle">{t("offer.checklist.hint")}</p>
        <ul className="mt-2 list-disc pl-5 text-sm text-muted">
          {CHECKLIST.map((item) => (
            <li key={item}>{t(checklistKey(item))}</li>
          ))}
        </ul>
      </div>

      {shown !== null ? (
        <OfferResult
          offer={shown}
          onDecide={(decision, advisorName) => {
            void decide(shown.id, decision, advisorName);
          }}
        />
      ) : null}

      {offers.isSuccess && offers.data.items.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-text">{t("offer.historyTitle")}</p>
          <ul className="flex flex-col gap-1 text-sm" aria-label={t("offer.historyTitle")}>
            {offers.data.items.map((item) => (
              <li key={item.id} className="flex flex-wrap justify-between gap-2 text-muted">
                <span>
                  {item.checkedOn} · {item.title ?? t("offer.untitled")} ·{" "}
                  <span className={toneOf(item.verdict).split(" ")[1]}>
                    {t(verdictKey(item.verdict)).split(":")[0]}
                  </span>
                  {item.amount !== null ? ` · ${item.amount.formatted}` : ""}
                </span>
                <span>
                  {item.decision !== null
                    ? t(decisionKey(item.decision))
                    : t("offer.decision.pending")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

function OfferResult({
  offer,
  onDecide,
}: {
  offer: OfferCheckDto;
  onDecide: (decision: string, advisor: string | null) => void;
}) {
  const { t } = useTranslation();
  const [advisor, setAdvisor] = useState(offer.advisor ?? "");
  const advisorName = advisor.trim() === "" ? null : advisor.trim();
  /** Savol kodidan matn (noma'lum kod — kodning o'zi). */
  const questionLabel = (code: string) => {
    const question = QUESTIONS.find((q) => q === code);
    return question === undefined ? code : t(questionKey(question));
  };
  return (
    <div
      className={`flex flex-col gap-3 rounded-lg border px-4 py-3 ${toneOf(offer.verdict)}`}
      role="status"
    >
      <p className="text-base font-semibold">{t(verdictKey(offer.verdict))}</p>
      <p className="text-sm">
        {t(levelKey(offer.level), { count: offer.signs.length })}
        {offer.categories.length > 0
          ? ` · ${offer.categories.map((c) => t(categoryKey(c))).join(" · ")}`
          : ""}
      </p>
      {offer.signs.length > 0 ? (
        <ol className="flex flex-col gap-1 text-sm text-text" aria-label={t("offer.signsTitle")}>
          {offer.signs.map((sign, index) => (
            <li key={sign.code}>
              {index + 1}. {sign.explanation}
            </li>
          ))}
        </ol>
      ) : null}
      {offer.flags.length > 0 ? (
        <ul className="flex flex-col gap-1 text-xs text-muted">
          {offer.flags.map((flag) => (
            <li key={`${flag.code}-${flag.question}`}>
              {flag.red ? "● " : "○ "}
              {flag.code === "UNKNOWN" ? `${questionLabel(flag.question)} — ` : ""}
              {flag.explanation}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{t("offer.noFlags")}</p>
      )}
      {offer.promised !== null ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Stat
            label={t("offer.promisedSimple", { percent: offer.promised.monthlyBp / 100 })}
            value={t("offer.multiple", { value: multipleText(offer.promised.simpleMultipleBp) })}
            hint={t("offer.promisedHint")}
          />
          <Stat
            label={t("offer.promisedCompound")}
            value={t("offer.multiple", { value: multipleText(offer.promised.compoundMultipleBp) })}
          />
        </div>
      ) : null}
      <div className="flex flex-col gap-2 border-t border-border pt-3 text-text">
        <p className="text-sm font-medium">{t("offer.stopTitle")}</p>
        <p className="text-xs text-muted">{t("offer.stopHint")}</p>
        {offer.decision !== null ? (
          <p className="text-sm">
            {t("offer.decidedLine", {
              decision: t(decisionKey(offer.decision)),
              date: offer.decidedOn ?? "",
            })}
            {offer.advisor !== null ? ` · ${t("offer.advisorLine", { name: offer.advisor })}` : ""}
          </p>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            <Field
              id={`offer-advisor-${offer.id}`}
              label={t("offer.advisorQuestion")}
              value={advisor}
              onChange={(event) => {
                setAdvisor(event.currentTarget.value);
              }}
            />
            <SecondaryButton
              onClick={() => {
                onDecide("DECLINED", advisorName);
              }}
            >
              {t("offer.decline")}
            </SecondaryButton>
            <SecondaryButton
              onClick={() => {
                onDecide("POSTPONED", advisorName);
              }}
            >
              {t("offer.postpone")}
            </SecondaryButton>
            <PrimaryButton
              disabled={advisorName === null || offer.coolingHoursLeft > 0}
              onClick={() => {
                onDecide("ACCEPTED", advisorName);
              }}
            >
              {t("offer.accept")}
            </PrimaryButton>
            <span className="text-xs text-subtle">
              {advisorName === null
                ? t("offer.acceptNeedsAdvisor")
                : offer.coolingHoursLeft > 0
                  ? t("offer.acceptWait", { hours: offer.coolingHoursLeft })
                  : t("offer.acceptReady")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
