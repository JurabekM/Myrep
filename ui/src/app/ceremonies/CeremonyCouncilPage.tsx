import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type AdultConsentDto,
  type CeremoniesDto,
  type CeremonyDto,
  commands,
} from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import { Alert, Card, PageHeader, PrimaryButton, SecondaryButton } from "../finance/ui";
import { ComparisonTable } from "./CeremoniesPage";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const MIN_NOTE = 20;

type Step = "compare" | "consent" | "summary";
const STEPS: readonly Step[] = ["compare", "consent", "summary"];
const STEP_KEYS = {
  compare: "ceremonies.council.steps.compare",
  consent: "ceremonies.council.steps.consent",
  summary: "ceremonies.council.steps.summary",
} as const;

/** Mutatsiya natijasini marosimlar keshiga yozadi. */
function useCouncilAction() {
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);
  async function run(action: () => Promise<CeremoniesDto>): Promise<boolean> {
    setError(null);
    try {
      queryClient.setQueryData(financeKeys.ceremonies, await action());
      return true;
    } catch (caught) {
      setError(message(caught));
      return false;
    }
  }
  return { run, error };
}

/**
 * «Oila kengashi: buni qarzsiz qanday o'tkazamiz?» — to'liq ekranli sessiya (DESKTOP_PROMPT 7-bo'lim uslubi):
 * 1) stsenariylar yonma-yon, tanlov va qaror matni; 2) har bir katta o'z PIN'i bilan rozilik; 3) yakun va
 * bayonnoma PDF. Hamma katta rozi bo'lgach marosimda «muhokama o'tkazilgan» belgisi paydo bo'ladi (Rustda).
 */
export function CeremonyCouncilPage({
  ceremony,
  onClose,
}: {
  ceremony: CeremonyDto;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>(ceremony.discussion === null ? "compare" : "consent");
  const index = STEPS.indexOf(step);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("ceremonies.council.title")}
      className="fixed inset-0 z-50 overflow-y-auto bg-app p-8"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <PageHeader
            title={t("ceremonies.council.title")}
            subtitle={t("ceremonies.council.subtitle", { title: ceremony.title })}
          />
          <SecondaryButton onClick={onClose}>{t("family.close")}</SecondaryButton>
        </header>

        <ol className="flex flex-wrap gap-2 text-sm">
          {STEPS.map((key, position) => (
            <li
              key={key}
              aria-current={key === step ? "step" : undefined}
              className={
                key === step
                  ? "rounded-md border border-accent px-3 py-1 text-text"
                  : "rounded-md border border-border px-3 py-1 text-muted"
              }
            >
              {position + 1}. {t(STEP_KEYS[key])}
            </li>
          ))}
        </ol>

        {step === "compare" ? (
          <CompareStep
            ceremony={ceremony}
            onStarted={() => {
              setStep("consent");
            }}
          />
        ) : null}
        {step === "consent" ? <ConsentStep ceremony={ceremony} /> : null}
        {step === "summary" ? <SummaryStep ceremony={ceremony} onFinish={onClose} /> : null}

        <footer className="flex flex-wrap gap-2">
          {index > 0 ? (
            <SecondaryButton
              onClick={() => {
                setStep(STEPS[index - 1] ?? "compare");
              }}
            >
              {t("family.back")}
            </SecondaryButton>
          ) : null}
          {index < STEPS.length - 1 && ceremony.discussion !== null ? (
            <PrimaryButton
              onClick={() => {
                setStep(STEPS[index + 1] ?? "summary");
              }}
            >
              {t("family.next")}
            </PrimaryButton>
          ) : null}
        </footer>
      </div>
    </div>
  );
}

