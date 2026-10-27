import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfHourDto, type MfLearningOverviewDto, type MfLearningPlanDto, type MfLearningResultDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";
import { useUi } from "../../state/ui";
import { ResultView } from "../learning/LearningScreen";
import { NEXT, STATUS_TONE } from "../learning/planStatus";
import { parseCount, showMinutes, toMinutes } from "../learning/time";

const GOALS = ["ABROAD", "HOME"] as const;
const PATHS = ["BOOK", "MENTOR", "COURSE", "PRACTICE"] as const;
const AREAS = ["WORK", "LANGUAGE", "DOCUMENTS", "OTHER"] as const;

/**
 * Musofir «O'zimga sarmoya» (8-tamoyil, musofir/SPEC 6A): bir soat qiymati ish valyutasida (uy
 * valyutasida — faqat kiritilgan kurs bilan), ikki maqsadli bilim rejasi (chet elda / uyda),
 * «Ilm zakoti» (hamyurtlarga yordam), kurs tekshiruvi (`jobAbroad` savoli bilan) va shu oy «Sarmoya»
 * qatori. Musofirning shaxsiy bo'limi; barcha summa yadrodan, UI faqat ko'rsatadi.
 */
export function MfLearningScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const openCourseCheck = useUi((s) => s.openCourseCheck);
  const o = useQuery({ queryKey: keys.mfLearning(spaceId), queryFn: () => call(commands.mfLearningOverview(spaceId, null)) });
  const [dialog, setDialog] = useState<"plan" | "teach" | null>(null);
  const data = o.error ? undefined : o.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("mfl.title")}</h1>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p>{t("mfl.intro")}</p>
        <p className="text-sm text-ink-muted">{t("mfl.example")}</p>
      </aside>
      <section aria-labelledby="mfl-tasks" className="card flex flex-col gap-2">
        <h2 id="mfl-tasks" className="text-lg font-semibold">
          {t("learn.tasks.title")}
        </h2>
        <ol className="list-decimal space-y-1 pl-5">
          {[1, 2, 3].map((n) => (
            <li key={n}>{t(`mfl.tasks.${n}`)}</li>
          ))}
        </ol>
      </section>
      <ErrorText error={o.error} />
      {data && <InvestCard data={data} />}
      {data && <HourCard key={data.hourValue?.id ?? "none"} spaceId={spaceId} data={data} />}
      {data && (
        <section aria-labelledby="mfl-plans" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="mfl-plans" className="text-xl font-semibold">
              {t("mfl.plans.title")}
            </h2>
            <button className="btn-primary" onClick={() => setDialog("plan")}>
              {t("learn.plans.new")}
            </button>
          </div>
          <p className="text-sm text-ink-muted">{t("mfl.plans.hint")}</p>
          {data.plans.length === 0 && <p className="card text-ink-muted">{t("mfl.plans.empty")}</p>}
          {data.plans.map((p) => (
            <PlanCard key={p.id} spaceId={spaceId} plan={p} />
          ))}
        </section>
      )}
      {data && <TeachingCard data={data} onAdd={() => setDialog("teach")} />}
      <section aria-labelledby="mfl-course" className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="mfl-course" className="text-lg font-semibold">
            {t("mfl.course.title")}
          </h2>
          <p className="text-sm text-ink-muted">{t("mfl.course.hint")}</p>
        </div>
        <button className="btn-ghost" onClick={openCourseCheck}>
          {t("learn.plan.checkCourse")}
        </button>
      </section>
      {dialog === "plan" && data && <MfPlanDialog spaceId={spaceId} data={data} onClose={() => setDialog(null)} />}
      {dialog === "teach" && <MfTeachingDialog spaceId={spaceId} onClose={() => setDialog(null)} />}
    </section>
  );
}

/** «Oʻzimga sarmoya: X — daromadning Y %» (ish valyutasida, bosh sahifadagi oy hisobi bilan bir xil). */
function InvestCard({ data }: { data: MfLearningOverviewDto }) {
  const { t } = useTranslation();
  const s = data.selfInvestment;
  return (
    <div className="card">
      <p className="text-sm text-ink-muted">{t("mfl.invest.title")}</p>
      <p data-testid="mfl-self-investment" className="text-lg font-medium tabular-nums">
        {s.sharePercent == null ? t("learn.selfInvestment.noIncome", { total: s.total.formatted }) : t("learn.selfInvestment.line", { total: s.total.formatted, percent: s.sharePercent })}
      </p>
      <p className="mt-1 text-sm text-ink-muted">{t("mfl.invest.hint")}</p>
    </div>
  );
}

