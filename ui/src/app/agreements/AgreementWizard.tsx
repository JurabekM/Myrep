import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Controller, type UseFormReturn, useFieldArray, useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { type AgreementDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, SecondaryButton } from "../finance/ui";
import { AgreementOpsCard } from "./AgreementOpsCard";
import { JournalCard } from "./JournalCard";
import { QUESTION_KEYS, kindKey, statusKey } from "./labels";
import { SignaturePad } from "./SignaturePad";
import { agreementFetchers, agreementKeys, useApplyAgreement } from "./queries";
import { type AnswersForm, answersSchema, nextId, toDto, toForm } from "./schema";

const QUESTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
type Question = (typeof QUESTIONS)[number];

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

/** Xato kodi → tarjima kaliti (to'liqlik xatolari). */
function completenessKey(code: string) {
  switch (code) {
    case "PARTIES_MIN_2":
      return "agreements.err.partiesMin2" as const;
    case "CONTRIBUTION_MISSING":
      return "agreements.err.contributionMissing" as const;
    case "DUTY_WITHOUT_OWNER":
      return "agreements.err.dutyWithoutOwner" as const;
    case "DUTY_WITHOUT_BREACH_CLAUSE":
      return "agreements.err.dutyWithoutBreach" as const;
    case "GUARANTEED_RETURN_FORBIDDEN":
      return "agreements.err.guaranteedReturn" as const;
    case "PROFIT_SHARES_NOT_100":
      return "agreements.err.sharesNot100" as const;
    case "ARBITER_IS_PARTY":
      return "agreements.err.arbiterIsParty" as const;
    case "NA_REASON_REQUIRED":
      return "agreements.err.naReasonRequired" as const;
    default:
      return "errors.generic" as const;
  }
}

/**
 * 9 savol ustasi (SPEC 2F.2, DESKTOP_PROMPT D8A): chapda progress «N / 9», o'rtada forma,
 * o'ngda maslahatchi fikri va jonli ko'rinish. 9/9 bo'lmasa «Imzolash» bosqichi ochilmaydi.
 * To'liqlik Rustda hisoblanadi; forma faqat qiymatlarni yig'adi.
 */