/** 1-qadam: stsenariylar taqqoslanadi, biri tanlanadi, qaror matni yoziladi. */
function CompareStep({ ceremony, onStarted }: { ceremony: CeremonyDto; onStarted: () => void }) {
  const { t } = useTranslation();
  const { run, error } = useCouncilAction();
  const current = ceremony.discussion;
  const [scenario, setScenario] = useState(current?.scenarioId ?? ceremony.scenarios[0]?.id ?? "");
  const [note, setNote] = useState(current?.note ?? "");
  const noteLength = note.trim().length;

  async function start(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await run(() =>
      commands
        .startCeremonyDiscussion({ ceremonyId: ceremony.id, scenarioId: scenario, note })
        .then(unwrap),
    );
    if (ok) {
      onStarted();
    }
  }

  return (
    <Card title={t("ceremonies.council.steps.compare")}>
      <p className="text-base text-text">{t("ceremonies.debtQuestion")}</p>
      <p className="text-sm text-muted">{t("ceremonies.council.compareHint")}</p>
      {ceremony.scenarios.length > 0 ? <ComparisonTable scenarios={ceremony.scenarios} /> : null}
      {current !== null ? (
        <p className="text-sm text-muted">
          {t("ceremonies.council.restartHint", { scenario: current.scenarioName })}
        </p>
      ) : null}
      <form className="flex flex-col gap-4" onSubmit={(event) => void start(event)}>
        <div className="flex flex-col gap-2">
          <label htmlFor="council-scenario" className="text-sm text-muted">
            {t("ceremonies.chooseScenario")}
          </label>
          <select
            id="council-scenario"
            className={SELECT_CLASS}
            value={scenario}
            onChange={(event) => {
              setScenario(event.currentTarget.value);
            }}
          >
            {ceremony.scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
                {s.hasDebt ? ` · ${t("ceremonies.funding.DEBT")}` : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="council-note" className="text-sm text-muted">
            {t("ceremonies.council.note")}
          </label>
          <textarea
            id="council-note"
            rows={4}
            className="rounded-lg border border-border bg-app px-3 py-2 text-base text-text outline-none focus:border-accent"
            placeholder={t("ceremonies.council.notePlaceholder")}
            value={note}
            onChange={(event) => {
              setNote(event.currentTarget.value);
            }}
          />
          <p className="text-xs text-subtle">
            {t("ceremonies.council.noteCount", { count: noteLength, min: MIN_NOTE })}
          </p>
        </div>
        <div>
          <PrimaryButton type="submit" disabled={scenario === "" || noteLength < MIN_NOTE}>
            {current === null ? t("ceremonies.council.start") : t("ceremonies.council.restart")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

/** 2-qadam: har bir katta a'zo o'z PIN'i bilan rozilik beradi. */
function ConsentStep({ ceremony }: { ceremony: CeremonyDto }) {
  const { t } = useTranslation();
  const discussion = ceremony.discussion;
  if (discussion === null) {
    return <p className="text-sm text-muted">{t("ceremonies.council.noDiscussion")}</p>;
  }
  const consentedCount = discussion.adults.filter((a) => a.consented).length;
  return (
    <Card title={t("ceremonies.council.steps.consent")}>
      <p className="text-base text-text">
        {t("ceremonies.council.decisionLine", { scenario: discussion.scenarioName })}
      </p>
      <p className="rounded-lg border border-border bg-app px-4 py-3 text-base text-text">
        {discussion.note}
      </p>
      <p className="text-sm text-muted">
        {t("ceremonies.council.consentHint", {
          done: consentedCount,
          total: discussion.adults.length,
        })}
      </p>
      <ul className="flex flex-col gap-3">
        {discussion.adults.map((adult) => (
          <AdultRow key={adult.memberId} ceremonyId={ceremony.id} adult={adult} />
        ))}
      </ul>
      {discussion.complete ? (
        <p className="text-sm text-success">{t("ceremonies.council.complete")}</p>
      ) : null}
    </Card>
  );
}

function AdultRow({ ceremonyId, adult }: { ceremonyId: string; adult: AdultConsentDto }) {
  const { t } = useTranslation();
  const { run, error } = useCouncilAction();
  const [pin, setPin] = useState("");

  async function consent(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    await run(() =>
      commands
        .consentCeremonyDiscussion({ ceremonyId, memberId: adult.memberId, pin })
        .then(unwrap),
    );
    // Natijadan qat'i nazar maydon tozalanadi: noto'g'ri PIN qayta teriladi, to'g'risi qolmaydi.
    setPin("");
  }

  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-base text-text">{adult.name}</span>
        <span className="text-xs text-muted">
          {adult.consented ? t("family.consented") : t("family.notConsented")}
        </span>
      </div>
      {adult.consented ? null : adult.hasPin ? (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(event) => void consent(event)}>
          <div className="flex flex-col gap-2">
            <label htmlFor={`council-pin-${adult.memberId}`} className="text-sm text-muted">
              {t("ceremonies.council.pinFor", { name: adult.name })}
            </label>
            <input
              id={`council-pin-${adult.memberId}`}
              type="password"
              inputMode="numeric"
              autoComplete="off"
              maxLength={6}
              className="h-10 w-40 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
              value={pin}
              onChange={(event) => {
                setPin(event.currentTarget.value.replace(/\D/g, "").slice(0, 6));
              }}
            />
          </div>
          <PrimaryButton type="submit" disabled={pin.length !== 6}>
            {t("family.consent")}
          </PrimaryButton>
        </form>
      ) : (
        <p className="text-sm text-muted">{t("ceremonies.council.noPin")}</p>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </li>
  );
}

/** 3-qadam: yakun — holat va bayonnoma PDF. */
function SummaryStep({ ceremony, onFinish }: { ceremony: CeremonyDto; onFinish: () => void }) {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const discussion = ceremony.discussion;

  async function createPdf() {
    setPdfError(null);
    try {
      setPdfPath(unwrap(await commands.createCeremonyMinutesPdf(ceremony.id)));
    } catch (caught) {
      setPdfError(message(caught));
    }
  }

  return (
    <Card title={t("ceremonies.council.steps.summary")}>
      {discussion !== null ? (
        <>
          <p className="text-base text-text">
            {discussion.complete
              ? t("ceremonies.council.summaryComplete")
              : t("ceremonies.council.summaryPending", {
                  done: discussion.adults.filter((a) => a.consented).length,
                  total: discussion.adults.length,
                })}
          </p>
          <p className="text-sm text-muted">
            {t("ceremonies.council.decisionLine", { scenario: discussion.scenarioName })} —{" "}
            {discussion.note}
          </p>
        </>
      ) : null}
      <div className="flex flex-col gap-2">
        <div>
          <SecondaryButton
            onClick={() => {
              void createPdf();
            }}
          >
            {t("ceremonies.council.minutesPdf")}
          </SecondaryButton>
        </div>
        {pdfPath !== null ? (
          <p className="text-sm text-text">{t("ceremonies.pdfSaved", { path: pdfPath })}</p>
        ) : null}
        {pdfError !== null ? <Alert>{pdfError}</Alert> : null}
      </div>
      <div>
        <PrimaryButton onClick={onFinish}>{t("family.finish")}</PrimaryButton>
      </div>
    </Card>
  );
}
