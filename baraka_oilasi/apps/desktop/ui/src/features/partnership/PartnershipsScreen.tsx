import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  type Answer,
  commands,
  type GateDto,
  type PartnershipDto,
  type PartnershipInput,
  type Stroke,
} from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { SignaturePad } from "../../components/SignaturePad";
import { call, CoreError } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const KINDS = ["MUDARABA", "MUSHARAKA"] as const;
const ROLES = ["CAPITAL_PROVIDER", "WORKER", "BOTH"] as const;
const CAPITAL_KINDS = ["MONEY", "EQUIPMENT"] as const;
/** Usta qadamlari: 9 savol, imzolar va boshlash. */
const STEPS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] as const;
type Step = (typeof STEPS)[number];

type Mode = "ANSWERED" | "NOT_APPLICABLE";
type Ans<T> = { mode: Mode; value: T; reason: string };
type CapitalForm = { kind: string; description: string; amount: string };
type PartyForm = { id: string; fullName: string; role: string; share: string; isMe: boolean; capital: CapitalForm[] };
type DutyForm = { id: string; title: string; owner: string; breach: string };
type BuyoutForm = { seller: string; buyer: string; units: string; per: string; period: string; start: string; profit: string };
type Form = {
  kind: string;
  title: string;
  parties: PartyForm[];
  profitMode: "SHARE" | "FIXED";
  fixed: string;
  duties: Ans<DutyForm[]>;
  negligence: string;
  custody: Ans<{ location: string; keeper: string; review: string }>;
  exit: Ans<{ notice: string; valuation: string; payout: string; assets: string }>;
  arbiter: Ans<{ name: string; role: string }>;
  term: Ans<{ from: string; months: string; review: string }>;
  witnesses: string[];
  buyout: BuyoutForm | null;
};

const ans = <T,>(value: T): Ans<T> => ({ mode: "ANSWERED", value, reason: "" });
const blankParty = (id: string, role: string, isMe: boolean): PartyForm => ({ id, fullName: "", role, share: "50", isMe, capital: [] });

function blank(): Form {
  return {
    kind: "MUDARABA",
    title: "",
    parties: [blankParty("P1", "CAPITAL_PROVIDER", false), blankParty("P2", "WORKER", true)],
    profitMode: "SHARE",
    fixed: "",
    duties: ans([{ id: "d1", title: "", owner: "", breach: "" }]),
    negligence: "",
    custody: ans({ location: "", keeper: "", review: "30" }),
    exit: ans({ notice: "30", valuation: "", payout: "", assets: "" }),
    arbiter: ans({ name: "", role: "" }),
    term: ans({ from: "", months: "12", review: "" }),
    witnesses: [""],
    buyout: null,
  };
}

/** Foiz matni (`50`, `33,5`) → basis points; butun sonlar bilan, pul emas. */
function toBp(v: string, field: string): number {
  const m = /^(\d{1,3})(?:[.,](\d{1,2}))?$/.exec(v.trim());
  if (!m) throw new CoreError({ code: "INVALID_PERCENT", field });
  return Number(m[1]) * 100 + Number((m[2] ?? "").padEnd(2, "0"));
}
const bpText = (bp: number) => {
  const frac = bp % 100;
  return frac === 0 ? String(Math.trunc(bp / 100)) : `${Math.trunc(bp / 100)},${String(frac).padStart(2, "0").replace(/0$/, "")}`;
};
/** Kunlar, oylar, birliklar — butun son (pul emas). */
function count(v: string, field: string): number {
  if (!/^\d{1,4}$/.test(v.trim())) throw new CoreError({ code: "INVALID_NUMBER", field });
  return Number(v.trim());
}
const empty = (...v: string[]) => v.every((x) => x.trim() === "");

function answer<F, T>(a: Ans<F>, isEmpty: (v: F) => boolean, build: (v: F) => T): Answer<T> {
  if (a.mode === "NOT_APPLICABLE") return { status: "NOT_APPLICABLE", reason: a.reason };
  return isEmpty(a.value) ? { status: "UNANSWERED" } : { status: "ANSWERED", value: build(a.value) };
}

function toInput(f: Form): PartnershipInput {
  return {
    kind: f.kind,
    title: f.title,
    parties: f.parties.map((p) => ({
      id: p.id,
      fullName: p.fullName,
      role: p.role,
      profitShareBp: toBp(p.share, "profitShareBp"),
      isMe: p.isMe,
      capital: p.role === "WORKER" ? [] : p.capital,
    })),
    fixedReturn: f.profitMode === "FIXED" ? f.fixed : null,
    duties: answer(
      f.duties,
      (d) => d.every((x) => empty(x.title, x.breach)),
      (d) => d.filter((x) => !empty(x.title, x.breach)).map((x) => ({ id: x.id, title: x.title, ownerPartyId: x.owner || null, breachClause: x.breach || null })),
    ),
    negligenceClause: f.negligence.trim() === "" ? null : f.negligence,
    custody: answer(
      f.custody,
      (c) => empty(c.location, c.keeper),
      (c) => ({ location: c.location, keeperPartyId: c.keeper, reviewEveryDays: count(c.review, "reviewEveryDays"), keeperDeviceId: null }),
    ),
    exitClause: answer(
      f.exit,
      (e) => empty(e.valuation, e.payout),
      (e) => ({ noticeDays: count(e.notice, "noticeDays"), valuationMethod: e.valuation, payoutTerms: e.payout, assetSplit: e.assets || null }),
    ),
    arbiter: answer(f.arbiter, (a) => empty(a.name), (a) => ({ fullName: a.name, role: a.role || null, partyId: null })),
    term: answer(
      f.term,
      (x) => empty(x.from, x.review),
      (x) => ({ effectiveFrom: x.from, durationMonths: x.months.trim() === "" ? null : count(x.months, "durationMonths"), reviewDate: x.review }),
    ),
    witnesses: f.witnesses,
    buyout: f.buyout && {
      sellerPartyId: f.buyout.seller,
      buyerPartyId: f.buyout.buyer,
      units: count(f.buyout.units, "units"),
      unitsPerPeriod: count(f.buyout.per, "unitsPerPeriod"),
      periodMonths: count(f.buyout.period, "periodMonths"),
      start: f.buyout.start,
      expectedProfit: f.buyout.profit.trim() === "" ? null : f.buyout.profit,
    },
  };
}