/** Bir soat qiymati (ish valyutasida): oxirgi to'liq oylar taklifi (AUTO) yoki qo'lda daromad va ish vaqti. */
function HourCard({ spaceId, data }: { spaceId: string; data: MfLearningOverviewDto }) {
  const { t } = useTranslation();
  const hv = data.hourValue;
  const suggest = useQuery({ queryKey: keys.mfHourSuggest(spaceId), queryFn: () => call(commands.mfHourSuggest(spaceId)) });
  const [f, setF] = useState(() => ({
    income: hv?.incomeSource === "MANUAL" ? hv.income.plain : "",
    hours: String(Math.floor((hv?.minutesPerDay ?? 600) / 60)),
    minutes: String((hv?.minutesPerDay ?? 600) % 60),
    days: String(hv?.days ?? 22),
  }));
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.mfHourSave(spaceId, {
          income: f.income.trim() === "" ? null : f.income,
          minutesPerDay: toMinutes(f.hours, f.minutes),
          days: parseCount(f.days, 2),
        }),
      ),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  const s = suggest.data;
  return (
    <section aria-labelledby="mfl-hour" data-testid="mfl-hour" className="card flex flex-col gap-3">
      <h2 id="mfl-hour" className="text-xl font-semibold">
        {t("mfl.hour.title")}
      </h2>
      {hv ? <HourView hv={hv} /> : <p className="text-ink-muted">{t("mfl.hour.none")}</p>}
      <div className="flex flex-col gap-1 text-sm">
        <p className="font-medium">{t("mfl.hour.months")}</p>
        {s && s.months.length === 0 && <p className="text-ink-muted">{t("mfl.hour.noMonths")}</p>}
        {s && s.months.length > 0 && (
          <ul data-testid="mfl-months" className="tabular-nums">
            {s.months.map((m) => (
              <li key={m.periodStart}>
                {t("mfl.hour.monthLine", {
                  period: t("kk.period", { from: showDate(m.periodStart), to: showDate(m.periodEnd) }),
                  total: m.total.formatted,
                })}
              </li>
            ))}
          </ul>
        )}
      </div>
      <form className="grid max-w-2xl gap-3 sm:grid-cols-3" onSubmit={submit}>
        <label className="sm:col-span-3">
          <span className="label">{t("mfl.hour.incomeField", { currency: data.workCurrency })}</span>
          <AmountInput value={f.income} onChange={(e) => setF({ ...f, income: e.target.value })} />
        </label>
        {s?.average && <p className="text-sm text-ink-muted sm:col-span-3">{t("learn.hour.suggest", { count: s.months.length, average: s.average.formatted })}</p>}
        <label>
          <span className="label">{t("learn.hour.hours")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })} required />
        </label>
        <label>
          <span className="label">{t("learn.hour.minutes")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.minutes} onChange={(e) => setF({ ...f, minutes: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("learn.hour.days")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.days} onChange={(e) => setF({ ...f, days: e.target.value })} required />
        </label>
        <div className="sm:col-span-3">
          <ErrorText error={save.error} />
        </div>
        <div className="sm:col-span-3">
          <button className="btn-primary" disabled={save.isPending}>
            {t("learn.hour.save")}
          </button>
        </div>
      </form>
    </section>
  );
}

