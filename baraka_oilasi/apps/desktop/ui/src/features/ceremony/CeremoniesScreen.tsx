import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { type CeremonyDto, commands, type GoalDto, type ScenarioDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { showDate, showMonth } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const KINDS = ["TOY", "BESHIK_TOY", "SUNNAT_TOY", "MARAKA", "OTHER"] as const;
const SOURCES = ["SAVINGS", "FAMILY", "EXPECTED_GIFTS", "DEBT"] as const;
const PRESSURE_CARDS = 4;
/** Stsenariylar yonma-yon (Tailwind dinamik klass yaratmaydi — aniq roʻyxat). */
const COLS: Record<number, string> = { 2: "lg:grid-cols-2", 3: "lg:grid-cols-3" };

const optional = (v: string) => (v.trim() === "" ? null : v);
/** Mehmonlar soni — pul emas, butun son; notoʻgʻri qiymat yadroga yuborilmaydi. */
const toGuests = (v: string) => {
  if (!/^\d{1,6}$/.test(v.trim())) throw new CoreError({ code: "INVALID_GUESTS", field: "guests" });
  return Number(v.trim());
};

/**
 * Toʻy va marosimlarni rejalash (uy/SPEC 2D.8): 2–3 stsenariy yonma-yon, moliyalash manbalari,
 * qarz boʻlsa — «Buni qarzsiz qanday oʻtkazamiz?» oilaviy muhokamasi, smeta PDF.
 */
export function CeremoniesScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [openId, setOpenId] = useState<string | null>(null);
  const list = useQuery({ queryKey: keys.ceremonies(spaceId), queryFn: () => call(commands.ceremonies(spaceId)) });
  if (openId) return <CeremonyDetail spaceId={spaceId} id={openId} onBack={() => setOpenId(null)} />;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("ceremony.title")}</h1>
      <PressureCard />
      <ErrorText error={list.error} />
      {(list.data ?? []).map((c) => (
        <button key={c.id} className="card flex flex-wrap items-center justify-between gap-3 text-left hover:border-accent" onClick={() => setOpenId(c.id)}>
          <span>
            <span className="text-lg font-semibold">{c.title}</span>
            <span className="ml-2 text-sm text-ink-muted">
              {t(`ceremony.kind.${c.kind}`)}{c.plannedOn ? ` · ${showDate(c.plannedOn)}` : ""}
            </span>
          </span>
          <span className="flex items-center gap-2 text-sm">
            {c.hasDebt && <span className="rounded border border-danger px-2 py-0.5 text-xs text-danger">{t("ceremony.withDebt")}</span>}
            <span className="rounded border border-line px-2 py-0.5 text-xs text-ink-muted">{t(`ceremony.status.${c.status}`)}</span>
            <span className="font-semibold tabular-nums text-accent-text">{c.total?.formatted ?? ""}</span>
          </span>
        </button>
      ))}
      <CreateForm spaceId={spaceId} onCreated={setOpenId} />
      <GiftGoals spaceId={spaceId} />
    </section>
  );
}

function PressureCard({ seed = 0 }: { seed?: number }) {
  const { t } = useTranslation();
  const [i, setI] = useState(seed % PRESSURE_CARDS);
  return (
    <aside className="card flex flex-col gap-2 border-accent/40">
      <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
      <p>{t(`ceremony.pressure.${i}`)}</p>
      <button className="self-start text-sm text-ink-muted underline" onClick={() => setI((v) => (v + 1) % PRESSURE_CARDS)}>
        {t("ceremony.pressure.next")}
      </button>
    </aside>
  );
}

