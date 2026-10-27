import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type LearningMemberDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { useDialog } from "../../lib/useDialog";
import { parseCount, toMinutes } from "./time";

const PATHS = ["BOOK", "MENTOR", "COURSE", "PRACTICE"] as const;

/** Yangi bilim rejasi (2G.2): bir a'zoda ko'pi bilan 2 ta faol reja — chegarani yadro tekshiradi. */
export function PlanDialog({ spaceId, members, onClose }: { spaceId: string; members: LearningMemberDto[]; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [f, setF] = useState({ memberId: members[0]?.memberId ?? "", skill: "", purpose: "", paths: [] as string[], budget: "", hours: "", minutes: "", startOn: "", reviewOn: "" });
  const create = useMutation({
    mutationFn: () =>
      call(
        commands.learningPlanCreate(spaceId, {
          memberId: f.memberId,
          skill: f.skill,
          purpose: f.purpose.trim() === "" ? null : f.purpose,
          paths: f.paths,
          budget: f.budget.trim() === "" ? null : f.budget,
          weeklyMinutes: toMinutes(f.hours, f.minutes),
          startOn: f.startOn || null,
          reviewOn: f.reviewOn || null,
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
        {members.length > 1 && (
          <label>
            <span className="label">{t("learn.plan.member")}</span>
            <select className="field" value={f.memberId} onChange={(e) => setF({ ...f, memberId: e.target.value })}>
              {members.map((m) => (
                <option key={m.memberId} value={m.memberId}>
                  {m.displayName}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          <span className="label">{t("learn.plan.skill")}</span>
          <input autoFocus className="field" placeholder={t("learn.plan.skillPlaceholder")} value={f.skill} onChange={(e) => setF({ ...f, skill: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("learn.plan.purpose")}</span>
          <input className="field" value={f.purpose} onChange={(e) => setF({ ...f, purpose: e.target.value })} />
        </label>
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
          <span className="label">{t("learn.plan.budget")}</span>
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
        <p className="text-sm text-ink-muted">{t("learn.plan.money")}</p>
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

/** «Ilm zakoti» yozuvi (2G.6): kimga (ixtiyoriy), nimani, qancha vaqt. */
export function TeachingDialog({ spaceId, members, onClose }: { spaceId: string; members: LearningMemberDto[]; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [f, setF] = useState({ memberId: members[0]?.memberId ?? "", occurredOn: "", learner: "", topic: "", minutes: "" });
  const add = useMutation({
    mutationFn: () =>
      call(
        commands.teachingLogAdd(spaceId, {
          memberId: f.memberId,
          occurredOn: f.occurredOn || null,
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
        <p className="text-sm text-ink-muted">{t("learn.teach.hint")}</p>
        {members.length > 1 && (
          <label>
            <span className="label">{t("learn.teach.member")}</span>
            <select className="field" value={f.memberId} onChange={(e) => setF({ ...f, memberId: e.target.value })}>
              {members.map((m) => (
                <option key={m.memberId} value={m.memberId}>
                  {m.displayName}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          <span className="label">{t("learn.teach.topic")}</span>
          <input autoFocus className="field" value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("learn.teach.learner")}</span>
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