function HourView({ hv }: { hv: MfHourDto }) {
  const { t } = useTranslation();
  const source = hv.incomeSource === "AUTO" ? t("mfl.hour.source.AUTO", { count: hv.months }) : t("learn.hour.source.MANUAL");
  const h = hv.home;
  const r = h.rate;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.value")}</p>
          <p data-testid="mfl-hour-value" className="kpi text-accent">
            {hv.hourValue.formatted}
          </p>
        </div>
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.double")}</p>
          <p data-testid="mfl-hour-double" className="text-2xl font-semibold tabular-nums">
            {hv.doubleTarget.formatted}
          </p>
        </div>
      </div>
      <div data-testid="mfl-hour-home" data-status={h.rateStatus} className="rounded-md border border-line p-3 text-sm">
        <p className="text-ink-muted">{t("mfl.hour.home")}</p>
        {h.hourValue && h.doubleTarget && h.rateStatus !== "SAME_CURRENCY" && (
          <p className="font-medium tabular-nums">{t("mfl.hour.homeValue", { value: h.hourValue.formatted, double: h.doubleTarget.formatted })}</p>
        )}
        {r && !r.identity && <p className="text-xs text-ink-muted">{t("mf.rateLine", { from: r.fromCurrency, rate: r.rate, to: r.toCurrency, date: showDate(r.rateOn) })}</p>}
        {h.rateStatus !== "FRESH" && <p className={h.rateStatus === "STALE" ? "text-warn" : "text-ink-muted"}>{t(`mfl.hour.rate.${h.rateStatus}`)}</p>}
      </div>
      <p className="text-sm">{t("mfl.hour.income", { amount: hv.income.formatted, source })}</p>
      <p className="text-sm text-ink-muted">
        {t("learn.hour.monthly", { time: showMinutes(t, hv.monthlyMinutes) })} · {t("learn.hour.computedOn", { date: showDate(hv.computedOn) })}
      </p>
      {hv.overCeiling && (
        <p role="note" data-testid="mfl-hour-ceiling" className="rounded-md border border-accent/40 bg-sidebar p-3 text-sm">
          <span className="font-semibold text-accent-text">{t("mentor.name")}: </span>
          {t("learn.hour.ceiling")}
        </p>
      )}
    </div>
  );
}

/** Reja kartasi: maqsad, holat, byudjet (ish valyutasida), boshlang'ich nuqta va natijani o'lchash. */
function PlanCard({ spaceId, plan: p }: { spaceId: string; plan: MfLearningPlanDto }) {
  const { t } = useTranslation();
  const openCourseCheck = useUi((s) => s.openCourseCheck);
  const [result, setResult] = useState<MfLearningResultDto | null>(null);
  const status = useMutation({ mutationFn: (to: string) => call(commands.mfLearningPlanSetStatus(spaceId, p.id, to)) });
  const measure = useMutation({ mutationFn: () => call(commands.mfLearningPlanResult(spaceId, p.id)), onSuccess: setResult });
  const open = p.status === "ACTIVE" || p.status === "PAUSED";
  return (
    <section aria-label={t("mfl.plan.label", { skill: p.skill })} data-testid={`mfl-plan-${p.id}`} className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-lg font-semibold">{p.skill}</h3>
        <span data-testid="mfl-plan-goal" className="rounded-full border border-line px-2 py-0.5 text-xs text-ink-muted">
          {t(`mfl.goalShort.${p.goal}`)}
        </span>
        <span data-testid="mfl-plan-status" className={`rounded-full border px-2 py-0.5 text-xs ${STATUS_TONE[p.status] ?? "border-line text-ink-muted"}`}>
          {t(`learn.status.${p.status}`)}
        </span>
      </div>
      <p className="text-sm">{t(`mfl.goal.${p.goal}`)}</p>
      {p.purpose && <p>{p.purpose}</p>}
      <p className="text-sm text-ink-muted">
        {p.paths.map((x) => t(`learn.path.${x}`)).join(", ")} · {t("learn.plan.dates", { start: showDate(p.startOn), review: showDate(p.reviewOn) })}
      </p>
      <ul className="grid gap-1 text-sm sm:grid-cols-2">
        <li>{t("learn.plan.weeklyTarget", { time: showMinutes(t, p.weeklyMinutes) })}</li>
        {p.budget && <li className="tabular-nums">{t("mfl.plan.budgetLine", { budget: p.budget.formatted })}</li>}
        <li className="tabular-nums">{p.baselineHourValue ? t("learn.plan.baseline", { value: p.baselineHourValue.formatted }) : t("learn.plan.noBaseline")}</li>
        {p.resultHourValue && <li className="tabular-nums">{t("learn.plan.lastResult", { value: p.resultHourValue.formatted })}</li>}
        {p.ventureIdeaTitle && <li data-testid="mfl-plan-idea">{t("mfl.plan.ideaLine", { title: p.ventureIdeaTitle })}</li>}
      </ul>
      {p.reviewDue && (
        <p role="note" className="text-sm text-accent-text">
          {t("learn.plan.reviewDue")}
        </p>
      )}
      {p.courseCheckSuggested && open && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="text-ink-muted">{t("learn.plan.courseHint")}</span>
          <button className="btn-ghost text-sm" onClick={openCourseCheck}>
            {t("learn.plan.checkCourse")}
          </button>
        </div>
      )}
      <ErrorText error={status.error ?? measure.error} />
      {result && <ResultView r={result} />}
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost text-sm" disabled={measure.isPending} onClick={() => measure.mutate()}>
          {t("learn.result.measure")}
        </button>
        {(NEXT[p.status] ?? []).map((to) => (
          <button key={to} className="btn-ghost text-sm" disabled={status.isPending} onClick={() => status.mutate(to)}>
            {t(`learn.action.${to}`)}
          </button>
        ))}
      </div>
    </section>
  );
}