function CreateForm({ spaceId, onCreated }: { spaceId: string; onCreated: (id: string) => void }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ kind: "TOY", title: "", date: "", scenario: "", guests: "" });
  const create = useMutation({
    mutationFn: () =>
      call(
        commands.createCeremony(spaceId, {
          kind: f.kind,
          title: f.title,
          plannedOn: optional(f.date),
          scenarioName: f.scenario,
          guests: toGuests(f.guests),
        }),
      ),
    onSuccess: (c) => onCreated(c.id),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit} aria-label={t("ceremony.new")}>
      <h2 className="text-lg font-semibold md:col-span-2">{t("ceremony.new")}</h2>
      <label>
        <span className="label">{t("ceremony.kindLabel")}</span>
        <select className="field" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
          {KINDS.map((k) => <option key={k} value={k}>{t(`ceremony.kind.${k}`)}</option>)}
        </select>
      </label>
      <label>
        <span className="label">{t("ceremony.name")}</span>
        <input className="field" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("ceremony.date")}</span>
        <input className="field tabular-nums" inputMode="numeric" placeholder="20.05.2027" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("ceremony.firstScenario")}</span>
        <input className="field" placeholder={t("ceremony.scenarioHint")} value={f.scenario} onChange={(e) => setF({ ...f, scenario: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("ceremony.guests")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={f.guests} onChange={(e) => setF({ ...f, guests: e.target.value })} required />
      </label>
      <div className="md:col-span-2"><ErrorText error={create.error} /></div>
      <div><button className="btn-primary" disabled={create.isPending}>{t("ceremony.create")}</button></div>
    </form>
  );
}

function CeremonyDetail({ spaceId, id, onBack }: { spaceId: string; id: string; onBack: () => void }) {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: keys.ceremony(spaceId, id), queryFn: () => call(commands.ceremony(spaceId, id)) });
  const confirm = useMutation({ mutationFn: () => call(commands.confirmCeremony(spaceId, id)) });
  const reopen = useMutation({ mutationFn: () => call(commands.reopenCeremony(spaceId, id)) });
  const pdf = useMutation({ mutationFn: () => call(commands.exportCeremonyEstimate(spaceId, id)) });
  const add = useMutation({
    mutationFn: (copyFrom: string | null) =>
      call(commands.addScenario(spaceId, id, { name: t("ceremony.newScenario"), guests: 0, copyFrom })),
  });
  const c = q.data;
  if (!c) return <ErrorText error={q.error} />;
  const locked = c.status === "CONFIRMED";
  const selected = c.scenarios.find((s) => s.selected);
  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-ghost px-3 py-1 text-sm" onClick={onBack}>← {t("ceremony.back")}</button>
        <h1 className="text-2xl font-semibold">{c.title}</h1>
        <span className="text-ink-muted">{t(`ceremony.kind.${c.kind}`)}{c.plannedOn ? ` · ${showDate(c.plannedOn)}` : ""}</span>
        <span className={`rounded border px-2 py-0.5 text-xs ${locked ? "border-accent text-accent-text" : "border-line text-ink-muted"}`}>{t(`ceremony.status.${c.status}`)}</span>
      </div>
      <Settings spaceId={spaceId} c={c} />
      {c.giftsWarning && <p role="note" className="rounded-md border border-warn p-3 text-sm">{t("ceremony.giftsWarning")}</p>}

      <div className={`grid gap-4 ${COLS[c.scenarios.length] ?? ""}`}>
        {c.scenarios.map((s) => <Scenario key={s.id} spaceId={spaceId} ceremonyId={id} s={s} locked={locked} canDelete={c.scenarios.length > 1} />)}
      </div>
      {!locked && c.scenarios.length < 3 && (
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => add.mutate(selected?.id ?? null)}>{t("ceremony.addScenarioCopy")}</button>
          <button className="btn-ghost" onClick={() => add.mutate(null)}>{t("ceremony.addScenarioEmpty")}</button>
        </div>
      )}
      <ErrorText error={add.error} />

      {(c.discussion.required || c.discussion.answers.some((a) => a.note !== "")) && <Discussion spaceId={spaceId} c={c} />}

      <div className="card flex flex-col gap-3">
        {c.confirmBlocker && <p className="text-sm text-ink-muted">{t(`ceremony.blocker.${c.confirmBlocker}`)}</p>}
        <div className="flex flex-wrap gap-2">
          {!locked && <button className="btn-primary" disabled={!c.canConfirm || confirm.isPending} onClick={() => confirm.mutate()}>{t("ceremony.confirm")}</button>}
          {c.status !== "DRAFT" && <button className="btn-ghost" onClick={() => reopen.mutate()}>{t("ceremony.reopen")}</button>}
          <button className="btn-ghost" disabled={pdf.isPending} onClick={() => pdf.mutate()}>{t("ceremony.pdf")}</button>
        </div>
        <ErrorText error={confirm.error ?? reopen.error ?? pdf.error} />
      </div>
      <PressureCard seed={c.title.length} />
    </section>
  );
}

