import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  commands,
  type DisputeDto,
  type GovernanceDto,
  type IncidentDto,
  type ReminderDto,
  type ReviewAckInput,
  type ReviewDto,
} from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate, todayText } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";

const REASONS = ["SCHEDULED", "PROFIT_SPIKE", "EXTRA"] as const;
const CLAUSES = [1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
const optional = (v: string) => (v.trim() === "" ? null : v);

/** Eslatma matni: «3 kun qoldi», «bugun», «2 kun o'tdi». */
export function ReminderText({ r }: { r: ReminderDto }) {
  const { t } = useTranslation();
  const tone = r.state === "UPCOMING" ? "text-warn" : "text-danger";
  return (
    <span className={tone}>
      {t(`gov.reminder.${r.state}`, { count: r.days, date: showDate(r.dueOn) })}
    </span>
  );
}

/**
 * 6-qonun ijrosi (uy/SPEC 2F): vazifalar va «bajara olmayapman», oylik ochiq hisob ko'rigi,
 * nizo va hakam, yillik yangilash. Hamma qoida yadroda — bu yerda faqat ko'rsatish va kiritish.
 */
export function GovernanceView({ spaceId, partnershipId, onOpenContract }: { spaceId: string; partnershipId: string; onOpenContract: () => void }) {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: keys.governance(spaceId, partnershipId), queryFn: () => call(commands.governance(spaceId, partnershipId)) });
  const [session, setSession] = useState(false);
  const g = q.data;
  if (!g) return <ErrorText error={q.error} />;
  return (
    <div className="flex flex-col gap-4">
      {g.inDispute && (
        <p role="status" className="rounded border border-danger px-3 py-2 text-sm">
          {t("gov.inDispute")}
        </p>
      )}
      {!g.writable && (
        <p className="rounded border border-line px-3 py-2 text-sm text-ink-muted">{t(`venture.readOnly.${g.readOnlyReason ?? "NOT_ACTIVE"}`, { name: "" })}</p>
      )}
      <Schedule spaceId={spaceId} g={g} onOpenContract={onOpenContract} />
      <Duties spaceId={spaceId} g={g} />
      <section className="card flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{t("gov.reviews")}</h2>
          {g.writable && (
            <button className="btn-primary" onClick={() => setSession(true)}>
              {t("gov.startReview")}
            </button>
          )}
        </div>
        <p className="text-sm text-ink-muted">{t("gov.reviewHint")}</p>
        {g.reviews.length === 0 ? <p className="text-sm text-ink-muted">{t("gov.noReviews")}</p> : <Reviews spaceId={spaceId} g={g} />}
      </section>
      <Disputes spaceId={spaceId} g={g} onOpenContract={onOpenContract} />
      {session && <ReviewSession spaceId={spaceId} g={g} onClose={() => setSession(false)} />}
    </div>
  );
}