export function AgreementWizard({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useTranslation();
  const agreement = useQuery({
    queryKey: agreementKeys.one(id),
    queryFn: agreementFetchers.one(id),
  });

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  if (!agreement.isSuccess) {
    return (
      <div className="fixed inset-0 z-50 bg-app p-8">
        <p className="text-sm text-muted">{t("common.loading")}</p>
      </div>
    );
  }
  return <WizardBody agreement={agreement.data} onClose={onClose} />;
}

function WizardBody({ agreement, onClose }: { agreement: AgreementDto; onClose: () => void }) {
  const { t } = useTranslation();
  const apply = useApplyAgreement();
  const message = useErrorMessage();
  const [question, setQuestion] = useState<Question>(1);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedPath, setSavedPath] = useState<string | null>(null);
  const form = useForm<AnswersForm>({
    resolver: zodResolver(answersSchema),
    defaultValues: toForm(agreement.answers),
    mode: "onBlur",
  });
  const locked = agreement.status === "IN_DISPUTE" || agreement.status === "ENDED";
  const isLoan = agreement.kind === "LOAN";
  const missing = new Set(agreement.completeness.missing);

  async function save(): Promise<AgreementDto | null> {
    setError(null);
    const valid = await form.trigger();
    if (!valid) {
      setError(t("agreements.formInvalid"));
      return null;
    }
    try {
      const next = unwrap(
        await commands.saveAgreementAnswers({
          id: agreement.id,
          version: agreement.version,
          answers: toDto(form.getValues()),
        }),
      );
      await apply(next);
      form.reset(toForm(next.answers));
      return next;
    } catch (caught) {
      setError(message(caught));
      return null;
    }
  }

  async function createPdf() {
    setError(null);
    try {
      setSavedPath(unwrap(await commands.createAgreementPdf(agreement.id)));
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-app p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="agreement-title"
        className="mx-auto flex w-full max-w-6xl flex-col gap-6"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 id="agreement-title" className="text-2xl font-semibold text-text">
              {agreement.title}
            </h1>
            <p className="text-sm text-muted">
              {t(kindKey(agreement.kind))} · {t(statusKey(agreement.status))} ·{" "}
              {t("agreements.version", { version: agreement.version })}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <SecondaryButton
              onClick={() => {
                void createPdf();
              }}
            >
              {t("agreements.pdf")}
            </SecondaryButton>
            <SecondaryButton onClick={onClose}>{t("agreements.close")}</SecondaryButton>
          </div>
        </div>
        {savedPath !== null ? (
          <p className="text-sm text-muted">{t("agreements.pdfSaved", { path: savedPath })}</p>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[200px_minmax(0,1fr)_280px]">
          <aside className="flex flex-col gap-2">
            <p className="text-sm font-medium text-text">
              {t("agreements.progress", { done: 9 - missing.size })}
            </p>
            <ol className="flex flex-col gap-1">
              {QUESTIONS.map((q) => (
                <li key={q}>
                  <button
                    type="button"
                    aria-current={q === question ? "step" : undefined}
                    onClick={() => {
                      setQuestion(q);
                      setSigning(false);
                    }}
                    className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${
                      q === question ? "bg-raised text-text" : "text-muted hover:bg-raised"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className={`inline-flex size-5 items-center justify-center rounded-full border text-xs ${
                        missing.has(q) ? "border-border text-subtle" : "border-accent text-accent"
                      }`}
                    >
                      {missing.has(q) ? q : "✓"}
                    </span>
                    {t(QUESTION_KEYS[q].title)}
                  </button>
                </li>
              ))}
            </ol>
            <PrimaryButton
              disabled={!agreement.completeness.complete || locked}
              onClick={() => {
                setSigning(true);
              }}
            >
              {t("agreements.toSigning")}
            </PrimaryButton>
            {!agreement.completeness.complete ? (
              <p className="text-xs text-subtle">{t("agreements.signLocked")}</p>
            ) : null}
          </aside>

          <section className="flex min-w-0 flex-col gap-4">
            {signing ? (
              <SigningStep agreement={agreement} onError={setError} />
            ) : (
              <QuestionForm form={form} question={question} isLoan={isLoan} locked={locked} />
            )}
            {!signing ? (
              <div className="flex flex-wrap gap-2">
                <SecondaryButton
                  disabled={question === 1}
                  onClick={() => {
                    setQuestion((q) => (q > 1 ? ((q - 1) as Question) : q));
                  }}
                >
                  {t("agreements.back")}
                </SecondaryButton>
                <SecondaryButton
                  disabled={question === 9}
                  onClick={() => {
                    setQuestion((q) => (q < 9 ? ((q + 1) as Question) : q));
                  }}
                >
                  {t("agreements.next")}
                </SecondaryButton>
                <PrimaryButton
                  disabled={locked}
                  onClick={() => {
                    void save();
                  }}
                >
                  {t("agreements.save")}
                </PrimaryButton>
              </div>
            ) : null}
            {agreement.completeness.errors.length > 0 ? (
              <ul
                className="flex flex-col gap-1 text-sm text-danger"
                aria-label={t("agreements.errorsTitle")}
              >
                {agreement.completeness.errors.map((code) => (
                  <li key={code}>{t(completenessKey(code))}</li>
                ))}
              </ul>
            ) : null}
            {error !== null ? <Alert>{error}</Alert> : null}
            {agreement.status === "SIGNED" ? <JournalCard agreement={agreement} /> : null}
            {agreement.status !== "DRAFT" || agreement.kind === "FAMILY" ? (
              <AgreementOpsCard agreement={agreement} />
            ) : null}
          </section>

          <aside className="flex flex-col gap-4">
            <Card title={t("agreements.adviceTitle")}>
              <p className="text-sm text-muted">{t(QUESTION_KEYS[question].advice)}</p>
            </Card>
            <Preview form={form} agreement={agreement} />
          </aside>
        </div>
      </div>
    </div>
  );
}

function QuestionForm({
  form,
  question,
  isLoan,
  locked,
}: {
  form: UseFormReturn<AnswersForm>;
  question: Question;
  isLoan: boolean;
  locked: boolean;
}) {
  const { t } = useTranslation();
  const { register, control } = form;
  const parties = useFieldArray({ control, name: "parties" });
  const contributions = useFieldArray({ control, name: "contributions" });
  const duties = useFieldArray({ control, name: "duties" });
  const shares = useFieldArray({ control, name: "profitShares" });
  const partyValues = useWatch({ control, name: "parties" });
  const partyOptions = partyValues.map((p) => ({ id: p.id, name: p.name === "" ? p.id : p.name }));

  const title = t(QUESTION_KEYS[question].title);
  const hint = t(QUESTION_KEYS[question].hint);

  return (
    <Card title={`${String(question)}. ${title}`}>
      <p className="text-sm text-muted">{hint}</p>
      <fieldset disabled={locked} className="flex flex-col gap-4">
        {question === 1 ? (
          <>
            {parties.fields.map((field, index) => (
              <div
                key={field.id}
                className="grid gap-3 rounded-lg border border-border p-3 sm:grid-cols-2"
              >
                <Field
                  id={`party-name-${field.id}`}
                  label={t("agreements.partyName")}
                  {...register(`parties.${index}.name`)}
                />
                <Field
                  id={`party-role-${field.id}`}
                  label={t("agreements.partyRole")}
                  {...register(`parties.${index}.role`)}
                />
                <Field
                  id={`party-relation-${field.id}`}
                  label={t("agreements.partyRelation")}
                  {...register(`parties.${index}.relation`)}
                />
                <label className="flex items-center gap-2 text-sm text-muted">
                  <input type="checkbox" {...register(`parties.${index}.isMe`)} />
                  {t("agreements.partyIsMe")}
                </label>
                <div>
                  <SecondaryButton
                    onClick={() => {
                      parties.remove(index);
                    }}
                  >
                    {t("agreements.remove")}
                  </SecondaryButton>
                </div>
              </div>
            ))}
            <div>
              <SecondaryButton
                onClick={() => {
                  parties.append({
                    id: nextId("P", form.getValues("parties")),
                    name: "",
                    role: "",
                    relation: "",
                    isMe: form.getValues("parties").length === 0,
                  });
                }}
              >
                {t("agreements.addParty")}
              </SecondaryButton>
            </div>
          </>
        ) : null}

        {question === 2 ? (
          <>
            {contributions.fields.map((field, index) => (
              <div
                key={field.id}
                className="grid gap-3 rounded-lg border border-border p-3 sm:grid-cols-2"
              >
                <PartySelect
                  id={`contrib-party-${field.id}`}
                  label={t("agreements.party")}
                  options={partyOptions}
                  {...register(`contributions.${index}.partyId`)}
                />
                <div className="flex flex-col gap-2">
                  <label htmlFor={`contrib-kind-${field.id}`} className="text-sm text-muted">
                    {t("agreements.contributionKind")}
                  </label>
                  <select
                    id={`contrib-kind-${field.id}`}
                    className={SELECT_CLASS}
                    {...register(`contributions.${index}.kind`)}
                  >
                    <option value="money">{t("agreements.kindMoney")}</option>
                    <option value="goods">{t("agreements.kindGoods")}</option>
                    <option value="labor">{t("agreements.kindLabor")}</option>
                    <option value="connections">{t("agreements.kindConnections")}</option>
                  </select>
                </div>
                <Field
                  id={`contrib-amount-${field.id}`}
                  label={t("agreements.contributionAmount")}
                  inputMode="numeric"
                  {...register(`contributions.${index}.amount`)}
                />
                <Field
                  id={`contrib-desc-${field.id}`}
                  label={t("agreements.contributionDescription")}
                  {...register(`contributions.${index}.description`)}
                />
                <div>
                  <SecondaryButton
                    onClick={() => {
                      contributions.remove(index);
                    }}
                  >
                    {t("agreements.remove")}
                  </SecondaryButton>
                </div>
              </div>
            ))}
            <div>
              <SecondaryButton
                onClick={() => {
                  contributions.append({
                    partyId: partyOptions[0]?.id ?? "",
                    kind: "money",
                    amount: "",
                    description: "",
                  });
                }}
              >
                {t("agreements.addContribution")}
              </SecondaryButton>
            </div>
          </>
        ) : null}

        {question === 3 ? (
          isLoan ? (
            <label className="flex items-center gap-2 text-sm text-text">
              <input type="checkbox" {...register("hasSchedule")} />
              {t("agreements.hasSchedule")}
            </label>
          ) : (
            <>
              {duties.fields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid gap-3 rounded-lg border border-border p-3 sm:grid-cols-2"
                >
                  <Field
                    id={`duty-title-${field.id}`}
                    label={t("agreements.dutyTitle")}
                    {...register(`duties.${index}.title`)}
                  />
                  <PartySelect
                    id={`duty-owner-${field.id}`}
                    label={t("agreements.dutyOwner")}
                    options={partyOptions}
                    allowEmpty={t("agreements.dutyNoOwner")}
                    {...register(`duties.${index}.ownerPartyId`)}
                  />
                  <div className="sm:col-span-2">
                    <Field
                      id={`duty-breach-${field.id}`}
                      label={t("agreements.dutyBreach")}
                      {...register(`duties.${index}.breachClause`)}
                    />
                  </div>
                  <div>
                    <SecondaryButton
                      onClick={() => {
                        duties.remove(index);
                      }}
                    >
                      {t("agreements.remove")}
                    </SecondaryButton>
                  </div>
                </div>
              ))}
              <div>
                <SecondaryButton
                  onClick={() => {
                    duties.append({
                      id: nextId("d", form.getValues("duties")),
                      title: "",
                      ownerPartyId: "",
                      breachClause: "",
                    });
                  }}
                >
                  {t("agreements.addDuty")}
                </SecondaryButton>
              </div>
            </>
          )
        ) : null}

        {question === 4 ? (
          isLoan ? (
            <p className="text-sm text-text">{t("agreements.loanNoInterest")}</p>
          ) : (
            <>
              <NaToggle form={form} flag="profitNotApplicable" reason="profitNaReason" />
              {shares.fields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid gap-3 rounded-lg border border-border p-3 sm:grid-cols-2"
                >
                  <PartySelect
                    id={`share-party-${field.id}`}
                    label={t("agreements.party")}
                    options={partyOptions}
                    {...register(`profitShares.${index}.partyId`)}
                  />
                  <Field
                    id={`share-bp-${field.id}`}
                    label={t("agreements.shareBp")}
                    type="number"
                    {...register(`profitShares.${index}.shareBp`, { valueAsNumber: true })}
                  />
                  <div>
                    <SecondaryButton
                      onClick={() => {
                        shares.remove(index);
                      }}
                    >
                      {t("agreements.remove")}
                    </SecondaryButton>
                  </div>
                </div>
              ))}
              <div>
                <SecondaryButton
                  onClick={() => {
                    shares.append({ partyId: partyOptions[0]?.id ?? "", shareBp: 5000 });
                  }}
                >
                  {t("agreements.addShare")}
                </SecondaryButton>
              </div>
              <p className="text-xs text-subtle">{t("agreements.fixedForbidden")}</p>
            </>
          )
        ) : null}

        {question === 5 ? (
          isLoan ? (
            <p className="text-sm text-text">{t("agreements.loanNoInterest")}</p>
          ) : (
            <>
              <NaToggle form={form} flag="lossNotApplicable" reason="lossNaReason" />
              <Field id="loss-text" label={t("agreements.lossText")} {...register("lossText")} />
            </>
          )
        ) : null}

        {question === 6 ? (
          <>
            <Field
              id="custody-location"
              label={t("agreements.custodyLocation")}
              {...register("custodyLocation")}
            />
            <PartySelect
              id="custody-keeper"
              label={t("agreements.keeper")}
              options={partyOptions}
              allowEmpty="—"
              {...register("keeperPartyId")}
            />
            <Field
              id="custody-review"
              label={t("agreements.reviewEveryDays")}
              type="number"
              {...register("reviewEveryDays", { valueAsNumber: true })}
            />
          </>
        ) : null}

        {question === 7 ? (
          <>
            <NaToggle form={form} flag="exitNotApplicable" reason="exitNaReason" />
            <Field
              id="exit-notice"
              label={t("agreements.exitNotice")}
              type="number"
              {...register("exitNoticeDays", { valueAsNumber: true })}
            />
            <Field
              id="exit-valuation"
              label={t("agreements.exitValuation")}
              {...register("exitValuation")}
            />
            <Field
              id="exit-payout"
              label={t("agreements.exitPayout")}
              {...register("exitPayout")}
            />
            <Field
              id="exit-assets"
              label={t("agreements.exitAssets")}
              {...register("exitAssets")}
            />
          </>
        ) : null}

        {question === 8 ? (
          <>
            <Field
              id="arbiter-name"
              label={t("agreements.arbiterName")}
              {...register("arbiterName")}
            />
            <Field
              id="arbiter-role"
              label={t("agreements.arbiterRole")}
              {...register("arbiterRole")}
            />
          </>
        ) : null}

        {question === 9 ? (
          <>
            <Field
              id="term-months"
              label={t("agreements.termMonths")}
              type="number"
              {...register("termMonths", { valueAsNumber: true })}
            />
            <Field
              id="review-date"
              label={t("agreements.reviewDate")}
              type="date"
              {...register("reviewDate")}
            />
          </>
        ) : null}
      </fieldset>
    </Card>
  );
}