function Settings({ spaceId, c }: { spaceId: string; c: CeremonyDto }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ title: c.title, date: c.plannedOn ? showDate(c.plannedOn) : "", capacity: c.capacitySource === "MANUAL" ? c.monthlyCapacity.plain : "" });
  const save = useMutation({
    mutationFn: () => call(commands.updateCeremony(spaceId, c.id, { title: f.title, plannedOn: optional(f.date), monthlyCapacity: optional(f.capacity) })),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid items-end gap-3 md:grid-cols-[minmax(0,1fr)_8rem_10rem_auto]" onSubmit={submit}>
      <label>
        <span className="label">{t("ceremony.name")}</span>
        <input className="field text-lg" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required />
      </label>
      <label>
        <span className="label">{t("ceremony.date")}</span>
        <input className="field text-lg tabular-nums" inputMode="numeric" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} />
      </label>
      <label>
        <span className="label">{t("ceremony.capacity")}</span>
        <AmountInput placeholder={c.monthlyCapacity.plain} value={f.capacity} onChange={(e) => setF({ ...f, capacity: e.target.value })} />
      </label>
      <button className="btn-ghost">{t("common.save")}</button>
      <p className="text-xs text-ink-muted md:col-span-4">{t(`ceremony.capacitySource.${c.capacitySource}`, { amount: c.monthlyCapacity.formatted })}</p>
      <div className="md:col-span-4"><ErrorText error={save.error} /></div>
    </form>
  );
}