function Schedule({ spaceId, g, onOpenContract }: { spaceId: string; g: GovernanceDto; onOpenContract: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const renew = useMutation({
    mutationFn: () => call(commands.renewPartnership(spaceId, g.partnershipId)),
    onSuccess: (dto) => qc.setQueryData(keys.partnership(spaceId, dto.id), dto),
  });
  return (
    <section className="grid gap-4 md:grid-cols-2">
      <div className="card flex flex-col gap-1">
        <p className="text-sm text-ink-muted">{t("gov.nextReview")}</p>
        <p className="text-lg font-semibold tabular-nums">{g.nextReviewDue ? showDate(g.nextReviewDue) : "—"}</p>
        <p className="text-sm text-ink-muted">{t("gov.every", { count: g.reviewEveryDays })}</p>
        {g.reviewReminder && <ReminderText r={g.reviewReminder} />}
      </div>
      <div className="card flex flex-col gap-1">
        <p className="text-sm text-ink-muted">{t("gov.renewal")}</p>
        <p className="text-lg font-semibold tabular-nums">{g.reviewDate ? showDate(g.reviewDate) : "—"}</p>
        {g.renewalReminder && <ReminderText r={g.renewalReminder} />}
        <p className="text-sm text-ink-muted">{t("gov.renewalHint")}</p>
        <ErrorText error={renew.error} />
        {renew.isSuccess ? (
          <div className="flex flex-col gap-2">
            <p role="status" className="text-sm text-accent-text">
              {t("gov.renewed")}
            </p>
            <button className="btn-ghost self-start" onClick={onOpenContract}>
              {t("gov.openContract")}
            </button>
          </div>
        ) : (
          g.status === "ACTIVE" &&
          g.reviewDate && (
            <button className="btn-ghost self-start" disabled={renew.isPending} onClick={() => renew.mutate()}>
              {t("gov.renew")}
            </button>
          )
        )}
      </div>
    </section>
  );
}

function Duties({ spaceId, g }: { spaceId: string; g: GovernanceDto }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<{ dutyId: string; partyId: string; reason: string; date: string; solution: string } | null>(null);
  const [reported, setReported] = useState<IncidentDto | null>(null);
  const done = (dto: GovernanceDto) => qc.setQueryData(keys.governance(spaceId, g.partnershipId), dto);
  const report = useMutation({
    mutationFn: () =>
      call(
        commands.reportDutyIncident(spaceId, g.partnershipId, {
          dutyId: form?.dutyId ?? "",
          partyId: form?.partyId ?? "",
          reason: form?.reason ?? "",
          occurredOn: form?.date ?? "",
          proposedSolution: optional(form?.solution ?? ""),
        }),
      ),
    onSuccess: (dto) => {
      done(dto);
      setForm(null);
      setReported(dto.incidents[0] ?? null);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    report.mutate();
  };
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("gov.duties")}</h2>
      {g.duties.length === 0 && <p className="text-sm text-ink-muted">{t("gov.noDuties")}</p>}
      {g.duties.map((d) => (
        <div key={d.id} className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-2">
          <div className="min-w-0">
            <p className="font-medium">{d.title}</p>
            <p className="text-sm text-ink-muted">
              {t("gov.owner")}: {d.ownerName ?? "—"}
            </p>
            {d.breachClause && (
              <p className="text-sm">
                <span className="text-ink-muted">{t("gov.breachClause")}:</span> {d.breachClause}
              </p>
            )}
          </div>
          {g.writable && (
            <button
              className="btn-ghost px-3 py-1 text-sm"
              onClick={() => {
                setReported(null);
                setForm({ dutyId: d.id, partyId: d.ownerPartyId ?? g.parties[0]?.partyId ?? "", reason: "", date: todayText(), solution: "" });
              }}
            >
              {t("gov.cannotDo")}
            </button>
          )}
        </div>
      ))}
      {form && (
        <form className="flex flex-col gap-3 rounded border border-warn p-3" onSubmit={submit} aria-label={t("gov.cannotDo")}>
          {(() => {
            const d = g.duties.find((x) => x.id === form.dutyId);
            return (
              <p className="text-sm">
                <span className="font-semibold">{d?.title}</span>
                {d?.breachClause && (
                  <>
                    <br />
                    <span className="text-warn">{t("gov.breachClause")}:</span> {d.breachClause}
                  </>
                )}
              </p>
            );
          })()}
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              <span className="label">{t("gov.party")}</span>
              <select className="field" value={form.partyId} onChange={(e) => setForm({ ...form, partyId: e.target.value })}>
                {g.parties.map((p) => (
                  <option key={p.partyId} value={p.partyId}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="label">{t("gov.date")}</span>
              <input className="field tabular-nums" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </label>
          </div>
          <label>
            <span className="label">{t("gov.reason")}</span>
            <input className="field" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("gov.solution")}</span>
            <input className="field" value={form.solution} onChange={(e) => setForm({ ...form, solution: e.target.value })} />
          </label>
          <ErrorText error={report.error} />
          <div className="flex gap-2">
            <button className="btn-primary" disabled={report.isPending}>
              {t("gov.report")}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setForm(null)}>
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}
      {reported && (
        <div role="status" className="flex flex-col gap-1 rounded border border-accent p-3 text-sm">
          <p className="font-semibold">{t("gov.reported", { code: reported.hashCode })}</p>
          {reported.breachClause ? (
            <p>
              {t("gov.nowClause")} <span className="font-semibold">{reported.breachClause}</span>
            </p>
          ) : (
            <p className="text-ink-muted">{t("gov.noClause")}</p>
          )}
        </div>
      )}
      {g.incidents.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-semibold">{t("gov.incidents")}</h3>
          {g.incidents.map((i) => (
            <Incident key={i.id} spaceId={spaceId} g={g} i={i} />
          ))}
        </div>
      )}
    </section>
  );
}

function Incident({ spaceId, g, i }: { spaceId: string; g: GovernanceDto; i: IncidentDto }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [note, setNote] = useState<string | null>(null);
  const resolve = useMutation({
    mutationFn: () => call(commands.resolveDutyIncident(spaceId, g.partnershipId, i.id, note ?? "")),
    onSuccess: (dto) => {
      qc.setQueryData(keys.governance(spaceId, g.partnershipId), dto);
      setNote(null);
    },
  });
  return (
    <div className="flex flex-col gap-1 border-b border-line pb-2 text-sm">
      <p>
        <span className="tabular-nums text-ink-muted">{showDate(i.occurredOn)}</span> · <span className="font-medium">{i.dutyTitle}</span> · {i.partyName}{" "}
        <span className={i.resolvedOn ? "text-accent-text" : "text-warn"}>· {t(i.resolvedOn ? "gov.resolved" : "gov.open")}</span>
      </p>
      <p>{i.reason}</p>
      {i.proposedSolution && (
        <p className="text-ink-muted">
          {t("gov.solution")}: {i.proposedSolution}
        </p>
      )}
      {i.resolvedOn && (
        <p className="text-accent-text">
          ✓ {showDate(i.resolvedOn)} — {i.resolutionNote}
        </p>
      )}
      {!i.resolvedOn && g.writable && note === null && (
        <button className="btn-ghost self-start px-3 py-1 text-sm" onClick={() => setNote("")}>
          {t("gov.resolve")}
        </button>
      )}
      {note !== null && (
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            resolve.mutate();
          }}
        >
          <input className="field min-w-0 flex-1" aria-label={t("gov.resolutionNote")} placeholder={t("gov.resolutionNote")} value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn-primary" disabled={resolve.isPending}>
            {t("common.save")}
          </button>
          <ErrorText error={resolve.error} />
        </form>
      )}
    </div>
  );
}