function fromAnswer<T, F>(a: Answer<T>, fallback: F, map: (v: T) => F): Ans<F> {
  if (a.status === "ANSWERED") return ans(map(a.value));
  if (a.status === "NOT_APPLICABLE") return { mode: "NOT_APPLICABLE", value: fallback, reason: a.reason };
  return ans(fallback);
}

function fromDto(p: PartnershipDto): Form {
  const b = blank();
  return {
    kind: p.kind,
    title: p.title,
    parties: p.parties.map((x) => ({
      id: x.id,
      fullName: x.fullName,
      role: x.role,
      share: bpText(x.profitShareBp),
      isMe: x.isMe,
      capital: x.capitalItems.map((c) => ({ kind: c.kind, description: c.description, amount: c.amount.plain })),
    })),
    profitMode: "SHARE",
    fixed: "",
    duties: fromAnswer(p.duties, b.duties.value, (d) => d.map((x) => ({ id: x.id, title: x.title, owner: x.ownerPartyId ?? "", breach: x.breachClause ?? "" }))),
    negligence: p.negligenceClause ?? "",
    custody: fromAnswer(p.custody, b.custody.value, (c) => ({ location: c.location, keeper: c.keeperPartyId, review: String(c.reviewEveryDays) })),
    exit: fromAnswer(p.exitClause, b.exit.value, (e) => ({ notice: String(e.noticeDays), valuation: e.valuationMethod, payout: e.payoutTerms, assets: e.assetSplit ?? "" })),
    arbiter: fromAnswer(p.arbiter, b.arbiter.value, (a) => ({ name: a.fullName, role: a.role ?? "" })),
    term: fromAnswer(p.term, b.term.value, (x) => ({ from: showDate(x.effectiveFrom), months: x.durationMonths == null ? "" : String(x.durationMonths), review: showDate(x.reviewDate) })),
    witnesses: p.witnesses.length > 0 ? p.witnesses : [""],
    buyout: p.buyout && {
      seller: p.buyout.sellerPartyId,
      buyer: p.buyout.buyerPartyId,
      units: String(p.buyout.units),
      per: String(p.buyout.unitsPerPeriod),
      period: String(p.buyout.periodMonths),
      start: p.buyout.start,
      profit: p.buyout.expectedProfit?.plain ?? "",
    },
  };
}

/**
 * 5-qonun: «Pulni halol ishga sol» (uy/SPEC 2E). Sheriklik — qarz ham, sadaqa ham emas: teng
 * huquqli kelishuv. Shartnoma 9 savol boʻyicha yoziladi, shu qurilmada imzolanadi.
 */
export function PartnershipsScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<string | "new" | null>(null);
  const list = useQuery({ queryKey: keys.partnerships(spaceId), queryFn: () => call(commands.partnerships(spaceId)) });
  if (open) return <PartnershipView spaceId={spaceId} id={open === "new" ? null : open} onOpen={setOpen} onBack={() => setOpen(null)} />;
  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("partnership.title")}</h1>
        <button className="btn-primary" onClick={() => setOpen("new")}>
          {t("partnership.new")}
        </button>
      </div>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p>{t("partnership.intro")}</p>
        <p className="text-sm text-ink-muted">{t("partnership.regulatory")}</p>
      </aside>
      <ErrorText error={list.error} />
      {list.data?.length === 0 && <p className="text-ink-muted">{t("partnership.empty")}</p>}
      {(list.data ?? []).map((p) => (
        <button key={p.id} className="card flex flex-wrap items-center justify-between gap-3 text-left hover:border-accent" onClick={() => setOpen(p.id)}>
          <span>
            <span className="text-lg font-semibold">{p.title}</span>
            <span className="ml-2 text-sm text-ink-muted">
              {t(`partnership.kind.${p.kind}`)}
              {p.myRole ? ` · ${t(`partnership.myRole.${p.myRole}`)}` : ""}
            </span>
          </span>
          <span className="flex items-center gap-2 text-sm">
            <span className="text-ink-muted">{t("partnership.progress", { n: p.answered })}</span>
            <StatusBadge status={p.status} />
            <span className="font-semibold tabular-nums text-accent">{p.capitalTotal.formatted}</span>
          </span>
        </button>
      ))}
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const tone = status === "ACTIVE" ? "border-accent text-accent-text" : "border-line text-ink-muted";
  return <span className={`rounded border px-2 py-0.5 text-xs ${tone}`}>{t(`partnership.status.${status}`)}</span>;
}