function Scenario({ spaceId, ceremonyId, s, locked, canDelete }: { spaceId: string; ceremonyId: string; s: ScenarioDto; locked: boolean; canDelete: boolean }) {
  const { t } = useTranslation();
  const [head, setHead] = useState({ name: s.name, guests: String(s.guests) });
  const [l, setL] = useState({ title: "", kind: "ONE_OFF", amount: "", source: "SAVINGS" });
  const select = useMutation({ mutationFn: () => call(commands.selectScenario(spaceId, ceremonyId, s.id)) });
  const rename = useMutation({
    mutationFn: () => call(commands.updateScenario(spaceId, ceremonyId, s.id, { name: head.name, guests: toGuests(head.guests), copyFrom: null })),
  });
  const remove = useMutation({ mutationFn: () => call(commands.deleteScenario(spaceId, ceremonyId, s.id)) });
  const addLine = useMutation({
    mutationFn: () => call(commands.addCeremonyLine(spaceId, ceremonyId, s.id, l)),
    onSuccess: () => setL({ ...l, title: "", amount: "" }),
  });
  const delLine = useMutation({ mutationFn: (lineId: string) => call(commands.deleteCeremonyLine(spaceId, ceremonyId, lineId)) });
  const submitHead = (e: FormEvent) => {
    e.preventDefault();
    rename.mutate();
  };
  const submitLine = (e: FormEvent) => {
    e.preventDefault();
    addLine.mutate();
  };
  return (
    <article className={`card flex min-w-0 flex-col gap-3 ${s.selected ? "border-accent" : ""}`} aria-label={s.name}>
      <form className="grid grid-cols-[1fr_auto] items-end gap-2" onSubmit={submitHead}>
        <label className="col-span-2">
          <span className="label">{t("ceremony.scenario")}</span>
          <input className="field font-semibold" value={head.name} disabled={locked} onChange={(e) => setHead({ ...head, name: e.target.value })} />
        </label>
        <label className={locked ? "col-span-2" : undefined}>
          <span className="label">{t("ceremony.guests")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={head.guests} disabled={locked} onChange={(e) => setHead({ ...head, guests: e.target.value })} />
        </label>
        {!locked && <button className="btn-ghost px-3 py-2 text-sm">{t("common.save")}</button>}
      </form>
      <ul className="flex flex-col gap-1 text-sm">
        {s.lines.map((x) => (
          <li key={x.id} className="flex items-start justify-between gap-2 border-b border-line py-1">
            <span className="min-w-0">
              {x.title}
              <span className="block text-xs text-ink-muted">
                {x.kind === "PER_GUEST" ? `${x.amount.formatted} × ${s.guests}` : t("ceremony.oneOff")} · {t(`ceremony.source.${x.source}`)}
              </span>
            </span>
            <span className={`flex items-center gap-2 tabular-nums ${x.source === "DEBT" ? "text-danger" : ""}`}>
              {x.total.formatted}
              {!locked && <button className="text-ink-muted" aria-label={t("ceremony.deleteLine", { title: x.title })} onClick={() => delLine.mutate(x.id)}>×</button>}
            </span>
          </li>
        ))}
      </ul>
      {!locked && (
        <form className="grid gap-2 rounded-md border border-line p-2 text-sm" onSubmit={submitLine} aria-label={t("ceremony.addLine")}>
          <input className="field" placeholder={t("ceremony.lineTitle")} aria-label={t("ceremony.lineTitle")} value={l.title} onChange={(e) => setL({ ...l, title: e.target.value })} required />
          <div className="grid grid-cols-2 gap-2">
            <select className="field" aria-label={t("ceremony.lineKind")} value={l.kind} onChange={(e) => setL({ ...l, kind: e.target.value })}>
              <option value="ONE_OFF">{t("ceremony.oneOff")}</option>
              <option value="PER_GUEST">{t("ceremony.perGuest")}</option>
            </select>
            <select className="field" aria-label={t("ceremony.lineSource")} value={l.source} onChange={(e) => setL({ ...l, source: e.target.value })}>
              {SOURCES.map((x) => <option key={x} value={x}>{t(`ceremony.source.${x}`)}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <input className="field tabular-nums" inputMode="decimal" placeholder={t("common.amount")} aria-label={t("ceremony.lineAmount")} value={l.amount} onChange={(e) => setL({ ...l, amount: e.target.value })} required />
            <button className="btn-ghost px-3">{t("goals.add")}</button>
          </div>
          {l.source === "DEBT" && <p className="text-xs text-danger">{t("ceremony.debtHint")}</p>}
        </form>
      )}
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm tabular-nums">
        {SOURCES.map((x) => {
          const v = { SAVINGS: s.bySource.savings, FAMILY: s.bySource.family, EXPECTED_GIFTS: s.bySource.expectedGifts, DEBT: s.bySource.debt }[x];
          return (
            <div key={x} className="contents">
              <dt className="text-ink-muted">{t(`ceremony.source.${x}`)}</dt>
              <dd className={`text-right ${x === "DEBT" && s.hasDebt ? "text-danger" : ""}`}>{v.formatted}</dd>
            </div>
          );
        })}
        <dt className="font-semibold">{t("ceremony.total")}</dt>
        <dd className="text-right text-lg font-semibold text-accent-text">{s.total.formatted}</dd>
      </dl>
      <p className="text-sm">
        {!s.hasDebt
          ? t("ceremony.noDebt")
          : s.notRepayable
            ? <span className="text-danger">{t("ceremony.notRepayable")}</span>
            : t("ceremony.payoff", { count: s.payoffMonths ?? 0, date: s.payoffDate ? showMonth(s.payoffDate) : "" })}
      </p>
      {s.savedVsMax.minor !== "0" && (
        <p className="text-sm text-accent-text">
          {t("ceremony.saved", { amount: s.savedVsMax.formatted })}
          {s.goalEquivalents.map((g) => <span key={g.goalId} className="block">{t("ceremony.savedGoal", { title: g.title, percent: g.percent })}</span>)}
        </p>
      )}
      <div className="mt-auto flex flex-wrap gap-2">
        {s.selected ? <span className="text-sm font-semibold text-accent-text">✓ {t("ceremony.selected")}</span> : !locked && <button className="btn-ghost px-3 py-1 text-sm" onClick={() => select.mutate()}>{t("ceremony.select")}</button>}
        {!locked && canDelete && <button className="btn-ghost px-3 py-1 text-sm" onClick={() => remove.mutate()}>{t("ceremony.deleteScenario")}</button>}
      </div>
      <ErrorText error={select.error ?? rename.error ?? remove.error ?? addLine.error ?? delLine.error} />
    </article>
  );
}

function Discussion({ spaceId, c }: { spaceId: string; c: CeremonyDto }) {
  const { t } = useTranslation();
  const [answers, setAnswers] = useState(c.discussion.answers);
  const save = useMutation({ mutationFn: () => call(commands.saveDiscussion(spaceId, c.id, answers)) });
  const agree = useMutation({ mutationFn: (memberId: string) => call(commands.agreeDiscussion(spaceId, c.id, memberId)) });
  const locked = c.status === "CONFIRMED";
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="discussion-title">
      <h2 id="discussion-title" className="text-lg font-semibold">{t("ceremony.discussion")}</h2>
      <p className="text-sm text-ink-muted">{t("ceremony.discussionIntro")}</p>
      <form className="flex flex-col gap-3" onSubmit={submit}>
        {answers.map((a, i) => (
          <label key={a.key}>
            <span className="label">{t(`ceremony.question.${a.key}`)}</span>
            <textarea
              className="field min-h-16"
              value={a.note}
              disabled={locked}
              onChange={(e) => setAnswers(answers.map((x, j) => (j === i ? { ...x, note: e.target.value } : x)))}
            />
          </label>
        ))}
        {!locked && <button className="btn-ghost self-start">{t("ceremony.saveAnswers")}</button>}
      </form>
      <ul className="flex flex-col gap-2">
        {c.discussion.adults.map((m) => (
          <li key={m.memberId} className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2 text-sm">
            <span>{m.name}</span>
            {m.agreedOn ? (
              <span className="text-accent-text">✓ {t("ceremony.agreed", { date: showDate(m.agreedOn) })}</span>
            ) : (
              !locked && <button className="btn-ghost px-3 py-1 text-sm" onClick={() => agree.mutate(m.memberId)}>{t("ceremony.agree", { name: m.name })}</button>
            )}
          </li>
        ))}
      </ul>
      {c.status === "DISCUSSED" && <p className="text-sm text-accent-text">{t("ceremony.discussionDone")}</p>}
      <ErrorText error={save.error ?? agree.error} />
    </section>
  );
}

/** Toʻyona oʻrniga jamgʻarma (uy/SPEC 2D.8): yosh oila maqsadiga mehmonlar hissasi. */
function GiftGoals({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const overview = useQuery({ queryKey: keys.debts(spaceId), queryFn: () => call(commands.debtsOverview(spaceId)) });
  const goals = overview.data?.goals ?? [];
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="gift-title">
      <h2 id="gift-title" className="text-lg font-semibold">{t("ceremony.giftGoal")}</h2>
      <p className="text-sm text-ink-muted">{t("ceremony.giftGoalIntro")}</p>
      {goals.length === 0 && <p className="text-sm text-ink-muted">{t("ceremony.noGoals")}</p>}
      {goals.map((g) => <GiftGoal key={g.id} spaceId={spaceId} g={g} />)}
    </section>
  );
}

function GiftGoal({ spaceId, g }: { spaceId: string; g: GoalDto }) {
  const { t } = useTranslation();
  const [who, setWho] = useState("");
  const [amount, setAmount] = useState("");
  const [copied, setCopied] = useState(false);
  const add = useMutation({
    mutationFn: () => call(commands.addGoalContribution(spaceId, g.id, { contributor: who, amount, givenOn: null })),
    onSuccess: () => {
      setWho("");
      setAmount("");
    },
  });
  const share = t("ceremony.shareText", { title: g.title, target: g.target.formatted, collected: g.collected.formatted });
  const copy = () => {
    void navigator.clipboard?.writeText(share).then(() => setCopied(true));
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <div className="flex flex-col gap-2 rounded-md border border-line p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{g.title}</span>
        <span className="tabular-nums">
          {g.collected.formatted} / {g.target.formatted} · <span className="text-accent-text">{g.collectedPercent}%</span>
        </span>
      </div>
      {g.contributions.length > 0 && (
        <ul className="text-xs text-ink-muted">
          {g.contributions.map((x) => <li key={x.id}>{x.contributor} — {x.amount.formatted}, {showDate(x.givenOn)}</li>)}
        </ul>
      )}
      <form className="flex flex-wrap items-end gap-2" onSubmit={submit}>
        <input className="field min-w-40 flex-1" placeholder={t("ceremony.guestName")} aria-label={t("ceremony.guestName")} value={who} onChange={(e) => setWho(e.target.value)} required />
        <input className="field w-40 tabular-nums" inputMode="decimal" placeholder={t("common.amount")} aria-label={t("ceremony.giftAmount")} value={amount} onChange={(e) => setAmount(e.target.value)} required />
        <button className="btn-ghost">{t("goals.add")}</button>
      </form>
      <div className="flex flex-wrap items-center gap-2">
        <p className="flex-1 rounded bg-sidebar p-2 text-xs">{share}</p>
        <button className="btn-ghost px-3 py-1 text-xs" onClick={copy}>{copied ? t("ceremony.copied") : t("ceremony.copy")}</button>
      </div>
      <ErrorText error={add.error} />
    </div>
  );
}
