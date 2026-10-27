import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type HourValueDto, type LearningMemberDto, type LearningOverviewDto, type LearningPlanDto, type LearningResultDto, type MoneyDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";
import { PlanDialog, TeachingDialog } from "./LearningDialogs";
import { NEXT, STATUS_TONE } from "./planStatus";
import { parseCount, showMinutes, toMinutes } from "./time";


/**
 * «O'zimga sarmoya» (8-tamoyil, uy/SPEC 2G): «Bir soatim qancha?», bilim rejalari, «Ilm zakoti» va
 * oylik «O'zimga sarmoya» qatori. Barcha summa va foizlar yadrodan; UI faqat ko'rsatadi.
 */
export function LearningScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const o = useQuery({ queryKey: keys.learning(spaceId), queryFn: () => call(commands.learningOverview(spaceId, null)) });
  const [dialog, setDialog] = useState<"plan" | "teach" | null>(null);
  const data = o.data;
  const names = new Map((data?.members ?? []).map((m) => [m.memberId, m.displayName]));
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("learn.title")}</h1>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p>{t("learn.intro")}</p>
        <p className="text-sm text-ink-muted">{t("learn.example")}</p>
      </aside>
      <section aria-labelledby="learn-tasks" className="card flex flex-col gap-2">
        <h2 id="learn-tasks" className="text-lg font-semibold">
          {t("learn.tasks.title")}
        </h2>
        <ol className="list-decimal space-y-1 pl-5">
          {[1, 2, 3].map((n) => (
            <li key={n}>{t(`learn.tasks.${n}`)}</li>
          ))}
        </ol>
      </section>
      <ErrorText error={o.error} />
      {data && <SelfInvestmentCard data={data} />}

      <h2 className="text-xl font-semibold">{t("learn.hour.title")}</h2>
      {(data?.members ?? []).map((m) => (
        <HourCard key={m.memberId} spaceId={spaceId} member={m} />
      ))}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">{t("learn.plans.title")}</h2>
        <button className="btn-primary" disabled={!data} onClick={() => setDialog("plan")}>
          {t("learn.plans.new")}
        </button>
      </div>
      <p className="text-sm text-ink-muted">{t("learn.plan.money")}</p>
      {data && data.plans.length === 0 && <p className="text-ink-muted">{t("learn.plans.empty")}</p>}
      {(data?.plans ?? []).map((p) => (
        <PlanCard key={p.id} spaceId={spaceId} plan={p} memberName={names.get(p.memberId) ?? ""} />
      ))}

      {data && <TeachingCard data={data} names={names} onAdd={() => setDialog("teach")} />}

      {dialog === "plan" && data && <PlanDialog spaceId={spaceId} members={data.members} onClose={() => setDialog(null)} />}
      {dialog === "teach" && data && <TeachingDialog spaceId={spaceId} members={data.members} onClose={() => setDialog(null)} />}
    </section>
  );
}

function SelfInvestmentCard({ data }: { data: LearningOverviewDto }) {
  const { t } = useTranslation();
  const s = data.selfInvestment;
  return (
    <div className="card">
      <p className="text-sm text-ink-muted">{t("learn.selfInvestment.title")}</p>
      <p data-testid="learn-self-investment" className="text-lg font-medium tabular-nums">
        {s.sharePercent == null ? t("learn.selfInvestment.noIncome", { total: s.total.formatted }) : t("learn.selfInvestment.line", { total: s.total.formatted, percent: s.sharePercent })}
      </p>
      <p className="mt-1 text-sm text-ink-muted">{t("learn.selfInvestment.hint")}</p>
    </div>
  );
}