function PartnershipView({ spaceId, id, onOpen, onBack }: { spaceId: string; id: string | null; onOpen: (id: string) => void; onBack: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: keys.partnership(spaceId, id ?? "new"),
    queryFn: () => call(commands.partnership(spaceId, id ?? "")),
    enabled: id !== null,
  });
  const [form, setForm] = useState<Form | null>(id === null ? blank() : null);
  const [step, setStep] = useState<Step>(1);
  const p = q.data ?? null;
  if (form === null && p) setForm(fromDto(p));

  const save = useMutation({
    mutationFn: (f: Form) => {
      const input = toInput(f);
      return call(id === null ? commands.createPartnership(spaceId, input) : commands.updatePartnership(spaceId, id, input));
    },
    onSuccess: (dto) => {
      qc.setQueryData(keys.partnership(spaceId, dto.id), dto);
      setForm(fromDto(dto));
      if (id === null) onOpen(dto.id);
    },
  });
  const locked = p?.status === "CLOSED";
  const set = (patch: Partial<Form>) => form && setForm({ ...form, ...patch });

  if (!form) return <ErrorText error={q.error} />;
  const fixedBlocked = form.profitMode === "FIXED";
  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-ghost px-3 py-1 text-sm" onClick={onBack}>
          ← {t("partnership.back")}
        </button>
        <h1 className="text-2xl font-semibold">{form.title || t("partnership.new")}</h1>
        {p && <StatusBadge status={p.status} />}
        {p?.version != null && <span className="text-sm text-ink-muted">{t("partnership.versionNo", { n: p.version })}</span>}
      </div>
      {p?.templateReview === "PENDING" && <p className="rounded border border-warn px-3 py-2 text-sm">{t("partnership.reviewPending")}</p>}
      {p?.amendmentPending && <p className="rounded border border-warn px-3 py-2 text-sm">{t("partnership.amendmentPending", { n: p.signedVersion ?? 0 })}</p>}
      <div className="grid gap-5 lg:grid-cols-[11rem_1fr]">
        <nav aria-label={t("partnership.steps")} className="flex flex-col gap-1">
          <p className="mb-1 text-sm text-ink-muted">{t("partnership.progress", { n: p?.check.answered ?? 0 })}</p>
          {STEPS.map((s) => {
            const missing = p?.check.missing.includes(s) ?? s <= 9;
            return (
              <button
                key={s}
                aria-current={step === s ? "step" : undefined}
                className={`rounded px-3 py-1.5 text-left text-sm ${step === s ? "bg-surface text-ink" : "text-ink-muted hover:text-ink"}`}
                onClick={() => setStep(s)}
              >
                {s <= 9 && <span className={missing ? "text-ink-muted" : "text-accent-text"}>{missing ? "○" : "●"} </span>}
                {t(`partnership.step.${s}`)}
              </button>
            );
          })}
        </nav>
        <div className="flex min-w-0 flex-col gap-4">
          {step <= 9 && (
            <form
              className="card flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                save.mutate(form);
              }}
            >
              <h2 className="text-lg font-semibold">
                {step}. {t(`partnership.q.${step}`)}
              </h2>
              <QuestionStep step={step} form={form} set={set} dto={p} />
              {fixedBlocked && step === 4 && <p className="text-sm text-danger">{t("partnership.fixedBlocked")}</p>}
              <ErrorText error={save.error} />
              {!locked && (
                <div className="flex flex-wrap gap-2">
                  <button className="btn-primary" disabled={save.isPending || fixedBlocked}>
                    {t("common.save")}
                  </button>
                  {step < 9 && (
                    <button type="button" className="btn-ghost" disabled={save.isPending || fixedBlocked} onClick={() => save.mutate(form, { onSuccess: () => setStep((step + 1) as Step) })}>
                      {t("partnership.saveNext")}
                    </button>
                  )}
                </div>
              )}
            </form>
          )}
          {step === 10 && (p ? <SignStep spaceId={spaceId} p={p} /> : <p className="text-ink-muted">{t("partnership.saveFirst")}</p>)}
          {step === 11 && (p ? <StartStep spaceId={spaceId} p={p} /> : <p className="text-ink-muted">{t("partnership.saveFirst")}</p>)}
          {p && step <= 9 && <CheckPanel p={p} />}
        </div>
      </div>
    </section>
  );
}

function Field({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={className}>
      <span className="label">{label}</span>
      {children}
    </label>
  );
}

/** «Javob» yoki asosli «Tegishli emas» (izoh majburiy, 2F.2). */
function NaToggle<T>({ a, onChange }: { a: Ans<T>; onChange: (a: Ans<T>) => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-4 text-sm">
        {(["ANSWERED", "NOT_APPLICABLE"] as const).map((m) => (
          <label key={m} className="flex items-center gap-2">
            <input type="radio" checked={a.mode === m} onChange={() => onChange({ ...a, mode: m })} />
            {t(`partnership.mode.${m}`)}
          </label>
        ))}
      </div>
      {a.mode === "NOT_APPLICABLE" && (
        <Field label={t("partnership.naReason")}>
          <input className="field" value={a.reason} onChange={(e) => onChange({ ...a, reason: e.target.value })} />
        </Field>
      )}
    </div>
  );
}

