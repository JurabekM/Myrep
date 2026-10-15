import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type AgreementDto,
  type AgreementOpsDto,
  type ReviewDto,
  commands,
} from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, SecondaryButton } from "../finance/ui";
import { journalKindKey } from "./labels";
import { agreementKeys } from "./queries";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

function useOps(agreement: AgreementDto) {
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(
    async (action: () => Promise<AgreementOpsDto>): Promise<boolean> => {
      setError(null);
      try {
        queryClient.setQueryData(agreementKeys.ops(agreement.id), await action());
        await queryClient.invalidateQueries({ queryKey: agreementKeys.one(agreement.id) });
        await queryClient.invalidateQueries({ queryKey: agreementKeys.center });
        return true;
      } catch (caught) {
        setError(message(caught));
        return false;
      }
    },
    [queryClient, message, agreement.id],
  );
  return { run, error };
}

/**
 * Kelishuv amaliyotlari (SPEC 2F.4, 2F.5, 2F.8, 2F.10; D13A): vazifa hodisalari, oylik ochiq hisob ko'rigi
 * (to'liq ekran sessiya, belgilar, bayonnoma PDF), nizo va hakam (ish papkasi PDF, qaror), yillik yangilash,
 * oilaviy kelishuvda ADULT PIN tasdig'i. Qoidalar Rustda; bu yerda faqat ko'rsatish.
 */
export function AgreementOpsCard({ agreement }: { agreement: AgreementDto }) {
  const { t } = useTranslation();
  const ops = useQuery({
    queryKey: agreementKeys.ops(agreement.id),
    queryFn: () => commands.getAgreementOps(agreement.id).then(unwrap),
  });
  const [session, setSession] = useState<string | null>(null);

  if (!ops.isSuccess) {
    return ops.isError ? <Alert>{t("errors.generic")}</Alert> : null;
  }
  const data = ops.data;
  const openReview = data.reviews.find((r) => r.id === session);

  return (
    <>
      {data.family !== null ? <FamilySection agreement={agreement} ops={data} /> : null}
      {data.status !== "DRAFT" ? (
        <>
          <IncidentsSection agreement={agreement} ops={data} />
          <ReviewsSection
            agreement={agreement}
            ops={data}
            onOpenSession={(id) => {
              setSession(id);
            }}
          />
          <DisputesSection agreement={agreement} ops={data} />
        </>
      ) : null}
      <RenewalSection agreement={agreement} ops={data} />
      {openReview !== undefined ? (
        <ReviewSession
          agreement={agreement}
          review={openReview}
          onClose={() => {
            setSession(null);
          }}
        />
      ) : null}
    </>
  );
}