function Integrity({ r }: { r: ReviewDto }) {
  const { t } = useTranslation();
  const ok = r.integrity === "INTACT";
  return (
    <span className={ok ? "text-accent-text" : "font-semibold text-danger"}>
      {t(`gov.integrity.${r.integrity}`)}
      {r.entriesAfter > 0 && <span className="block text-xs text-ink-muted">{t("gov.entriesAfter", { count: r.entriesAfter })}</span>}
    </span>
  );
}

function Reviews({ spaceId, g }: { spaceId: string; g: GovernanceDto }) {
  const { t } = useTranslation();
  const pdf = useMutation({ mutationFn: (id: string) => call(commands.exportReviewProtocol(spaceId, g.partnershipId, id)) });
  return (
    <div className="flex flex-col gap-2">
      <ErrorText error={pdf.error} />
      {g.reviews.map((r) => (
        <article key={r.id} aria-label={t("gov.reviewNo", { n: r.no })} className="flex flex-col gap-2 border-t border-line pt-3 text-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold">
                {t("gov.reviewNo", { n: r.no })} · <span className="tabular-nums">{showDate(r.fromOn)} — {showDate(r.toOn)}</span>
              </p>
              <p className="text-ink-muted">
                {t(`gov.reason.${r.reason}`)} · {t("gov.heldOn")} {showDate(r.heldOn)}
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-right">
                <Integrity r={r} />
                <span className="block font-mono text-xs text-ink-muted">{r.chainCode}</span>
              </div>
              <button className="btn-ghost whitespace-nowrap px-3 py-1 text-sm" disabled={pdf.isPending} onClick={() => pdf.mutate(r.id)}>
                {t("gov.protocolPdf")}
              </button>
            </div>
          </div>
          {r.acks.map((a) => (
            <p key={a.partyId}>
              {a.partyName}: <span className={a.verdict === "AGREE" ? "text-accent-text" : "text-warn"}>{t(`gov.verdict.${a.verdict}`)}</span>
              {a.note && <span className="text-ink-muted"> — {a.note}</span>}
            </p>
          ))}
        </article>
      ))}
    </div>
  );
}