function PartySelect({ form, value, onChange, label }: { form: Form; value: string; onChange: (v: string) => void; label: string }) {
  const { t } = useTranslation();
  return (
    <Field label={label}>
      <select className="field" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t("partnership.choose")}</option>
        {form.parties.map((p) => (
          <option key={p.id} value={p.id}>
            {p.fullName || p.id}
          </option>
        ))}
      </select>
    </Field>
  );
}

function QuestionStep({ step, form, set, dto }: { step: Step; form: Form; set: (p: Partial<Form>) => void; dto: PartnershipDto | null }) {
  const { t } = useTranslation();
  const party = (i: number, patch: Partial<PartyForm>) => set({ parties: form.parties.map((p, j) => (j === i ? { ...p, ...patch } : p)) });
  switch (step) {
    case 1:
      return (
        <>
          <Field label={t("partnership.name")}>
            <input className="field" value={form.title} onChange={(e) => set({ title: e.target.value })} required />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            {KINDS.map((k) => (
              <label key={k} className={`card flex cursor-pointer flex-col gap-1 ${form.kind === k ? "border-accent" : ""}`}>
                <span className="flex items-center gap-2 font-semibold">
                  <input type="radio" name="kind" checked={form.kind === k} disabled={dto?.status === "ACTIVE"} onChange={() => set({ kind: k })} />
                  {t(`partnership.kind.${k}`)}
                </span>
                <span className="text-sm text-ink-muted">{t(`partnership.kindHint.${k}`)}</span>
              </label>
            ))}
          </div>
          {form.parties.map((p, i) => (
            <div key={p.id} className="grid items-end gap-3 rounded border border-line p-3 sm:grid-cols-2">
              <Field label={t("partnership.partyName", { id: p.id })} className="sm:col-span-2">
                <input className="field" value={p.fullName} onChange={(e) => party(i, { fullName: e.target.value })} />
              </Field>
              <Field label={t("partnership.role")}>
                <select className="field" value={p.role} onChange={(e) => party(i, { role: e.target.value })}>
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`partnership.role.${r}`)}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="flex items-center justify-between gap-2 pb-2">
                <label className="flex items-center gap-2 text-sm">
                  <input type="radio" name="me" checked={p.isMe} onChange={() => set({ parties: form.parties.map((x, j) => ({ ...x, isMe: j === i })) })} />
                  {t("partnership.isMe")}
                </label>
                {form.parties.length > 2 && (
                  <button type="button" className="btn-ghost px-3 py-1 text-sm" onClick={() => set({ parties: form.parties.filter((_, j) => j !== i) })}>
                    {t("partnership.remove")}
                  </button>
                )}
              </div>
            </div>
          ))}
          <button
            type="button"
            className="btn-ghost self-start"
            onClick={() => {
              let n = form.parties.length + 1;
              while (form.parties.some((p) => p.id === `P${n}`)) n += 1;
              set({ parties: [...form.parties, blankParty(`P${n}`, "BOTH", false)] });
            }}
          >
            + {t("partnership.addParty")}
          </button>
        </>
      );
    case 2:
      return (
        <>
          {form.parties.map((p, i) =>
            p.role === "WORKER" ? (
              <p key={p.id} className="text-ink-muted">
                {t("partnership.laborOnly", { name: p.fullName || p.id })}
              </p>
            ) : (
              <div key={p.id} className="flex flex-col gap-2 rounded border border-line p-3">
                <p className="font-semibold">{p.fullName || p.id}</p>
                {p.capital.map((c, k) => (
                  <div key={k} className="grid items-end gap-2 border-b border-line pb-3 sm:grid-cols-[1fr_1fr_auto]">
                    <Field label={t("partnership.capitalKind")}>
                      <select className="field" value={c.kind} onChange={(e) => party(i, { capital: p.capital.map((x, j) => (j === k ? { ...x, kind: e.target.value } : x)) })}>
                        {CAPITAL_KINDS.map((ck) => (
                          <option key={ck} value={ck}>
                            {t(`partnership.capital.${ck}`)}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label={t("partnership.capitalWhat")} className="sm:order-last sm:col-span-3">
                      <input className="field" value={c.description} onChange={(e) => party(i, { capital: p.capital.map((x, j) => (j === k ? { ...x, description: e.target.value } : x)) })} />
                    </Field>
                    <Field label={t(c.kind === "EQUIPMENT" ? "partnership.agreedPrice" : "common.amount")}>
                      <AmountInput value={c.amount} onChange={(e) => party(i, { capital: p.capital.map((x, j) => (j === k ? { ...x, amount: e.target.value } : x)) })} />
                    </Field>
                    <button type="button" className="btn-ghost px-3 py-2 text-sm" onClick={() => party(i, { capital: p.capital.filter((_, j) => j !== k) })}>
                      ×
                    </button>
                  </div>
                ))}
                <button type="button" className="btn-ghost self-start text-sm" onClick={() => party(i, { capital: [...p.capital, { kind: "MONEY", description: "", amount: "" }] })}>
                  + {t("partnership.addCapital")}
                </button>
                {dto?.parties.find((x) => x.id === p.id) && <p className="text-sm text-ink-muted">{t("partnership.capitalTotal", { amount: dto.parties.find((x) => x.id === p.id)?.capital.formatted ?? "" })}</p>}
              </div>
            ),
          )}
        </>
      );
    case 3:
      return (
        <>
          <NaToggle a={form.duties} onChange={(duties) => set({ duties })} />
          {form.duties.mode === "ANSWERED" && (
            <>
              <p className="text-sm text-ink-muted">{t("partnership.dutiesHint")}</p>
              {form.duties.value.map((d, k) => {
                const upd = (patch: Partial<DutyForm>) => set({ duties: { ...form.duties, value: form.duties.value.map((x, j) => (j === k ? { ...x, ...patch } : x)) } });
                return (
                  <div key={d.id} className="grid items-end gap-2 rounded border border-line p-3 sm:grid-cols-2">
                    <Field label={t("partnership.dutyTitle")}>
                      <input className="field" value={d.title} onChange={(e) => upd({ title: e.target.value })} />
                    </Field>
                    <PartySelect form={form} label={t("partnership.dutyOwner")} value={d.owner} onChange={(owner) => upd({ owner })} />
                    <Field label={t("partnership.breach")} className="sm:col-span-2">
                      <input className="field" placeholder={t("partnership.breachPlaceholder")} value={d.breach} onChange={(e) => upd({ breach: e.target.value })} />
                    </Field>
                  </div>
                );
              })}
              <button
                type="button"
                className="btn-ghost self-start"
                onClick={() => set({ duties: { ...form.duties, value: [...form.duties.value, { id: `d${form.duties.value.length + 1}`, title: "", owner: "", breach: "" }] } })}
              >
                + {t("partnership.addDuty")}
              </button>
            </>
          )}
        </>
      );
    case 4:
      return (
        <>
          <div className="flex flex-col gap-2 text-sm">
            {(["SHARE", "FIXED"] as const).map((m) => (
              <label key={m} className="flex items-center gap-2">
                <input type="radio" checked={form.profitMode === m} onChange={() => set({ profitMode: m })} />
                {t(`partnership.profitMode.${m}`)}
              </label>
            ))}
          </div>
          {form.profitMode === "FIXED" ? (
            <div role="alert" className="card flex flex-col gap-2 border-danger">
              <p className="font-semibold text-danger">{t("error.GUARANTEED_RETURN_FORBIDDEN")}</p>
              <p className="text-sm">{t("partnership.fixedExplain")}</p>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {form.parties.map((p, i) => (
                <Field key={p.id} label={t("partnership.shareOf", { name: p.fullName || p.id })}>
                  <input className="field tabular-nums" inputMode="decimal" value={p.share} onChange={(e) => party(i, { share: e.target.value })} />
                </Field>
              ))}
            </div>
          )}
          <p className="text-sm text-ink-muted">{t("partnership.shareHint")}</p>
        </>
      );
    case 5:
      return (
        <>
          <p>{t(`partnership.loss.${form.kind}`)}</p>
          {dto && (
            <ul className="text-sm">
              {dto.parties.map((x) => (
                <li key={x.id}>
                  {x.fullName}: <span className="font-semibold tabular-nums">{x.lossShare ?? "—"}</span>
                </li>
              ))}
            </ul>
          )}
          {form.kind === "MUDARABA" && (
            <Field label={t("partnership.negligence")}>
              <textarea className="field" rows={2} value={form.negligence} onChange={(e) => set({ negligence: e.target.value })} />
            </Field>
          )}
        </>
      );
    case 6:
      return (
        <>
          <NaToggle a={form.custody} onChange={(custody) => set({ custody })} />
          {form.custody.mode === "ANSWERED" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("partnership.custodyWhere")} className="sm:col-span-2">
                <input className="field" value={form.custody.value.location} onChange={(e) => set({ custody: { ...form.custody, value: { ...form.custody.value, location: e.target.value } } })} />
              </Field>
              <PartySelect form={form} label={t("partnership.keeper")} value={form.custody.value.keeper} onChange={(keeper) => set({ custody: { ...form.custody, value: { ...form.custody.value, keeper } } })} />
              <Field label={t("partnership.reviewDays")}>
                <input className="field tabular-nums" inputMode="numeric" value={form.custody.value.review} onChange={(e) => set({ custody: { ...form.custody, value: { ...form.custody.value, review: e.target.value } } })} />
              </Field>
            </div>
          )}
        </>
      );
    case 7:
      return <ExitStep form={form} set={set} dto={dto} />;
    case 8:
      return (
        <>
          <NaToggle a={form.arbiter} onChange={(arbiter) => set({ arbiter })} />
          {form.arbiter.mode === "ANSWERED" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("partnership.arbiter")}>
                <input className="field" value={form.arbiter.value.name} onChange={(e) => set({ arbiter: { ...form.arbiter, value: { ...form.arbiter.value, name: e.target.value } } })} />
              </Field>
              <Field label={t("partnership.arbiterRole")}>
                <input className="field" value={form.arbiter.value.role} onChange={(e) => set({ arbiter: { ...form.arbiter, value: { ...form.arbiter.value, role: e.target.value } } })} />
              </Field>
            </div>
          )}
          <p className="text-sm text-ink-muted">{t("partnership.arbiterHint")}</p>
          <h3 className="font-semibold">{t("partnership.witnesses")}</h3>
          {form.witnesses.map((w, k) => (
            <input key={k} aria-label={t("partnership.witnessN", { n: k + 1 })} className="field" value={w} onChange={(e) => set({ witnesses: form.witnesses.map((x, j) => (j === k ? e.target.value : x)) })} />
          ))}
          <button type="button" className="btn-ghost self-start" onClick={() => set({ witnesses: [...form.witnesses, ""] })}>
            + {t("partnership.addWitness")}
          </button>
        </>
      );
    case 9:
      return (
        <>
          <NaToggle a={form.term} onChange={(term) => set({ term })} />
          {form.term.mode === "ANSWERED" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("partnership.from")}>
                <input className="field tabular-nums" placeholder="01.11.2026" value={form.term.value.from} onChange={(e) => set({ term: { ...form.term, value: { ...form.term.value, from: e.target.value } } })} />
              </Field>
              <Field label={t("partnership.months")}>
                <input className="field tabular-nums" inputMode="numeric" value={form.term.value.months} onChange={(e) => set({ term: { ...form.term, value: { ...form.term.value, months: e.target.value } } })} />
              </Field>
              <Field label={t("partnership.reviewOn")}>
                <input className="field tabular-nums" placeholder="01.11.2027" value={form.term.value.review} onChange={(e) => set({ term: { ...form.term, value: { ...form.term.value, review: e.target.value } } })} />
              </Field>
            </div>
          )}
        </>
      );
    default:
      return null;
  }
}