function NaToggle({
  form,
  flag,
  reason,
}: {
  form: UseFormReturn<AnswersForm>;
  flag: "profitNotApplicable" | "lossNotApplicable" | "exitNotApplicable";
  reason: "profitNaReason" | "lossNaReason" | "exitNaReason";
}) {
  const { t } = useTranslation();
  const checked = useWatch({ control: form.control, name: flag });
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <label className="flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" {...form.register(flag)} />
        {t("agreements.notApplicable")}
      </label>
      {checked ? (
        <Field id={`na-${reason}`} label={t("agreements.naReason")} {...form.register(reason)} />
      ) : null}
    </div>
  );
}

function PartySelect({
  id,
  label,
  options,
  allowEmpty,
  ...select
}: {
  id: string;
  label: string;
  options: readonly { id: string; name: string }[];
  allowEmpty?: string;
} & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm text-muted">
        {label}
      </label>
      <select id={id} className={SELECT_CLASS} {...select}>
        {allowEmpty !== undefined ? <option value="">{allowEmpty}</option> : null}
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Bo'sh yoki yo'q qiymat — «—». */
function show(value: string | undefined): string {
  return value === undefined || value === "" ? "—" : value;
}

function num(value: number | undefined): string {
  return value === undefined ? "—" : String(value);
}

/** Jonli ko'rinish: hujjatning matnli oynasi (PDF bilan bir xil ma'lumot; PDF'ning o'zi «PDF» tugmasida). */
function Preview({
  form,
  agreement,
}: {
  form: UseFormReturn<AnswersForm>;
  agreement: AgreementDto;
}) {
  const { t } = useTranslation();
  const values = useWatch({ control: form.control });
  const parties = values.parties ?? [];
  const nameOf = (id: string | undefined): string => {
    const found = parties.find((p) => p.id === id);
    return show(found === undefined ? id : found.name);
  };
  const na = (reason: string | undefined) => `${t("agreements.notApplicable")}: ${show(reason)}`;
  const line = (items: string[]) => (items.length === 0 ? "—" : items.join("; "));
  return (
    <Card title={t("agreements.previewTitle")}>
      <div className="flex flex-col gap-2 text-sm">
        <p className="font-semibold text-text">{agreement.title}</p>
        <p className="text-muted">
          1. {line(parties.map((p) => `${show(p.name)} (${show(p.role)})`))}
        </p>
        <p className="text-muted">
          2.{" "}
          {line(
            (values.contributions ?? []).map(
              (c) =>
                `${nameOf(c.partyId)}: ${show(c.kind)} ${show(c.amount)} ${show(c.description)}`,
            ),
          )}
        </p>
        <p className="text-muted">
          3.{" "}
          {values.hasSchedule === true
            ? t("agreements.hasSchedule")
            : line(
                (values.duties ?? []).map((d) => `${show(d.title)} — ${nameOf(d.ownerPartyId)}`),
              )}
        </p>
        <p className="text-muted">
          4.{" "}
          {values.profitNotApplicable === true
            ? na(values.profitNaReason)
            : line(
                (values.profitShares ?? []).map((s) => `${nameOf(s.partyId)} ${num(s.shareBp)} bp`),
              )}
        </p>
        <p className="text-muted">
          5. {values.lossNotApplicable === true ? na(values.lossNaReason) : show(values.lossText)}
        </p>
        <p className="text-muted">
          6. {show(values.custodyLocation)} · {nameOf(values.keeperPartyId)} ·{" "}
          {num(values.reviewEveryDays)} {t("agreements.days")}
        </p>
        <p className="text-muted">
          7.{" "}
          {values.exitNotApplicable === true
            ? na(values.exitNaReason)
            : `${num(values.exitNoticeDays)} ${t("agreements.days")} · ${show(values.exitValuation)} · ${show(values.exitPayout)}`}
        </p>
        <p className="text-muted">
          8. {show(values.arbiterName)}{" "}
          {values.arbiterRole === undefined || values.arbiterRole === ""
            ? ""
            : `(${values.arbiterRole})`}
        </p>
        <p className="text-muted">
          9. {num(values.termMonths)} {t("agreements.months")} · {show(values.reviewDate)}
        </p>
      </div>
    </Card>
  );
}

/** Imzolash bosqichi: har tomon (va hakam) uchun imzo, so'ng yakunlash (og'zaki kelishuv sanasi bilan). */
function SigningStep({
  agreement,
  onError,
}: {
  agreement: AgreementDto;
  onError: (value: string | null) => void;
}) {
  const { t } = useTranslation();
  const apply = useApplyAgreement();
  const message = useErrorMessage();
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [openingParty, setOpeningParty] = useState("");
  const [openingAmount, setOpeningAmount] = useState("");
  const signers = [
    ...agreement.answers.parties.map((p) => ({
      id: p.id,
      role: "PARTY",
      label: `${p.name} (${t("agreements.roleParty")})`,
    })),
    ...(agreement.answers.arbiterName.trim() !== ""
      ? [
          {
            id: "ARBITER",
            role: "ARBITER",
            label: `${agreement.answers.arbiterName} (${t("agreements.roleArbiter")})`,
          },
        ]
      : []),
  ];
  const signed = new Set(agreement.signatures.map((s) => `${s.partyId}:${s.role}`));

  async function run(action: () => Promise<AgreementDto>) {
    onError(null);
    try {
      await apply(await action());
    } catch (caught) {
      onError(message(caught));
    }
  }

  return (
    <Card title={t("agreements.signingTitle")}>
      <p className="text-sm text-muted">{t("agreements.signingHint")}</p>
      {signers.map((signer) =>
        signed.has(`${signer.id}:${signer.role}`) ? (
          <p key={signer.id} className="text-sm text-text">
            ✓ {signer.label} — {t("agreements.signed")}
          </p>
        ) : (
          <SignaturePad
            key={signer.id}
            label={signer.label}
            onSave={(image) => {
              void run(() =>
                commands
                  .addSignature({
                    agreementId: agreement.id,
                    partyId: signer.id,
                    role: signer.role,
                    image,
                  })
                  .then(unwrap),
              );
            }}
          />
        ),
      )}
      {agreement.status !== "SIGNED" ? (
        <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
          <p className="text-sm font-medium text-text">{t("agreements.oralTitle")}</p>
          <p className="text-xs text-subtle">{t("agreements.oralHint")}</p>
          <Field
            id="effective-from"
            type="date"
            label={t("agreements.effectiveFrom")}
            value={effectiveFrom}
            onChange={(event) => {
              setEffectiveFrom(event.currentTarget.value);
            }}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label htmlFor="opening-party" className="text-sm text-muted">
                {t("agreements.openingParty")}
              </label>
              <select
                id="opening-party"
                className={SELECT_CLASS}
                value={openingParty}
                onChange={(event) => {
                  setOpeningParty(event.currentTarget.value);
                }}
              >
                <option value="">—</option>
                {agreement.answers.parties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <Field
              id="opening-amount"
              label={t("agreements.openingAmount")}
              inputMode="numeric"
              value={openingAmount}
              onChange={(event) => {
                setOpeningAmount(event.currentTarget.value);
              }}
            />
          </div>
          <div>
            <PrimaryButton
              disabled={signers.some((s) => !signed.has(`${s.id}:${s.role}`))}
              onClick={() => {
                void run(() =>
                  commands
                    .signAgreement({
                      agreementId: agreement.id,
                      effectiveFrom: effectiveFrom === "" ? null : effectiveFrom,
                      openingBalancePartyId: openingParty === "" ? null : openingParty,
                      openingBalanceAmount: openingAmount.trim() === "" ? null : openingAmount,
                    })
                    .then(unwrap),
                );
              }}
            >
              {t("agreements.finishSigning")}
            </PrimaryButton>
          </div>
        </div>
      ) : (
        <p className="text-sm text-text">
          {t("agreements.signedSince", { date: agreement.effectiveFrom ?? "—" })}
        </p>
      )}
    </Card>
  );
}

export { Controller };