/** Yangi reja: maqsad (chet elda / uyda), uyda — ixtiyoriy «Hunardan ishga» g'oyasi. Chegarani yadro tekshiradi. */
function MfPlanDialog({ spaceId, data, onClose }: { spaceId: string; data: MfLearningOverviewDto; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [f, setF] = useState({ goal: "ABROAD", skill: "", purpose: "", paths: [] as string[], budget: "", hours: "", minutes: "", startOn: "", reviewOn: "", ideaId: data.startupIdeaId ?? "" });
  const home = f.goal === "HOME";
  const create = useMutation({
    mutationFn: () =>
      call(
        commands.mfLearningPlanCreate(spaceId, {
          goal: f.goal,
          skill: f.skill,
          purpose: f.purpose.trim() === "" ? null : f.purpose,
          paths: f.paths,
          budget: f.budget.trim() === "" ? null : f.budget,
          weeklyMinutes: toMinutes(f.hours, f.minutes),
          startOn: f.startOn || null,
          reviewOn: f.reviewOn || null,
          ventureIdeaId: home && f.ideaId ? f.ideaId : null,
        }),
      ),
    onSuccess: onClose,
  });
  const togglePath = (p: string) => setF({ ...f, paths: f.paths.includes(p) ? f.paths.filter((x) => x !== p) : [...f.paths, p] });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("learn.plan.dialog")} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <form className="card flex max-h-full w-full max-w-xl flex-col gap-4 overflow-y-auto" onSubmit={submit}>
        <h2 className="text-xl font-semibold">{t("learn.plan.dialog")}</h2>
        <fieldset className="flex flex-col gap-2">
          <legend className="label">{t("mfl.plan.goal")}</legend>
          {GOALS.map((g) => (
            <label key={g} className="flex items-start gap-2">
              <input type="radio" name="mfl-goal" className="mt-1" checked={f.goal === g} onChange={() => setF({ ...f, goal: g })} />
              <span>
                {t(`mfl.goal.${g}`)}
                <span className="block text-xs text-ink-muted">{t(`mfl.goalHint.${g}`)}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <label>
          <span className="label">{t("learn.plan.skill")}</span>
          <input autoFocus className="field" placeholder={t("mfl.plan.skillPlaceholder")} value={f.skill} onChange={(e) => setF({ ...f, skill: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("learn.plan.purpose")}</span>
          <input className="field" value={f.purpose} onChange={(e) => setF({ ...f, purpose: e.target.value })} />
        </label>
        {home && data.ideas.length > 0 && (
          <label>
            <span className="label">{t("mfl.plan.idea")}</span>
            <select className="field" value={f.ideaId} onChange={(e) => setF({ ...f, ideaId: e.target.value })}>
              <option value="">{t("mfl.plan.noIdea")}</option>
              {data.ideas.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title}
                </option>
              ))}
            </select>
          </label>
        )}
        <fieldset className="flex flex-col gap-2">
          <legend className="label">{t("learn.plan.paths")}</legend>
          <div className="flex flex-wrap gap-4">
            {PATHS.map((p) => (
              <label key={p} className="flex items-center gap-2">
                <input type="checkbox" checked={f.paths.includes(p)} onChange={() => togglePath(p)} />
                {t(`learn.path.${p}`)}
              </label>
            ))}
          </div>
          {f.paths.includes("COURSE") && <p className="text-sm text-ink-muted">{t("learn.plan.courseHint")}</p>}
        </fieldset>
        <label>
          <span className="label">{t("mfl.plan.budget", { currency: data.workCurrency })}</span>
          <AmountInput value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label>
            <span className="label">{t("learn.plan.weeklyHours")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("learn.plan.weeklyMinutes")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={f.minutes} onChange={(e) => setF({ ...f, minutes: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("learn.plan.start")}</span>
            <input type="date" className="field" value={f.startOn} onChange={(e) => setF({ ...f, startOn: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("learn.plan.review")}</span>
            <input type="date" className="field" value={f.reviewOn} onChange={(e) => setF({ ...f, reviewOn: e.target.value })} />
          </label>
        </div>
        <p className="text-sm text-ink-muted">{t("mfl.plans.hint")}</p>
        <ErrorText error={create.error} />
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={create.isPending}>
            {t("learn.plan.create")}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </div>
  );
}

/** «Ilm zakoti»: shu oy hamyurtlarga ish, til yoki hujjat bo'yicha yordam va boshqa o'rgatishlar. */
function TeachingCard({ data, onAdd }: { data: MfLearningOverviewDto; onAdd: () => void }) {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="mfl-teach" className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="mfl-teach" className="text-xl font-semibold">
          {t("learn.teach.title")}
        </h2>
        <button className="btn-ghost" onClick={onAdd}>
          {t("learn.teach.add")}
        </button>
      </div>
      <p className="text-sm text-ink-muted">{t("mfl.teach.hint")}</p>
      <p data-testid="mfl-teach-count" className="font-medium">
        {t("learn.teach.count", { count: data.teachingCount })}
      </p>
      {data.teaching.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("learn.teach.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.teaching.map((r) => (
            <li key={r.id} className="flex flex-wrap gap-x-3 py-2 text-sm">
              <span className="tabular-nums text-ink-muted">{showDate(r.occurredOn)}</span>
              <span className="rounded-full border border-line px-2 text-xs text-ink-muted">{t(`mfl.area.${r.area}`)}</span>
              <span className="font-medium">{r.topic}</span>
              {r.learner && <span>{t("learn.teach.to", { learner: r.learner })}</span>}
              {r.minutes != null && <span className="text-ink-muted">{showMinutes(t, r.minutes)}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function MfTeachingDialog({ spaceId, onClose }: { spaceId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [f, setF] = useState({ area: "WORK", learner: "", topic: "", minutes: "", occurredOn: "" });
  const add = useMutation({
    mutationFn: () =>
      call(
        commands.mfTeachingAdd(spaceId, {
          occurredOn: f.occurredOn || null,
          area: f.area,
          learner: f.learner.trim() === "" ? null : f.learner,
          topic: f.topic,
          minutes: f.minutes.trim() === "" ? null : parseCount(f.minutes, 4),
        }),
      ),
    onSuccess: onClose,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("learn.teach.dialog")} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <form className="card flex max-h-full w-full max-w-xl flex-col gap-4 overflow-y-auto" onSubmit={submit}>
        <h2 className="text-xl font-semibold">{t("learn.teach.dialog")}</h2>
        <p className="text-sm text-ink-muted">{t("mfl.teach.hint")}</p>
        <fieldset>
          <legend className="label">{t("mfl.teach.area")}</legend>
          <div className="flex flex-wrap gap-2">
            {AREAS.map((a) => (
              <button key={a} type="button" aria-pressed={f.area === a} className={f.area === a ? "btn-primary text-sm" : "btn-ghost text-sm"} onClick={() => setF({ ...f, area: a })}>
                {t(`mfl.area.${a}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <label>
          <span className="label">{t("learn.teach.topic")}</span>
          <input autoFocus className="field" value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("mfl.teach.learner")}</span>
          <input className="field" value={f.learner} onChange={(e) => setF({ ...f, learner: e.target.value })} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label>
            <span className="label">{t("learn.teach.minutes")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={f.minutes} onChange={(e) => setF({ ...f, minutes: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("learn.teach.date")}</span>
            <input type="date" className="field" value={f.occurredOn} onChange={(e) => setF({ ...f, occurredOn: e.target.value })} />
          </label>
        </div>
        <ErrorText error={add.error} />
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={add.isPending}>
            {t("common.save")}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </div>
  );
}
