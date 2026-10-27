import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type OfferCheckDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { useDialog } from "../../lib/useDialog";
import type { OfferMode } from "../../state/ui";

const OFFER_QUESTIONS = ["guaranteed", "lossShared", "realActivity", "recruitment", "urgency", "written", "licensed", "inspection", "exitEasy"] as const;
/** Kurs yoki ustoz taklifi (uy/SPEC 2G.4): 8 savol. Musofirning `jobAbroad` savoli — M6 da. */
const COURSE_QUESTIONS = ["fastRich", "secretFormula", "incomeGuarantee", "syllabus", "teacherVerifiable", "urgency", "recruitment", "trialOrRefund"] as const;
const MODES = ["OFFER", "COURSE"] as const;
const REPLIES = ["YES", "NO", "UNKNOWN"] as const;
const TONE: Record<string, string> = { GREEN: "border-accent", YELLOW: "border-warn", RED: "border-danger" };
const TEXT: Record<string, string> = { GREEN: "text-accent-text", YELLOW: "text-warn", RED: "text-danger" };

/**
 * «Kafolatlangan foyda» detektori (uy/SPEC 2E.5): tavakkalsiz, kafolatlangan foyda va'da qilinsa —
 * u yerda yo ribo, yo firibgarlik bor. `COURSE` turi — kurs yoki ustoz taklifi (2G.4): pul faqat
 * haqiqiy hunar va bilim uchun. Qaror jadvali yadroda; hech narsa saqlanmaydi.
 */
export function OfferCheckDialog({ onClose, initialMode = "OFFER" }: { onClose: () => void; initialMode?: OfferMode }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [mode, setMode] = useState<OfferMode>(initialMode);
  const [a, setA] = useState<Record<string, string>>({});
  const check = useMutation({
    mutationFn: (m: OfferMode): Promise<OfferCheckDto> => {
      const v = (q: string) => a[q] ?? "";
      if (m === "COURSE") {
        return call(
          commands.checkCourse({
            fastRich: v("fastRich"),
            secretFormula: v("secretFormula"),
            incomeGuarantee: v("incomeGuarantee"),
            syllabus: v("syllabus"),
            teacherVerifiable: v("teacherVerifiable"),
            urgency: v("urgency"),
            recruitment: v("recruitment"),
            trialOrRefund: v("trialOrRefund"),
            jobAbroad: null,
          }),
        );
      }
      return call(
        commands.checkOffer({
          guaranteed: v("guaranteed"),
          lossShared: v("lossShared"),
          realActivity: v("realActivity"),
          recruitment: v("recruitment"),
          urgency: v("urgency"),
          written: v("written"),
          licensed: v("licensed"),
          inspection: v("inspection"),
          exitEasy: v("exitEasy"),
        }),
      );
    },
  });
  const course = mode === "COURSE";
  const questions: readonly string[] = course ? COURSE_QUESTIONS : OFFER_QUESTIONS;
  const qKey = (q: string) => (course ? `offer.course.q.${q}` : `offer.q.${q}`);
  const complete = questions.every((q) => a[q]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    check.mutate(mode);
  };
  const switchMode = (m: OfferMode) => {
    setMode(m);
    setA({});
    check.reset();
  };
  const r = check.data;
  const flagText = (code: string) => (course && code === "TWO_SIGNS" ? t("offer.course.twoSigns") : t(`offer.flag.${code}`));
  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("offer.title")} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <form className="card flex max-h-full w-full max-w-2xl flex-col gap-4 overflow-y-auto" onSubmit={submit}>
        <h2 className="text-xl font-semibold">{t("offer.title")}</h2>
        <div role="group" aria-label={t("offer.mode")} className="flex flex-wrap gap-2">
          {MODES.map((m) => (
            <button key={m} type="button" aria-pressed={mode === m} className={mode === m ? "btn-primary text-sm" : "btn-ghost text-sm"} onClick={() => switchMode(m)}>
              {t(`offer.mode.${m}`)}
            </button>
          ))}
        </div>
        <p className="text-sm text-ink-muted">{t(course ? "offer.course.intro" : "offer.intro")}</p>
        {questions.map((q) => (
          <div key={`${mode}-${q}`} role="radiogroup" aria-labelledby={`offer-${q}`} className="flex flex-col gap-1">
            <p id={`offer-${q}`} className="font-medium">
              {t(qKey(q))}
            </p>
            <div className="flex flex-wrap gap-4 text-sm">
              {REPLIES.map((v) => (
                <label key={v} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={q}
                    checked={a[q] === v}
                    onChange={() => {
                      setA({ ...a, [q]: v });
                      check.reset();
                    }}
                  />
                  {t(`offer.reply.${v}`)}
                </label>
              ))}
            </div>
          </div>
        ))}
        <ErrorText error={check.error} />
        {r && (
          <div role="status" data-testid="offer-result" className={`card flex flex-col gap-2 border-2 ${TONE[r.verdict] ?? ""}`}>
            <p className={`text-lg font-semibold ${TEXT[r.verdict] ?? ""}`}>{t(course ? `offer.course.verdict.${r.verdict}` : `offer.verdict.${r.verdict}`)}</p>
            {r.signs > 0 && <p className="text-sm font-medium">{t(course ? "offer.course.signs" : "offer.signs", { count: r.signs })}</p>}
            {r.flags.map((f) => (
              <p key={f.code} className="text-sm">
                <span className={TEXT[f.level] ?? ""}>●</span> {flagText(f.code)}
              </p>
            ))}
            <p className="text-sm text-ink-muted">{t(course ? `offer.course.advice.${r.verdict}` : `offer.advice.${r.verdict}`)}</p>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={!complete || check.isPending}>
            {t("offer.check")}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            {t("common.close")}
          </button>
        </div>
      </form>
    </div>
  );
}
