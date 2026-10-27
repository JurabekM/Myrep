import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkDelegateInput, type KkDelegateResultDto, type KkDelegationDto, type KkLearningOverviewDto, type KkOwnerHourDto, type KkStaffOptionDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";
import { useUi } from "../../state/ui";
import { parseCount, showMinutes, toMinutes } from "../learning/time";

/**
 * Kasb-kor «O'zimga sarmoya» (8-tamoyil, kasbkor/SPEC 8A): egasining bir soati (yopilgan oylardan),
 * «O'zim qilaymi yoki o'rgatib topshiraymi?», «Ilm zakoti» (xodimga o'rgatish), kurs tekshiruvi va
 * «Sarmoya (o'qish)» qatori. Egasi bo'limi — sotuvchi qurilmasida ko'rinmaydi (soat qiymati foydadan).
 * Barcha summa yadrodan; UI faqat ko'rsatadi.
 */
export function KkLearningScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const openCourseCheck = useUi((s) => s.openCourseCheck);
  const o = useQuery({
    queryKey: keys.kkLearning(spaceId),
    queryFn: () => call(commands.kkLearningOverview(spaceId, null)),
  });
  const [teach, setTeach] = useState(false);
  const data = o.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kkl.title")}</h1>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p>{t("kkl.intro")}</p>
        <p className="text-sm text-ink-muted">{t("kkl.example")}</p>
      </aside>
      <section aria-labelledby="kkl-tasks" className="card flex flex-col gap-2">
        <h2 id="kkl-tasks" className="text-lg font-semibold">
          {t("learn.tasks.title")}
        </h2>
        <ol className="list-decimal space-y-1 pl-5">
          {[1, 2, 3].map((n) => (
            <li key={n}>{t(`kkl.tasks.${n}`)}</li>
          ))}
        </ol>
      </section>
      <ErrorText error={o.error} />
      {data && (
        <div className="card">
          <p className="text-sm text-ink-muted">{t("kkl.invest.title")}</p>
          <p data-testid="kkl-self-investment" className="text-lg font-medium tabular-nums">
            {data.selfInvestment.formatted}
          </p>
          <p className="mt-1 text-sm text-ink-muted">{t("kkl.invest.hint")}</p>
        </div>
      )}
      {data && <OwnerHourCard key={data.hourValue?.id ?? "none"} spaceId={spaceId} hv={data.hourValue} />}
      {data && <DelegateCard spaceId={spaceId} data={data} />}
      {data && <TeachingCard data={data} onAdd={() => setTeach(true)} />}
      <section aria-labelledby="kkl-course" className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="kkl-course" className="text-lg font-semibold">
            {t("kkl.course.title")}
          </h2>
          <p className="text-sm text-ink-muted">{t("kkl.course.hint")}</p>
        </div>
        <button className="btn-ghost" onClick={openCourseCheck}>
          {t("learn.plan.checkCourse")}
        </button>
      </section>
      {teach && data && <KkTeachingDialog spaceId={spaceId} staff={data.staff} onClose={() => setTeach(false)} />}
    </section>
  );
}