function ExitStep({ form, set, dto }: { form: Form; set: (p: Partial<Form>) => void; dto: PartnershipDto | null }) {
  const { t } = useTranslation();
  const e = form.exit;
  const upd = (patch: Partial<Form["exit"]["value"]>) => set({ exit: { ...e, value: { ...e.value, ...patch } } });
  const b = form.buyout;
  const ub = (patch: Partial<BuyoutForm>) => b && set({ buyout: { ...b, ...patch } });
  const seller = form.parties.find((p) => p.role !== "WORKER" && !p.isMe) ?? form.parties[0];
  const buyer = form.parties.find((p) => p.id !== seller?.id && p.role !== "CAPITAL_PROVIDER") ?? form.parties[1];
  return (
    <>
      <NaToggle a={e} onChange={(exit) => set({ exit })} />
      {e.mode === "ANSWERED" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("partnership.notice")}>
            <input className="field tabular-nums" inputMode="numeric" value={e.value.notice} onChange={(x) => upd({ notice: x.target.value })} />
          </Field>
          <Field label={t("partnership.valuation")}>
            <input className="field" value={e.value.valuation} onChange={(x) => upd({ valuation: x.target.value })} />
          </Field>
          <Field label={t("partnership.payout")}>
            <input className="field" value={e.value.payout} onChange={(x) => upd({ payout: x.target.value })} />
          </Field>
          <Field label={t("partnership.assets")}>
            <input className="field" value={e.value.assets} onChange={(x) => upd({ assets: x.target.value })} />
          </Field>
        </div>
      )}
      <div className="flex flex-col gap-3 rounded border border-line p-3">
        <label className="flex items-center gap-2 font-semibold">
          <input
            type="checkbox"
            checked={b !== null}
            onChange={(x) => set({ buyout: x.target.checked ? { seller: seller?.id ?? "", buyer: buyer?.id ?? "", units: "10", per: "1", period: "1", start: "", profit: "" } : null })}
          />
          {t("partnership.buyout")}
        </label>
        <p className="text-sm text-ink-muted">{t("partnership.buyoutHint")}</p>
        {b && (
          <div className="grid gap-3 sm:grid-cols-2">
            <PartySelect form={form} label={t("partnership.seller")} value={b.seller} onChange={(v) => ub({ seller: v })} />
            <PartySelect form={form} label={t("partnership.buyer")} value={b.buyer} onChange={(v) => ub({ buyer: v })} />
            <Field label={t("partnership.units")}>
              <input className="field tabular-nums" inputMode="numeric" value={b.units} onChange={(x) => ub({ units: x.target.value })} />
            </Field>
            <Field label={t("partnership.unitsPer")}>
              <input className="field tabular-nums" inputMode="numeric" value={b.per} onChange={(x) => ub({ per: x.target.value })} />
            </Field>
            <Field label={t("partnership.periodMonths")}>
              <input className="field tabular-nums" inputMode="numeric" value={b.period} onChange={(x) => ub({ period: x.target.value })} />
            </Field>
            <Field label={t("partnership.buyoutStart")}>
              <input className="field tabular-nums" placeholder="30.11.2026" value={b.start} onChange={(x) => ub({ start: x.target.value })} />
            </Field>
            <Field label={t("partnership.expectedProfit")} className="sm:col-span-2">
              <AmountInput value={b.profit} onChange={(x) => ub({ profit: x.target.value })} />
            </Field>
          </div>
        )}
        {dto?.buyout && <BuyoutTable dto={dto} />}
      </div>
    </>
  );
}