/** Oila kengashi uslubidagi to'liq ekran ko'rik sessiyasi (uy/SPEC 2F.5). */
function ReviewSession({ spaceId, g, onClose }: { spaceId: string; g: GovernanceDto; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const qc = useQueryClient();
  // Bo'sh sana — yadro «bugun» deb oladi (UI o'z soatiga tayanmaydi).
  const [toText, setToText] = useState("");
  const [to, setTo] = useState("");
  const [reason, setReason] = useState<string>("SCHEDULED");
  const [acks, setAcks] = useState<Record<string, { verdict: string; note: string }>>({});
  const draft = useQuery({ queryKey: ["reviewDraft", spaceId, g.partnershipId, to], queryFn: () => call(commands.reviewDraft(spaceId, g.partnershipId, to)) });
  const hold = useMutation({
    mutationFn: () =>
      call(
        commands.holdReview(spaceId, g.partnershipId, {
          toOn: draft.data?.toOn ?? to,
          reason,
          acks: g.parties.map((p): ReviewAckInput => ({ partyId: p.partyId, verdict: acks[p.partyId]?.verdict ?? "", note: optional(acks[p.partyId]?.note ?? "") })),
        }),
      ),
    onSuccess: (dto) => {
      qc.setQueryData(keys.governance(spaceId, g.partnershipId), dto);
      onClose();
    },
  });
  const d = draft.data;
  const complete = g.parties.every((p) => {
    const a = acks[p.partyId];
    return a?.verdict === "AGREE" || (a?.verdict === "OBJECT" && a.note.trim() !== "");
  });
  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("gov.session")} className="fixed inset-0 z-20 overflow-y-auto bg-paper p-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-serif text-2xl font-semibold">
            {t("gov.session")} {d ? `№${d.no}` : ""} · {g.title}
          </h2>
          <button className="btn-ghost" onClick={onClose}>
            {t("common.close")}
          </button>
        </div>
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setTo(toText);
          }}
        >
          <label>
            <span className="label">{t("gov.toOn")}</span>
            <input className="field tabular-nums" placeholder={t("gov.today")} value={toText} onChange={(e) => setToText(e.target.value)} />
          </label>
          <button className="btn-ghost">{t("gov.showRange")}</button>
          <label>
            <span className="label">{t("gov.reasonTitle")}</span>
            <select className="field" value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => (
                <option key={r} value={r}>
                  {t(`gov.reason.${r}`)}
                </option>
              ))}
            </select>
          </label>
        </form>
        <ErrorText error={draft.error} />
        {d && (
          <>
            <p className="text-ink-muted">
              {showDate(d.fromOn)} — {showDate(d.toOn)}
            </p>
            <div className={`card flex flex-col gap-1 ${d.chainOk ? "border-accent/60" : "border-danger"}`}>
              <p className={d.chainOk ? "text-accent-text" : "font-semibold text-danger"}>{t(d.chainOk ? "gov.chainOk" : "gov.chainBroken")}</p>
              <p className="text-sm text-ink-muted">
                {t("gov.chainEntries", { count: d.chainEntries })} · <span className="font-mono">{d.chainCode}</span>
              </p>
            </div>
            <dl className="card grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
              <Total label={t("venture.total.income")} value={d.totals.income.formatted} />
              <Total label={t("venture.total.expense")} value={d.totals.expense.formatted} />
              {d.totals.forceMajeure.minor !== "0" && <Total label={t("venture.total.forceMajeure")} value={d.totals.forceMajeure.formatted} />}
              {d.totals.corrections.minor !== "0" && <Total label={t("venture.total.corrections")} value={d.totals.corrections.formatted} />}
              <Total label={t("venture.total.result")} value={d.totals.result.formatted} strong />
              <Total label={t("gov.entries")} value={String(d.totals.entries)} />
              <Total label={t("gov.periodsClosed")} value={String(d.totals.periodsClosed)} />
            </dl>
            <div className="card flex flex-col gap-2">
              <h3 className="font-semibold">{t("gov.openIncidents")}</h3>
              {d.openIncidents.length === 0 ? (
                <p className="text-sm text-ink-muted">{t("gov.noOpenIncidents")}</p>
              ) : (
                d.openIncidents.map((i) => (
                  <p key={i.id} className="text-sm">
                    <span className="tabular-nums text-ink-muted">{showDate(i.occurredOn)}</span> · {i.dutyTitle} · {i.partyName} — {i.reason}
                  </p>
                ))
              )}
            </div>
            <div className="card overflow-x-auto">
              <h3 className="mb-2 font-semibold">{t("gov.entriesTitle")}</h3>
              {d.entries.length === 0 ? (
                <p className="text-sm text-ink-muted">{t("venture.empty")}</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <tbody>
                    {d.entries.map((e) => (
                      <tr key={e.id} className="border-t border-line">
                        <td className="py-1 pr-3 tabular-nums">{showDate(e.occurredOn)}</td>
                        <td className="py-1 pr-3">{t(`venture.kind.${e.kind}`)}</td>
                        <td className="py-1 pr-3 text-ink-muted">{e.note}</td>
                        <td className="py-1 text-right tabular-nums">{e.effect.formatted}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="card flex flex-col gap-3">
              <h3 className="font-semibold">{t("gov.acksTitle")}</h3>
              {g.parties.map((p) => {
                const a = acks[p.partyId] ?? { verdict: "", note: "" };
                const set = (patch: Partial<typeof a>) => setAcks({ ...acks, [p.partyId]: { ...a, ...patch } });
                return (
                  <div key={p.partyId} role="radiogroup" aria-label={p.name} className="flex flex-col gap-2 border-b border-line pb-2">
                    <p className="font-medium">{p.name}</p>
                    <div className="flex flex-wrap gap-4 text-sm">
                      {(["AGREE", "OBJECT"] as const).map((v) => (
                        <label key={v} className="flex items-center gap-2">
                          <input type="radio" name={`ack-${p.partyId}`} checked={a.verdict === v} onChange={() => set({ verdict: v })} />
                          {t(`gov.verdict.${v}`)}
                        </label>
                      ))}
                    </div>
                    {a.verdict === "OBJECT" && (
                      <input className="field" aria-label={t("gov.objectionNote", { name: p.name })} placeholder={t("gov.objectionNote", { name: p.name })} value={a.note} onChange={(e) => set({ note: e.target.value })} />
                    )}
                  </div>
                );
              })}
              <ErrorText error={hold.error} />
              <button className="btn-primary self-start" disabled={!complete || hold.isPending} onClick={() => hold.mutate()}>
                {t("gov.holdReview")}
              </button>
              <p className="text-sm text-ink-muted">{t("gov.holdHint")}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Total({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <dt className="text-ink-muted">{label}</dt>
      <dd className={`tabular-nums ${strong ? "text-lg font-semibold text-accent-text" : ""}`}>{value}</dd>
    </div>
  );
}

function Disputes({ spaceId, g, onOpenContract }: { spaceId: string; g: GovernanceDto; onOpenContract: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<{ subject: string; clauses: number[]; openedBy: string; claim: string } | null>(null);
  const open = useMutation({
    mutationFn: () =>
      call(
        commands.openPartnershipDispute(spaceId, g.partnershipId, {
          subject: form?.subject ?? "",
          clauses: form?.clauses ?? [],
          openedBy: form?.openedBy ?? "",
          claims: form && form.claim.trim() !== "" ? [{ partyId: form.openedBy, claim: form.claim }] : [],
        }),
      ),
    onSuccess: (dto) => {
      qc.setQueryData(keys.governance(spaceId, g.partnershipId), dto);
      setForm(null);
    },
  });
  return (
    <section className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("gov.disputes")}</h2>
        {!g.inDispute && g.status === "ACTIVE" && form === null && (
          <button className="btn-ghost" onClick={() => setForm({ subject: "", clauses: [], openedBy: g.parties[0]?.partyId ?? "", claim: "" })}>
            {t("gov.openDispute")}
          </button>
        )}
      </div>
      <p className="text-sm text-ink-muted">{t("gov.disputeHint", { arbiter: g.arbiterName ?? "—" })}</p>
      {form && (
        <form
          className="flex flex-col gap-3 rounded border border-danger p-3"
          onSubmit={(e) => {
            e.preventDefault();
            open.mutate();
          }}
        >
          <label>
            <span className="label">{t("gov.subject")}</span>
            <input className="field" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </label>
          <fieldset className="flex flex-col gap-1">
            <legend className="label">{t("gov.clauses")}</legend>
            <div className="flex flex-wrap gap-3 text-sm">
              {CLAUSES.map((c) => (
                <label key={c} className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={form.clauses.includes(c)}
                    onChange={(e) => setForm({ ...form, clauses: e.target.checked ? [...form.clauses, c] : form.clauses.filter((x) => x !== c) })}
                  />
                  {c}. {t(`partnership.step.${c}`)}
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            <span className="label">{t("gov.openedBy")}</span>
            <select className="field" value={form.openedBy} onChange={(e) => setForm({ ...form, openedBy: e.target.value })}>
              {g.parties.map((p) => (
                <option key={p.partyId} value={p.partyId}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">{t("gov.claim")}</span>
            <input className="field" value={form.claim} onChange={(e) => setForm({ ...form, claim: e.target.value })} />
          </label>
          <p className="text-sm text-warn">{t("gov.disputeEffect")}</p>
          <ErrorText error={open.error} />
          <div className="flex gap-2">
            <button className="btn-primary" disabled={open.isPending}>
              {t("gov.openDispute")}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setForm(null)}>
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}
      {g.disputes.length === 0 && !form && <p className="text-sm text-ink-muted">{t("gov.noDisputes")}</p>}
      {g.disputes.map((d) => (
        <Dispute key={d.id} spaceId={spaceId} g={g} d={d} onOpenContract={onOpenContract} />
      ))}
    </section>
  );
}

function Dispute({ spaceId, g, d, onOpenContract }: { spaceId: string; g: GovernanceDto; d: DisputeDto; onOpenContract: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const done = (dto: GovernanceDto) => qc.setQueryData(keys.governance(spaceId, g.partnershipId), dto);
  const missing = g.parties.filter((p) => !d.claims.some((c) => c.partyId === p.partyId));
  const [claim, setClaim] = useState({ partyId: missing[0]?.partyId ?? "", text: "" });
  const [decision, setDecision] = useState({ date: todayText(), text: "", outcome: "RESUME" });
  const addClaim = useMutation({
    mutationFn: () => call(commands.addDisputeClaim(spaceId, g.partnershipId, d.id, { partyId: claim.partyId || (missing[0]?.partyId ?? ""), claim: claim.text })),
    onSuccess: (dto) => {
      done(dto);
      setClaim({ partyId: "", text: "" });
    },
  });
  const decide = useMutation({
    mutationFn: () => call(commands.recordArbiterDecision(spaceId, g.partnershipId, d.id, { decidedOn: decision.date, decision: decision.text, outcome: decision.outcome })),
    onSuccess: done,
  });
  const folder = useMutation({ mutationFn: () => call(commands.exportDisputeFolder(spaceId, g.partnershipId, d.id)) });
  return (
    <article className={`flex flex-col gap-2 rounded border p-3 ${d.open ? "border-danger" : "border-line"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold">{d.subject}</p>
        <span className={d.open ? "text-sm text-danger" : "text-sm text-accent-text"}>{t(d.open ? "gov.disputeOpen" : "gov.disputeClosed")}</span>
      </div>
      <p className="text-sm text-ink-muted">
        {t("gov.openedOn", { date: showDate(d.openedOn), name: d.openedByName })} · {t("gov.clausesList", { list: d.clauses.join(", ") })}
      </p>
      {d.claims.map((c) => (
        <p key={c.partyId} className="text-sm">
          <span className="font-medium">{c.partyName}:</span> {c.claim}
        </p>
      ))}
      {d.open && missing.length > 0 && (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addClaim.mutate();
          }}
        >
          <label>
            <span className="label">{t("gov.party")}</span>
            <select className="field" value={claim.partyId || (missing[0]?.partyId ?? "")} onChange={(e) => setClaim({ ...claim, partyId: e.target.value })}>
              {missing.map((p) => (
                <option key={p.partyId} value={p.partyId}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-0 flex-1">
            <span className="label">{t("gov.claim")}</span>
            <input className="field" value={claim.text} onChange={(e) => setClaim({ ...claim, text: e.target.value })} />
          </label>
          <button className="btn-ghost" disabled={addClaim.isPending}>
            {t("gov.addClaim")}
          </button>
        </form>
      )}
      {d.decision ? (
        <div className="flex flex-col gap-1 rounded bg-surface p-2 text-sm">
          <p className="font-semibold">
            {t("gov.decisionOf", { name: d.decision.arbiterName, date: showDate(d.decision.decidedOn) })}
          </p>
          <p>{d.decision.decision}</p>
          <p className="text-accent-text">{t(`gov.outcome.${d.decision.outcome}`)}</p>
          {d.decision.outcome === "AMEND" && (
            <button className="btn-ghost self-start px-3 py-1 text-sm" onClick={onOpenContract}>
              {t("gov.openContract")}
            </button>
          )}
        </div>
      ) : (
        <form
          className="flex flex-col gap-2 border-t border-line pt-2"
          onSubmit={(e) => {
            e.preventDefault();
            decide.mutate();
          }}
        >
          <p className="text-sm font-semibold">{t("gov.recordDecision", { name: g.arbiterName ?? "—" })}</p>
          <div className="grid gap-2 sm:grid-cols-[10rem_1fr]">
            <label>
              <span className="label">{t("gov.date")}</span>
              <input className="field tabular-nums" value={decision.date} onChange={(e) => setDecision({ ...decision, date: e.target.value })} />
            </label>
            <label>
              <span className="label">{t("gov.decision")}</span>
              <input className="field" value={decision.text} onChange={(e) => setDecision({ ...decision, text: e.target.value })} />
            </label>
          </div>
          <div role="radiogroup" aria-label={t("gov.outcomeTitle")} className="flex flex-wrap gap-4 text-sm">
            {(["RESUME", "AMEND"] as const).map((o) => (
              <label key={o} className="flex items-center gap-2">
                <input type="radio" name={`outcome-${d.id}`} checked={decision.outcome === o} onChange={() => setDecision({ ...decision, outcome: o })} />
                {t(`gov.outcome.${o}`)}
              </label>
            ))}
          </div>
          <button className="btn-primary self-start" disabled={decide.isPending}>
            {t("gov.saveDecision")}
          </button>
        </form>
      )}
      <ErrorText error={addClaim.error ?? decide.error ?? folder.error} />
      <button className="btn-ghost self-start px-3 py-1 text-sm" disabled={folder.isPending} onClick={() => folder.mutate()}>
        {t("gov.folderPdf")}
      </button>
    </article>
  );
}