function FamilySection({ agreement, ops }: { agreement: AgreementDto; ops: AgreementOpsDto }) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  const [member, setMember] = useState(ops.family?.adults[0]?.memberId ?? "");
  const [pin, setPin] = useState("");
  if (ops.family === null) {
    return null;
  }
  return (
    <Card title={t("ops.familyTitle")}>
      <p className="text-sm text-muted">{t("ops.familyHint")}</p>
      <ul className="flex flex-col gap-1 text-sm text-text">
        {ops.family.adults.map((adult) => (
          <li key={adult.memberId}>
            {adult.name} —{" "}
            {adult.confirmed
              ? t("ops.familyConfirmed")
              : adult.hasPin
                ? t("ops.familyPending")
                : t("ops.familyNoPin")}
          </li>
        ))}
      </ul>
      {ops.family.complete ? (
        <p className="text-sm text-success">{t("ops.familyComplete")}</p>
      ) : (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
            event.preventDefault();
            void run(() =>
              commands
                .confirmFamily({ agreementId: agreement.id, memberId: member, pin })
                .then(unwrap),
            ).then(() => {
              setPin("");
            });
          }}
        >
          <div className="flex flex-col gap-2">
            <label htmlFor="family-member" className="text-sm text-muted">
              {t("ops.familyMember")}
            </label>
            <select
              id="family-member"
              className={SELECT_CLASS}
              value={member}
              onChange={(event) => {
                setMember(event.currentTarget.value);
              }}
            >
              {ops.family.adults
                .filter((a) => !a.confirmed)
                .map((a) => (
                  <option key={a.memberId} value={a.memberId}>
                    {a.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="w-40">
            <Field
              id="family-pin"
              label={t("ops.familyPin")}
              type="password"
              inputMode="numeric"
              maxLength={6}
              autoComplete="off"
              value={pin}
              onChange={(event) => {
                setPin(event.currentTarget.value.replace(/\D/g, "").slice(0, 6));
              }}
            />
          </div>
          <PrimaryButton type="submit" disabled={pin.length !== 6 || member === ""}>
            {t("ops.familyConfirm")}
          </PrimaryButton>
        </form>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

function IncidentsSection({ agreement, ops }: { agreement: AgreementDto; ops: AgreementOpsDto }) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  const [duty, setDuty] = useState(agreement.answers.duties[0]?.id ?? "");
  const [party, setParty] = useState(agreement.answers.parties[0]?.id ?? "");
  const [reason, setReason] = useState("");
  const [fix, setFix] = useState("");
  const selected = agreement.answers.duties.find((d) => d.id === duty);

  return (
    <Card title={t("ops.incidentsTitle")}>
      <p className="text-sm text-muted">{t("ops.incidentsHint")}</p>
      {selected !== undefined ? (
        <p className="rounded-lg border border-border bg-app px-3 py-2 text-sm text-text">
          {t("ops.clauseLine", { title: selected.title, clause: selected.breachClause })}
        </p>
      ) : null}
      <form
        className="grid gap-3 sm:grid-cols-5"
        onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
          event.preventDefault();
          void run(() =>
            commands
              .reportDutyIncident({
                agreementId: agreement.id,
                dutyId: duty,
                partyId: party,
                reason,
                proposedFix: fix.trim() === "" ? null : fix,
                occurredOn: null,
              })
              .then(unwrap),
          ).then((ok) => {
            if (ok) {
              setReason("");
              setFix("");
            }
          });
        }}
      >
        <div className="flex flex-col gap-2">
          <label htmlFor="incident-duty" className="text-sm text-muted">
            {t("ops.incidentDuty")}
          </label>
          <select
            id="incident-duty"
            className={SELECT_CLASS}
            value={duty}
            onChange={(event) => {
              setDuty(event.currentTarget.value);
            }}
          >
            {agreement.answers.duties.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="incident-party" className="text-sm text-muted">
            {t("ops.incidentParty")}
          </label>
          <select
            id="incident-party"
            className={SELECT_CLASS}
            value={party}
            onChange={(event) => {
              setParty(event.currentTarget.value);
            }}
          >
            {agreement.answers.parties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <Field
          id="incident-reason"
          label={t("ops.incidentReason")}
          value={reason}
          onChange={(event) => {
            setReason(event.currentTarget.value);
          }}
        />
        <Field
          id="incident-fix"
          label={t("ops.incidentFix")}
          value={fix}
          onChange={(event) => {
            setFix(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={reason.trim() === "" || duty === ""}>
            {t("ops.incidentReport")}
          </PrimaryButton>
        </div>
      </form>
      {ops.incidents.length === 0 ? (
        <p className="text-sm text-muted">{t("ops.noIncidents")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {ops.incidents.map((incident) => (
            <li
              key={incident.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-app px-3 py-2 text-sm"
            >
              <span className="flex flex-col gap-1 text-text">
                <span>
                  {incident.occurredOn} · {incident.dutyTitle} · {incident.partyName}
                  {incident.resolved ? ` · ${t("ops.incidentResolved")}` : ""}
                </span>
                <span className="text-xs text-subtle">
                  {incident.reason}
                  {incident.proposedFix !== null ? ` → ${incident.proposedFix}` : ""} ·{" "}
                  {t("ops.clauseShort", { clause: incident.breachClause })}
                </span>
              </span>
              {!incident.resolved ? (
                <SecondaryButton
                  className="h-8 px-2 text-xs"
                  onClick={() => {
                    void run(() => commands.resolveDutyIncident(incident.id).then(unwrap));
                  }}
                >
                  {t("ops.incidentResolve")}
                </SecondaryButton>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

function ReviewsSection({
  agreement,
  ops,
  onOpenSession,
}: {
  agreement: AgreementDto;
  ops: AgreementOpsDto;
  onOpenSession: (id: string) => void;
}) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  return (
    <Card title={t("ops.reviewsTitle")}>
      <p className="text-sm text-muted">{t("ops.reviewsHint")}</p>
      <div>
        <PrimaryButton
          onClick={() => {
            void run(() =>
              commands
                .openReview({ agreementId: agreement.id, periodStart: null, periodEnd: null })
                .then(unwrap),
            ).then((ok) => {
              if (ok) {
                onOpenSession("latest");
              }
            });
          }}
        >
          {t("ops.reviewOpen")}
        </PrimaryButton>
      </div>
      {ops.reviews.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {ops.reviews.map((review) => (
            <li
              key={review.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-app px-3 py-2 text-sm text-text"
            >
              <span>
                {review.periodStart} — {review.periodEnd} ·{" "}
                {review.complete ? t("ops.reviewComplete") : t("ops.reviewPending")} ·{" "}
                {review.chainOk ? t("center.chainOk") : t("center.chainBroken")}
              </span>
              <SecondaryButton
                className="h-8 px-2 text-xs"
                onClick={() => {
                  onOpenSession(review.id);
                }}
              >
                {t("ops.reviewSession")}
              </SecondaryButton>
            </li>
          ))}
        </ul>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

/** To'liq ekran ko'rik sessiyasi (oila kengashi uslubi): yozuvlar, yakun, hodisalar, zanjir, belgilar, PDF. */
function ReviewSession({
  agreement,
  review,
  onClose,
}: {
  agreement: AgreementDto;
  review: ReviewDto;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  const message = useErrorMessage();
  const [comments, setComments] = useState<Record<string, string>>({});
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const nameOf = (id: string) => agreement.answers.parties.find((p) => p.id === id)?.name ?? id;

  async function createPdf() {
    setPdfError(null);
    try {
      setPdfPath(unwrap(await commands.createReviewPdf(review.id)));
    } catch (caught) {
      setPdfError(message(caught));
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("ops.sessionTitle")}
      className="fixed inset-0 z-50 overflow-y-auto bg-app p-8"
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-text">
            {t("ops.sessionTitle")} · {review.periodStart} — {review.periodEnd}
          </h1>
          <SecondaryButton onClick={onClose}>{t("agreements.close")}</SecondaryButton>
        </div>
        <p className={`text-sm ${review.chainOk ? "text-muted" : "text-danger"}`}>
          {review.chainOk ? t("ops.sessionChainOk") : t("ops.sessionChainBroken")} ·{" "}
          {review.chainHead.slice(0, 16)}…
        </p>
        <Card title={t("ops.sessionEntries")}>
          {review.entries.length === 0 ? (
            <p className="text-sm text-muted">{t("ops.sessionNoEntries")}</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-text">
              {review.entries.map((entry) => (
                <li key={entry.seq} className="flex flex-wrap justify-between gap-2">
                  <span>
                    {entry.date} · {t(journalKindKey(entry.kind))} · {nameOf(entry.partyId)}
                  </span>
                  <span>{entry.amount.formatted}</span>
                </li>
              ))}
            </ul>
          )}
          {review.summary.length > 0 ? (
            <ul className="flex flex-col gap-1 border-t border-border pt-2 text-sm text-text">
              {review.summary.map((line) => (
                <li key={line.label} className="flex justify-between">
                  <span>{line.label}</span>
                  <span className="font-medium">{line.amount.formatted}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </Card>
        {review.incidents.length > 0 ? (
          <Card title={t("ops.sessionIncidents")}>
            <ul className="flex flex-col gap-1 text-sm text-text">
              {review.incidents.map((incident) => (
                <li key={incident.id}>
                  {incident.dutyTitle} · {incident.reason} ·{" "}
                  {t("ops.clauseShort", { clause: incident.breachClause })}
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
        <Card title={t("ops.sessionMarks")}>
          <ul className="flex flex-col gap-3">
            {review.marks.map((mark) => (
              <li
                key={mark.partyId}
                className="flex flex-col gap-2 rounded-lg border border-border bg-app px-3 py-2 text-sm"
              >
                <span className="text-text">
                  {mark.name} —{" "}
                  {mark.decision === "AGREE"
                    ? t("ops.markAgree")
                    : mark.decision === "OBJECT"
                      ? t("ops.markObjectLine", { comment: mark.comment ?? "" })
                      : t("ops.markNone")}
                </span>
                {mark.decision === null ? (
                  <div className="flex flex-wrap items-end gap-2">
                    <PrimaryButton
                      onClick={() => {
                        void run(() =>
                          commands
                            .markReview({
                              reviewId: review.id,
                              partyId: mark.partyId,
                              decision: "AGREE",
                              comment: null,
                            })
                            .then(unwrap),
                        );
                      }}
                    >
                      {t("ops.markAgreeButton")}
                    </PrimaryButton>
                    <div className="w-64">
                      <Field
                        id={`objection-${mark.partyId}`}
                        label={t("ops.markComment")}
                        value={comments[mark.partyId] ?? ""}
                        onChange={(event) => {
                          const value = event.currentTarget.value;
                          setComments((current) => ({ ...current, [mark.partyId]: value }));
                        }}
                      />
                    </div>
                    <SecondaryButton
                      disabled={(comments[mark.partyId] ?? "").trim() === ""}
                      onClick={() => {
                        void run(() =>
                          commands
                            .markReview({
                              reviewId: review.id,
                              partyId: mark.partyId,
                              decision: "OBJECT",
                              comment: comments[mark.partyId] ?? "",
                            })
                            .then(unwrap),
                        );
                      }}
                    >
                      {t("ops.markObjectButton")}
                    </SecondaryButton>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
        <div className="flex flex-wrap items-center gap-2">
          <PrimaryButton
            onClick={() => {
              void createPdf();
            }}
          >
            {t("ops.sessionPdf")}
          </PrimaryButton>
          {pdfPath !== null ? (
            <span className="text-xs text-subtle">
              {t("agreements.pdfSaved", { path: pdfPath })}
            </span>
          ) : null}
        </div>
        {error !== null ? <Alert>{error}</Alert> : null}
        {pdfError !== null ? <Alert>{pdfError}</Alert> : null}
      </div>
    </div>
  );
}

function DisputesSection({ agreement, ops }: { agreement: AgreementDto; ops: AgreementOpsDto }) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  const message = useErrorMessage();
  const [party, setParty] = useState(agreement.answers.parties[0]?.id ?? "");
  const [subject, setSubject] = useState("");
  const [clauses, setClauses] = useState("");
  const [claim, setClaim] = useState("");
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [newVersion, setNewVersion] = useState(false);
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  async function arbiterPdf() {
    setPdfError(null);
    try {
      setPdfPath(unwrap(await commands.createArbiterPdf(agreement.id)));
    } catch (caught) {
      setPdfError(message(caught));
    }
  }

  return (
    <Card title={t("ops.disputesTitle")}>
      <p className="text-sm text-muted">{t("ops.disputesHint")}</p>
      {ops.status === "IN_DISPUTE" ? (
        <p className="rounded-lg border border-danger/40 px-3 py-2 text-sm text-danger">
          {t("ops.inDispute")}
        </p>
      ) : null}
      {ops.status === "SIGNED" ? (
        <form
          className="grid gap-3 sm:grid-cols-5"
          onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
            event.preventDefault();
            void run(() =>
              commands
                .openDispute({ agreementId: agreement.id, partyId: party, subject, clauses, claim })
                .then(unwrap),
            ).then((ok) => {
              if (ok) {
                setSubject("");
                setClauses("");
                setClaim("");
              }
            });
          }}
        >
          <div className="flex flex-col gap-2">
            <label htmlFor="dispute-party" className="text-sm text-muted">
              {t("ops.disputeParty")}
            </label>
            <select
              id="dispute-party"
              className={SELECT_CLASS}
              value={party}
              onChange={(event) => {
                setParty(event.currentTarget.value);
              }}
            >
              {agreement.answers.parties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <Field
            id="dispute-subject"
            label={t("ops.disputeSubject")}
            value={subject}
            onChange={(event) => {
              setSubject(event.currentTarget.value);
            }}
          />
          <Field
            id="dispute-clauses"
            label={t("ops.disputeClauses")}
            value={clauses}
            onChange={(event) => {
              setClauses(event.currentTarget.value);
            }}
          />
          <Field
            id="dispute-claim"
            label={t("ops.disputeClaim")}
            value={claim}
            onChange={(event) => {
              setClaim(event.currentTarget.value);
            }}
          />
          <div className="flex items-end">
            <SecondaryButton type="submit" disabled={subject.trim() === "" || claim.trim() === ""}>
              {t("ops.disputeOpen")}
            </SecondaryButton>
          </div>
        </form>
      ) : null}
      {ops.disputes.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {ops.disputes.map((dispute) => (
            <li
              key={dispute.id}
              className="flex flex-col gap-2 rounded-lg border border-border bg-app px-3 py-2 text-sm"
            >
              <span className="text-text">
                {dispute.openedOn} · {dispute.subject} · {dispute.openedByName}
              </span>
              <span className="text-xs text-subtle">
                {t("ops.disputeClausesLine", { clauses: dispute.clauses })} ·{" "}
                {t("ops.disputeClaimLine", { claim: dispute.claim })}
              </span>
              {dispute.decision !== null ? (
                <span className="text-sm text-success">
                  {t("ops.disputeDecided", {
                    decision: dispute.decision,
                    date: dispute.decidedOn ?? "",
                  })}
                </span>
              ) : (
                <form
                  className="flex flex-wrap items-end gap-2"
                  onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
                    event.preventDefault();
                    void run(() =>
                      commands
                        .decideDispute({
                          disputeId: dispute.id,
                          decision: decisions[dispute.id] ?? "",
                          newVersion,
                        })
                        .then(unwrap),
                    );
                  }}
                >
                  <div className="w-72">
                    <Field
                      id={`decision-${dispute.id}`}
                      label={t("ops.disputeDecision")}
                      value={decisions[dispute.id] ?? ""}
                      onChange={(event) => {
                        const value = event.currentTarget.value;
                        setDecisions((current) => ({ ...current, [dispute.id]: value }));
                      }}
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-text">
                    <input
                      type="checkbox"
                      checked={newVersion}
                      onChange={(event) => {
                        setNewVersion(event.currentTarget.checked);
                      }}
                    />
                    {t("ops.disputeNewVersion")}
                  </label>
                  <PrimaryButton
                    type="submit"
                    disabled={(decisions[dispute.id] ?? "").trim() === ""}
                  >
                    {t("ops.disputeDecide")}
                  </PrimaryButton>
                </form>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <SecondaryButton
          onClick={() => {
            void arbiterPdf();
          }}
        >
          {t("ops.arbiterPdf")}
        </SecondaryButton>
        {pdfPath !== null ? (
          <span className="text-xs text-subtle">{t("agreements.pdfSaved", { path: pdfPath })}</span>
        ) : null}
      </div>
      {error !== null ? <Alert>{error}</Alert> : null}
      {pdfError !== null ? <Alert>{pdfError}</Alert> : null}
    </Card>
  );
}

function RenewalSection({ agreement, ops }: { agreement: AgreementDto; ops: AgreementOpsDto }) {
  const { t } = useTranslation();
  const { run, error } = useOps(agreement);
  if (ops.reviewDate === null && ops.versionNotes.length === 0) {
    return null;
  }
  return (
    <Card title={t("ops.renewalTitle")}>
      {ops.reviewDate !== null ? (
        <p className={`text-sm ${ops.reviewDue ? "text-warning" : "text-muted"}`}>
          {ops.reviewDue
            ? t("ops.renewalDue", { date: ops.reviewDate })
            : t("ops.renewalNext", { date: ops.reviewDate })}
        </p>
      ) : null}
      {ops.status !== "IN_DISPUTE" && ops.status !== "ENDED" ? (
        <div>
          <SecondaryButton
            onClick={() => {
              void run(() => commands.confirmUnchanged(agreement.id).then(unwrap));
            }}
          >
            {t("ops.renewalConfirm")}
          </SecondaryButton>
        </div>
      ) : null}
      {ops.versionNotes.length > 0 ? (
        <ul className="flex flex-col gap-1 text-xs text-subtle">
          {ops.versionNotes.map((note) => (
            <li key={note.version}>
              {t("agreements.version", { version: note.version })} · {note.date} · {note.note}
            </li>
          ))}
        </ul>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