/** «Bir soatim qancha?» (2G.1): oxirgi hisob, taklif (AUTO) yoki qo'lda daromad, ish vaqti. */
function HourCard({ spaceId, member }: { spaceId: string; member: LearningMemberDto }) {
  const { t } = useTranslation();
  const hv = member.hourValue;
  const suggest = useQuery({ queryKey: keys.hourSuggest(spaceId, member.memberId), queryFn: () => call(commands.hourValueSuggest(spaceId, member.memberId)) });
  const [f, setF] = useState(() => ({
    income: hv?.incomeSource === "MANUAL" ? hv.income.plain : "",
    hours: String(Math.floor((hv?.minutesPerDay ?? 480) / 60)),
    minutes: String((hv?.minutesPerDay ?? 480) % 60),
    days: String(hv?.days ?? 22),
  }));
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.hourValueSave(spaceId, {
          memberId: member.memberId,
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
  const avg = suggest.data?.average;
  const label = t("learn.hour.cardLabel", { name: member.displayName });
  return (
    <section aria-label={label} data-testid={`hour-${member.memberId}`} className="card flex flex-col gap-3">
      <h3 className="font-semibold">{member.displayName}</h3>
      {hv ? <HourValueView hv={hv} /> : <p className="text-ink-muted">{t("learn.hour.none")}</p>}
      <form className="grid max-w-2xl gap-3 sm:grid-cols-3" onSubmit={submit}>
        <label className="sm:col-span-3">
          <span className="label">{t("learn.hour.incomeField")}</span>
          <AmountInput value={f.income} onChange={(e) => setF({ ...f, income: e.target.value })} />
        </label>
        <p className="text-sm text-ink-muted sm:col-span-3">{avg ? t("learn.hour.suggest", { count: suggest.data?.months.length ?? 0, average: avg.formatted }) : t("learn.hour.noSuggest")}</p>
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

function HourValueView({ hv }: { hv: HourValueDto }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.value")}</p>
          <p data-testid="hour-value" className="kpi text-accent">
            {hv.hourValue.formatted}
          </p>
        </div>
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.double")}</p>
          <p data-testid="hour-double" className="text-2xl font-semibold tabular-nums">
            {hv.doubleTarget.formatted}
          </p>
        </div>
      </div>
      <p className="text-sm">{t("learn.hour.income", { amount: hv.income.formatted, source: t(`learn.hour.source.${hv.incomeSource}`) })}</p>
      <p className="text-sm text-ink-muted">
        {t("learn.hour.monthly", { time: showMinutes(t, hv.monthlyMinutes) })} · {t("learn.hour.computedOn", { date: showDate(hv.computedOn) })}
      </p>
      {hv.overCeiling && (
        <p role="note" data-testid="hour-ceiling" className="rounded-md border border-accent/40 bg-sidebar p-3 text-sm">
          <span className="font-semibold text-accent-text">{t("mentor.name")}: </span>
          {t("learn.hour.ceiling")}
        </p>
      )}
    </div>
  );
}

/** Bilim rejasi kartasi (2G.2, 2G.5): holat, o'qish vaqti, byudjet va sarflangani, natijani o'lchash. */
function PlanCard({ spaceId, plan: p, memberName }: { spaceId: string; plan: LearningPlanDto; memberName: string }) {
  const { t } = useTranslation();
  const openCourseCheck = useUi((s) => s.openCourseCheck);
  const [study, setStudy] = useState({ hours: "", minutes: "" });
  const [result, setResult] = useState<LearningResultDto | null>(null);
  const status = useMutation({ mutationFn: (to: string) => call(commands.learningPlanSetStatus(spaceId, p.id, to)) });
  const log = useMutation({
    mutationFn: () => call(commands.studyLogAdd(spaceId, p.id, { occurredOn: null, minutes: toMinutes(study.hours, study.minutes), note: null })),
    onSuccess: () => setStudy({ hours: "", minutes: "" }),
  });
  const measure = useMutation({ mutationFn: () => call(commands.learningPlanResult(spaceId, p.id)), onSuccess: setResult });
  const open = p.status === "ACTIVE" || p.status === "PAUSED";
  const submitStudy = (e: FormEvent) => {
    e.preventDefault();
    log.mutate();
  };
  return (
    <section aria-label={t("learn.plan.cardLabel", { skill: p.skill })} data-testid={`plan-${p.id}`} className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-lg font-semibold">{p.skill}</h3>
        <span className="text-sm text-ink-muted">{memberName}</span>
        <span data-testid="plan-status" className={`rounded-full border px-2 py-0.5 text-xs ${STATUS_TONE[p.status] ?? "border-line text-ink-muted"}`}>
          {t(`learn.status.${p.status}`)}
        </span>
      </div>
      {p.purpose && <p>{p.purpose}</p>}
      <p className="text-sm text-ink-muted">
        {p.paths.map((x) => t(`learn.path.${x}`)).join(", ")} · {t("learn.plan.dates", { start: showDate(p.startOn), review: showDate(p.reviewOn) })}
      </p>
      <ul className="grid gap-1 text-sm sm:grid-cols-2">
        <li>{t("learn.plan.weeklyTarget", { time: showMinutes(t, p.weeklyMinutes) })}</li>
        <li data-testid="plan-studied">{t("learn.plan.studied", { time: showMinutes(t, p.studyMinutes) })}</li>
        <li data-testid="plan-spent" className="tabular-nums">
          {p.budget ? t("learn.plan.budgetLine", { budget: p.budget.formatted, spent: p.spent.formatted }) : t("learn.plan.spentLine", { spent: p.spent.formatted })}
        </li>
        <li className="tabular-nums">{p.baselineHourValue ? t("learn.plan.baseline", { value: p.baselineHourValue.formatted }) : t("learn.plan.noBaseline")}</li>
        {p.resultHourValue && <li className="tabular-nums">{t("learn.plan.lastResult", { value: p.resultHourValue.formatted })}</li>}
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
      {open && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={submitStudy}>
          <p className="w-full text-sm font-medium">{t("learn.study.title")}</p>
          <label className="w-28">
            <span className="label">{t("learn.study.hours")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={study.hours} onChange={(e) => setStudy({ ...study, hours: e.target.value })} />
          </label>
          <label className="w-28">
            <span className="label">{t("learn.study.minutes")}</span>
            <input className="field tabular-nums" inputMode="numeric" value={study.minutes} onChange={(e) => setStudy({ ...study, minutes: e.target.value })} />
          </label>
          <button className="btn-ghost" disabled={log.isPending}>
            {t("learn.study.add")}
          </button>
        </form>
      )}
      <ErrorText error={log.error ?? status.error ?? measure.error} />
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

/** Natija ko'rinishi uchun yetarli maydonlar (Uy va Musofir natijasi — bir xil shakl). */
type ResultLike = Pick<LearningResultDto, "diff" | "changeBp" | "changePercent"> & {
  baseline: { hourValue: MoneyDto } | null;
  current: { hourValue: MoneyDto };
};

/** Natija (2G.5): pasaysa yoki o'zgarmasa ham uyaltirilmaydi — davom ettirish, o'zgartirish yoki yopish. */
export function ResultView({ r }: { r: ResultLike }) {
  const { t } = useTranslation();
  // Boshlang'ich nuqta yo'q — solishtirib bo'lmaydi: faqat hozirgi qiymat va betaraf izoh.
  if (!r.baseline) {
    return (
      <div role="status" data-testid="plan-result" className="rounded-md border border-line p-3 text-sm">
        <p className="font-medium tabular-nums">{t("learn.result.currentOnly", { current: r.current.hourValue.formatted })}</p>
        <p className="text-ink-muted">{t("learn.result.noBaseline")}</p>
      </div>
    );
  }
  // Belgi yadro bergan bazis punktdan (yo'q bo'lsa — farq matnidan); UI hech narsa hisoblamaydi.
  const up = r.changeBp != null ? r.changeBp > 0 : r.diff != null && r.diff.minor !== "0" && !r.diff.minor.startsWith("-");
  return (
    <div role="status" data-testid="plan-result" className="rounded-md border border-line p-3 text-sm">
      <p className="font-medium tabular-nums">{t("learn.result.line", { baseline: r.baseline.hourValue.formatted, current: r.current.hourValue.formatted })}</p>
      {r.diff && <p className="tabular-nums">{r.changePercent != null ? t("learn.result.diff", { diff: r.diff.formatted, percent: r.changePercent }) : t("learn.result.diffOnly", { diff: r.diff.formatted })}</p>}
      <p className="text-ink-muted">{t(up ? "learn.result.up" : "learn.result.flat")}</p>
    </div>
  );
}

/** «Ilm zakoti» (2G.6): shu oydagi o'rgatish yozuvlari va ularning soni. Pul hisobi yo'q. */
function TeachingCard({ data, names, onAdd }: { data: LearningOverviewDto; names: Map<string, string>; onAdd: () => void }) {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="learn-teach" className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="learn-teach" className="text-xl font-semibold">
          {t("learn.teach.title")}
        </h2>
        <button className="btn-ghost" onClick={onAdd}>
          {t("learn.teach.add")}
        </button>
      </div>
      <p className="text-sm text-ink-muted">{t("learn.teach.hint")}</p>
      <p data-testid="teach-count" className="font-medium">
        {t("learn.teach.count", { count: data.teachingCount })}
      </p>
      {data.teaching.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("learn.teach.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.teaching.map((r) => (
            <li key={r.id} className="flex flex-wrap gap-x-3 py-2 text-sm">
              <span className="tabular-nums text-ink-muted">{showDate(r.occurredOn)}</span>
              <span className="font-medium">{r.topic}</span>
              <span className="text-ink-muted">{names.get(r.memberId) ?? ""}</span>
              {r.learner && <span>{t("learn.teach.to", { learner: r.learner })}</span>}
              {r.minutes != null && <span className="text-ink-muted">{showMinutes(t, r.minutes)}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