/** Buyout jadvali va qolgan ulush (uy/SPEC 2E.2): kenglik yadro bergan bp dan. */
function BuyoutTable({ dto }: { dto: PartnershipDto }) {
  const { t } = useTranslation();
  const b = dto.buyout;
  if (!b) return null;
  if (b.error) return <p className="text-sm text-danger">{t(`error.${b.error}`, { defaultValue: t("error.GENERIC") })}</p>;
  const name = (id: string) => dto.parties.find((p) => p.id === id)?.fullName ?? id;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        {t("partnership.buyoutSummary", { buyer: name(b.buyerPartyId), seller: name(b.sellerPartyId), n: b.rows.length, end: b.endDate ?? "" })}
      </p>
      {b.buyerProfit && <p className="text-sm text-ink-muted">{t("partnership.buyerProfit", { amount: b.buyerProfit.formatted })}</p>}
      <table className="w-full text-sm tabular-nums">
        <thead className="text-left text-ink-muted">
          <tr>
            <th className="py-1">№</th>
            <th>{t("partnership.date")}</th>
            <th className="text-right">{t("partnership.payment")}</th>
            <th className="w-2/5 pl-3 font-normal">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm bg-chart2" />
                {name(b.sellerPartyId)}
              </span>{" "}
              /{" "}
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-sm bg-chart1" />
                {name(b.buyerPartyId)}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {b.rows.map((r) => (
            <tr key={r.period} className="border-t border-line">
              <td className="py-1">{r.period}</td>
              <td>{r.date}</td>
              <td className={`text-right ${r.exceedsShare ? "text-warn" : ""}`}>
                {r.payment.formatted}
                {r.exceedsShare ? " ⚠" : ""}
              </td>
              <td className="pl-3">
                <div className="flex h-3 overflow-hidden rounded bg-line" title={`${r.sellerPercent} / ${r.buyerPercent}`}>
                  <div className="bg-chart2" style={{ width: `${r.sellerBp / 100}%` }} />
                  <div className="bg-chart1" style={{ width: `${r.buyerBp / 100}%` }} />
                </div>
                <span className="text-xs text-ink-muted">
                  {r.sellerPercent} / {r.buyerPercent}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {b.rows.some((r) => r.exceedsShare) && <p className="text-sm text-warn">{t("partnership.exceedsShare")}</p>}
      <p className="text-xs text-ink-muted">{t("partnership.buyoutPricing")}</p>
    </div>
  );
}

function CheckPanel({ p }: { p: PartnershipDto }) {
  const { t, i18n } = useTranslation();
  const label = (code: string) => (i18n.exists(`partnership.check.${code}`) ? t(`partnership.check.${code}`) : t(`error.${code}`, { defaultValue: code }));
  if (p.check.errors.length === 0 && p.check.warnings.length === 0) {
    return p.check.canSign ? <p className="text-sm text-accent-text">{t("partnership.readyToSign")}</p> : null;
  }
  return (
    <div className="card flex flex-col gap-1 text-sm">
      {p.check.errors.map((c) => (
        <p key={c} className="text-danger">
          • {label(c)}
        </p>
      ))}
      {p.check.warnings.map((c) => (
        <p key={c} className="text-warn">
          • {label(c)}
        </p>
      ))}
    </div>
  );
}

function SignStep({ spaceId, p }: { spaceId: string; p: PartnershipDto }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [signing, setSigning] = useState<{ key: string; name: string } | null>(null);
  const sign = useMutation({
    mutationFn: (strokes: Stroke[]) => call(commands.signPartnership(spaceId, p.id, { signerKey: signing?.key ?? "", strokes })),
    onSuccess: (dto) => {
      qc.setQueryData(keys.partnership(spaceId, p.id), dto);
      setSigning(null);
    },
  });
  const pdf = useMutation({ mutationFn: () => call(commands.exportPartnershipContract(spaceId, p.id)) });
  return (
    <div className="card flex flex-col gap-4">
      <h2 className="text-lg font-semibold">{t("partnership.step.10")}</h2>
      <p className="text-sm text-ink-muted">{t("partnership.signHint")}</p>
      {!p.check.canSign && <p className="text-sm text-danger">{t("partnership.signBlocked")}</p>}
      <CheckPanel p={p} />
      <p className="text-sm">
        {p.version != null ? t("partnership.versionNo", { n: p.version }) : t("partnership.newVersion")} · {t("partnership.hashCode", { code: p.hashCode })}
      </p>
      <ul className="flex flex-col gap-2">
        {p.signers.map((s) => (
          <li key={s.key} className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-2">
            <span>
              <span className="text-sm text-ink-muted">{t(`partnership.signer.${s.role}`)}</span>
              <br />
              {s.name}
            </span>
            {s.signedAt ? (
              <span className="flex items-center gap-3">
                {s.svg && <img alt={t("partnership.signatureOf", { name: s.name })} className="h-10 rounded bg-[#FAF9F5] px-1" src={`data:image/svg+xml;utf8,${encodeURIComponent(s.svg)}`} />}
                <span className="text-sm text-accent-text">✓ {s.signedAt}</span>
              </span>
            ) : (
              p.status !== "CLOSED" && (
                <button className="btn-ghost px-3 py-1 text-sm" disabled={!p.check.canSign} onClick={() => setSigning({ key: s.key, name: s.name })}>
                  {t("partnership.signAs", { name: s.name })}
                </button>
              )
            )}
          </li>
        ))}
      </ul>
      {p.allSigned && <p className="text-sm text-accent-text">{t("partnership.allSigned", { n: p.version ?? 0 })}</p>}
      <ErrorText error={sign.error ?? pdf.error} />
      <button className="btn-ghost self-start" onClick={() => pdf.mutate()}>
        {t("partnership.pdf")}
      </button>
      {p.history.length > 0 && (
        <div className="text-sm">
          <h3 className="font-semibold">{t("partnership.history")}</h3>
          {p.history.map((h) => (
            <p key={h.no} className="text-ink-muted">
              {t("partnership.historyRow", { n: h.no, date: h.createdOn, signed: h.signed, required: h.required })}
              {h.inForce ? ` · ${t("partnership.inForce")}` : ""}
            </p>
          ))}
        </div>
      )}
      {signing && <SignaturePad name={signing.name} busy={sign.isPending} onCancel={() => setSigning(null)} onSave={(s) => sign.mutate(s)} />}
    </div>
  );
}

function GateCard({ g }: { g: GateDto }) {
  const { t } = useTranslation();
  return (
    <div className={`card flex flex-col gap-2 ${g.open ? "border-accent" : "border-warn"}`}>
      <h3 className="font-semibold">{t(g.open ? "partnership.gate.open" : "partnership.gate.closed")}</h3>
      <p className="text-sm">
        {g.coverageMonths != null
          ? t("partnership.gate.coverage", { months: g.coverageMonths, required: g.requiredMonths, balance: g.balance.formatted, essentials: g.monthlyEssentials?.formatted ?? "" })
          : t("partnership.gate.noHistory", { balance: g.balance.formatted })}
      </p>
      {g.reasons.map((r) => (
        <p key={r} className="text-sm text-warn">
          • {t(`partnership.gate.reason.${r}`)}
        </p>
      ))}
    </div>
  );
}

function StartStep({ spaceId, p }: { spaceId: string; p: PartnershipDto }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const done = (dto: PartnershipDto) => qc.setQueryData(keys.partnership(spaceId, p.id), dto);
  const ack = useMutation({ mutationFn: () => call(commands.acknowledgeNotDebt(spaceId, p.id)), onSuccess: done });
  const consent = useMutation({ mutationFn: (m: string) => call(commands.consentPartnership(spaceId, p.id, m)), onSuccess: done });
  const activate = useMutation({ mutationFn: () => call(commands.activatePartnership(spaceId, p.id)), onSuccess: done });
  const close = useMutation({ mutationFn: () => call(commands.closePartnership(spaceId, p.id)), onSuccess: done });
  return (
    <div className="card flex flex-col gap-4">
      <h2 className="text-lg font-semibold">{t("partnership.step.11")}</h2>
      {p.meProvidesCapital && (
        <>
          <p className="text-sm text-ink-muted">{t("partnership.gateHint")}</p>
          {p.gate && <GateCard g={p.gate} />}
        </>
      )}
      {p.meReceivesCapital && p.consent && (
        <div className="flex flex-col gap-3">
          <div className="card flex flex-col gap-2 border-accent/40">
            <p className="font-semibold">{t("partnership.notDebt.title")}</p>
            <p className="text-sm">{t(`partnership.notDebt.${p.kind}`)}</p>
            {p.consent.notDebtAckOn ? (
              <p className="text-sm text-accent-text">✓ {t("partnership.notDebt.acked", { date: showDate(p.consent.notDebtAckOn) })}</p>
            ) : (
              <button className="btn-ghost self-start" disabled={ack.isPending} onClick={() => ack.mutate()}>
                {t("partnership.notDebt.ack")}
              </button>
            )}
          </div>
          <p className="text-sm text-ink-muted">{t("partnership.consentHint")}</p>
          {p.consent.adults.map((a) => (
            <div key={a.memberId} className="flex items-center justify-between border-b border-line pb-2">
              <span>{a.name}</span>
              {a.agreedOn ? (
                <span className="text-sm text-accent-text">✓ {t("partnership.agreedOn", { date: showDate(a.agreedOn) })}</span>
              ) : (
                <button className="btn-ghost px-3 py-1 text-sm" disabled={p.status !== "SIGNED" || consent.isPending} onClick={() => consent.mutate(a.memberId)}>
                  {t("partnership.consentAs", { name: a.name })}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {p.activateBlocker && p.status !== "ACTIVE" && p.status !== "CLOSED" && <p className="text-sm text-warn">{t(`partnership.blocker.${p.activateBlocker}`)}</p>}
      <ErrorText error={ack.error ?? consent.error ?? activate.error ?? close.error} />
      {p.status === "SIGNED" && (
        <button className="btn-primary self-start" disabled={!p.canActivate || activate.isPending} onClick={() => activate.mutate()}>
          {t("partnership.activate")}
        </button>
      )}
      {p.status === "ACTIVE" && (
        <>
          <p className="text-sm text-accent-text">{t("partnership.activeNote", { n: p.signedVersion ?? 0 })}</p>
          <button className="btn-ghost self-start" disabled={close.isPending} onClick={() => close.mutate()}>
            {t("partnership.close")}
          </button>
        </>
      )}
    </div>
  );
}