/** Egasining bir soati (8A.1): yopilgan oylar taklifi (AUTO) yoki qo'lda topgani va ish vaqti. */
function OwnerHourCard({ spaceId, hv }: { spaceId: string; hv: KkOwnerHourDto | null }) {
  const { t } = useTranslation();
  const suggest = useQuery({
    queryKey: keys.kkOwnerSuggest(spaceId),
    queryFn: () => call(commands.kkOwnerHourSuggest(spaceId)),
  });
  const [f, setF] = useState(() => ({
    income: hv?.incomeSource === "MANUAL" ? hv.income.plain : "",
    hours: String(Math.floor((hv?.minutesPerDay ?? 600) / 60)),
    minutes: String((hv?.minutesPerDay ?? 600) % 60),
    days: String(hv?.days ?? 26),
  }));
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkOwnerHourSave(spaceId, {
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
    <section aria-labelledby="kkl-hour" data-testid="kkl-hour" className="card flex flex-col gap-3">
      <h2 id="kkl-hour" className="text-xl font-semibold">
        {t("kkl.hour.title")}
      </h2>
      {hv ? <OwnerHourView hv={hv} /> : <p className="text-ink-muted">{t("kkl.hour.none")}</p>}
      <div className="flex flex-col gap-1 text-sm">
        <p className="font-medium">{t("kkl.hour.months")}</p>
        {s && s.months.length === 0 && <p className="text-ink-muted">{t("kkl.hour.noMonths")}</p>}
        {s && s.months.length > 0 && (
          <ul data-testid="kkl-months" className="tabular-nums">
            {s.months.map((m) => (
              <li key={m.periodStart}>
                {t("kkl.hour.monthLine", {
                  period: t("kk.period", {
                    from: showDate(m.periodStart),
                    to: showDate(m.periodEnd),
                  }),
                  labor: m.ownerLabor.formatted,
                  profit: m.trueProfit.formatted,
                  earned: m.earnings.formatted,
                })}
              </li>
            ))}
          </ul>
        )}
        <p className="text-ink-muted">{t("kkl.hour.salaryNote")}</p>
      </div>
      <form className="grid max-w-2xl gap-3 sm:grid-cols-3" onSubmit={submit}>
        <label className="sm:col-span-3">
          <span className="label">{t("kkl.hour.incomeField")}</span>
          <AmountInput value={f.income} onChange={(e) => setF({ ...f, income: e.target.value })} />
        </label>
        {s?.average && (
          <p className="text-sm text-ink-muted sm:col-span-3">
            {t("kkl.hour.suggest", {
              count: s.months.length,
              average: s.average.formatted,
            })}
          </p>
        )}
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

function OwnerHourView({ hv }: { hv: KkOwnerHourDto }) {
  const { t } = useTranslation();
  const source = hv.incomeSource === "AUTO" ? t("kkl.hour.source.AUTO", { count: hv.months }) : t("kkl.hour.source.MANUAL");
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.value")}</p>
          <p data-testid="kkl-hour-value" className="kpi text-accent">
            {hv.hourValue.formatted}
          </p>
        </div>
        <div>
          <p className="text-sm text-ink-muted">{t("learn.hour.double")}</p>
          <p data-testid="kkl-hour-double" className="text-2xl font-semibold tabular-nums">
            {hv.doubleTarget.formatted}
          </p>
        </div>
      </div>
      <p className="text-sm">{t("kkl.hour.income", { amount: hv.income.formatted, source })}</p>
      <p className="text-sm text-ink-muted">
        {t("learn.hour.monthly", { time: showMinutes(t, hv.monthlyMinutes) })} · {t("learn.hour.computedOn", { date: showDate(hv.computedOn) })}
      </p>
      {hv.overCeiling && (
        <p role="note" data-testid="kkl-hour-ceiling" className="rounded-md border border-accent/40 bg-sidebar p-3 text-sm">
          <span className="font-semibold text-accent-text">{t("mentor.name")}: </span>
          {t("learn.hour.ceiling")}
        </p>
      )}
    </div>
  );
}

const EMPTY = {
  task: "",
  agreementId: "",
  owner: "",
  taskHours: "",
  taskMinutes: "",
  helper: "",
  trainingMoney: "",
  trainingHours: "",
  trainingMinutes: "",
};

/** «O'zim qilaymi yoki o'rgatib topshiraymi?» (8A.2): hisob yadroda, qaror xodim kartochkasiga bog'lanishi mumkin. */
function DelegateCard({ spaceId, data }: { spaceId: string; data: KkLearningOverviewDto }) {
  const { t } = useTranslation();
  const [f, setF] = useState(EMPTY);
  const [result, setResult] = useState<KkDelegateResultDto | null>(null);
  const input = (): KkDelegateInput => ({
    task: f.task,
    agreementId: f.agreementId || null,
    ownerHourValue: f.owner.trim() === "" ? null : f.owner,
    taskMinutes: toMinutes(f.taskHours, f.taskMinutes),
    helperHourCost: f.helper,
    trainingMoney: f.trainingMoney.trim() === "" ? null : f.trainingMoney,
    trainingMinutes: toMinutes(f.trainingHours, f.trainingMinutes),
  });
  const calc = useMutation({
    mutationFn: () => call(commands.kkDelegateCalc(spaceId, input())),
    onSuccess: setResult,
  });
  const save = useMutation({
    mutationFn: () => call(commands.kkDelegationSave(spaceId, input())),
    onSuccess: (d) => {
      setResult(d.result);
      setF(EMPTY);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    calc.mutate();
  };
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <section aria-labelledby="kkl-delegate" className="card flex flex-col gap-3">
      <h2 id="kkl-delegate" className="text-xl font-semibold">
        {t("kkl.del.title")}
      </h2>
      <p className="text-sm text-ink-muted">{t("kkl.del.hint")}</p>
      <form className="grid max-w-3xl gap-3 sm:grid-cols-4" onSubmit={submit} aria-label={t("kkl.del.title")}>
        <label className="sm:col-span-2">
          <span className="label">{t("kkl.del.task")}</span>
          <input className="field" placeholder={t("kkl.del.taskPlaceholder")} value={f.task} onChange={set("task")} />
        </label>
        <label className="sm:col-span-2">
          <span className="label">{t("kkl.del.staff")}</span>
          <select className="field" value={f.agreementId} onChange={set("agreementId")}>
            <option value="">{t("kkl.del.noStaff")}</option>
            {data.staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="sm:col-span-2">
          <span className="label">{t("kkl.del.owner")}</span>
          <AmountInput value={f.owner} placeholder={data.hourValue?.hourValue.plain ?? ""} onChange={set("owner")} />
        </label>
        <label className="sm:col-span-2">
          <span className="label">{t("kkl.del.helper")}</span>
          <AmountInput value={f.helper} onChange={set("helper")} />
        </label>
        <label>
          <span className="label">{t("kkl.del.taskHours")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.taskHours} onChange={set("taskHours")} />
        </label>
        <label>
          <span className="label">{t("kkl.del.minutes")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.taskMinutes} onChange={set("taskMinutes")} />
        </label>
        <label>
          <span className="label">{t("kkl.del.trainingHours")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.trainingHours} onChange={set("trainingHours")} />
        </label>
        <label>
          <span className="label">{t("kkl.del.minutes")}</span>
          <input className="field tabular-nums" inputMode="numeric" value={f.trainingMinutes} onChange={set("trainingMinutes")} />
        </label>
        <label className="sm:col-span-2">
          <span className="label">{t("kkl.del.trainingMoney")}</span>
          <AmountInput value={f.trainingMoney} onChange={set("trainingMoney")} />
        </label>
        <div className="sm:col-span-4">
          <ErrorText error={calc.error ?? save.error} />
        </div>
        <div className="flex flex-wrap gap-2 sm:col-span-4">
          <button className="btn-primary" disabled={calc.isPending}>
            {t("kkl.del.calc")}
          </button>
          <button type="button" className="btn-ghost" disabled={save.isPending} onClick={() => save.mutate()}>
            {t("kkl.del.save")}
          </button>
        </div>
      </form>
      {result && <DelegateResult r={result} />}
      <h3 className="font-semibold">{t("kkl.del.saved")}</h3>
      {data.delegations.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("kkl.del.empty")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.delegations.map((d) => (
            <DelegationRow key={d.id} spaceId={spaceId} d={d} />
          ))}
        </ul>
      )}
    </section>
  );
}

function DelegateResult({ r }: { r: KkDelegateResultDto }) {
  const { t } = useTranslation();
  const delegate = r.verdict === "DELEGATE";
  const payback = r.paybackMonths == null ? "—" : r.paybackMonths === 0 ? t("kkl.del.now") : t("kkl.del.months", { count: r.paybackMonths });
  return (
    <div role="status" data-testid="kkl-delegate-result" className="flex flex-col gap-2 rounded-md border border-line p-3">
      <p className="text-sm font-medium">{t("kkl.del.result")}</p>
      <table className="w-full max-w-xl text-sm">
        <tbody>
          <tr>
            <td className="py-1 text-ink-muted">{t("kkl.del.benefit")}</td>
            <td data-testid="kkl-benefit" className="py-1 text-right tabular-nums">
              {r.monthlyBenefit.formatted}
            </td>
          </tr>
          <tr>
            <td className="py-1 text-ink-muted">
              {t("kkl.del.fullCost")}{" "}
              <span className="text-xs">
                (
                {t("kkl.del.timeCost", {
                  amount: r.trainingTimeCost.formatted,
                })}
                )
              </span>
            </td>
            <td data-testid="kkl-full-cost" className="py-1 text-right tabular-nums">
              {r.fullCost.formatted}
            </td>
          </tr>
          {delegate && (
            <tr>
              <td className="py-1 text-ink-muted">{t("kkl.del.payback")}</td>
              <td data-testid="kkl-payback" className="py-1 text-right font-semibold tabular-nums text-accent-text">
                {payback}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <p data-testid="kkl-verdict" className={delegate ? "text-sm" : "text-sm text-warn"}>
        {delegate
          ? t("kkl.del.verdict.DELEGATE", {
              benefit: r.monthlyBenefit.formatted,
            })
          : t("kkl.del.verdict.SELF_CHEAPER")}
      </p>
    </div>
  );
}

function DelegationRow({ spaceId, d }: { spaceId: string; d: KkDelegationDto }) {
  const { t } = useTranslation();
  // O'chirish — ikki bosqichda: avval tasdiq so'raladi (tasodifiy bosishdan himoya).
  const [confirming, setConfirming] = useState(false);
  const del = useMutation({
    mutationFn: () => call(commands.kkDelegationDelete(spaceId, d.id)),
    onSettled: () => setConfirming(false),
  });
  const r = d.result;
  return (
    <li aria-label={t("kkl.del.label", { task: d.task })} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
      <span className="font-medium">{d.task}</span>
      {d.staffName && <span className="text-ink-muted">{d.staffName}</span>}
      <span className="text-ink-muted">
        {t("kkl.del.line", {
          time: showMinutes(t, d.taskMinutes),
          helper: d.helperHourCost.formatted,
          date: showDate(d.decidedOn),
        })}
      </span>
      <span className={r.verdict === "DELEGATE" ? "tabular-nums text-accent-text" : "text-warn"}>
        {r.verdict === "DELEGATE" ? (r.paybackMonths === 0 ? t("kkl.del.now") : t("kkl.del.months", { count: r.paybackMonths ?? 0 })) : t("kkl.del.verdict.SELF_CHEAPER")}
      </span>
      {confirming ? (
        <span role="group" aria-label={t("kkl.del.confirm", { task: d.task })} className="ml-auto flex flex-wrap items-center gap-2">
          <span className="text-warn">{t("kkl.del.confirm", { task: d.task })}</span>
          <button className="btn-ghost text-xs" disabled={del.isPending} onClick={() => del.mutate()}>
            {t("kkl.del.confirmYes")}
          </button>
          <button className="btn-ghost text-xs" onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </button>
        </span>
      ) : (
        <button className="btn-ghost ml-auto text-xs" onClick={() => setConfirming(true)}>
          {t("kkl.del.delete")}
        </button>
      )}
      <ErrorText error={del.error} />
    </li>
  );
}

/** «Ilm zakoti» (8A.3): shu oy xodimlarga va boshqalarga o'rgatilgani. Pul hisobi yo'q. */
function TeachingCard({ data, onAdd }: { data: KkLearningOverviewDto; onAdd: () => void }) {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="kkl-teach" className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="kkl-teach" className="text-xl font-semibold">
          {t("learn.teach.title")}
        </h2>
        <button className="btn-ghost" onClick={onAdd}>
          {t("learn.teach.add")}
        </button>
      </div>
      <p className="text-sm text-ink-muted">{t("kkl.teach.hint")}</p>
      <p data-testid="kkl-teach-count" className="font-medium">
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
              {r.learner && <span>{t("learn.teach.to", { learner: r.learner })}</span>}
              {r.minutes != null && <span className="text-ink-muted">{showMinutes(t, r.minutes)}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function KkTeachingDialog({ spaceId, staff, onClose }: { spaceId: string; staff: KkStaffOptionDto[]; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [f, setF] = useState({
    agreementId: staff[0]?.id ?? "",
    learner: "",
    topic: "",
    minutes: "",
    occurredOn: "",
  });
  const add = useMutation({
    mutationFn: () =>
      call(
        commands.kkTeachingAdd(spaceId, {
          occurredOn: f.occurredOn || null,
          agreementId: f.agreementId || null,
          learner: f.agreementId || f.learner.trim() === "" ? null : f.learner,
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
        <p className="text-sm text-ink-muted">{t("kkl.teach.hint")}</p>
        <label>
          <span className="label">{t("learn.teach.topic")}</span>
          <input autoFocus className="field" value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("kkl.teach.staff")}</span>
          <select className="field" value={f.agreementId} onChange={(e) => setF({ ...f, agreementId: e.target.value })}>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
            <option value="">{t("kkl.teach.other")}</option>
          </select>
        </label>
        {!f.agreementId && (
          <label>
            <span className="label">{t("kkl.teach.learner")}</span>
            <input className="field" value={f.learner} onChange={(e) => setF({ ...f, learner: e.target.value })} />
          </label>
        )}
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
