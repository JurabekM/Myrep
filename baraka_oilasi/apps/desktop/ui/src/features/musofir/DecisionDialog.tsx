import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfDecisionInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";

const KINDS = ["LEND", "PARTNERSHIP", "INVEST", "PURCHASE", "OTHER"] as const;
const REPLIES = ["YES", "NO", "UNKNOWN"] as const;
const CHOICES = ["WAIT", "PROCEED", "DECLINE"] as const;
/** U12 «Taklifni tekshirish» savollari — matnlari `offer.*` da (bir xil jadval). */
const OFFER_KEYS = new Set(["guaranteed", "lossShared", "realActivity", "recruitment", "urgency", "written"]);
const MF_FLAGS = new Set([
  "FRESH_RETURN_APPROACH",
  "UPFRONT_BEFORE_DOCUMENTS",
  "UPFRONT_UNKNOWN",
  "ABROAD_JOB_FEE",
  "NO_REPAYMENT_DATE",
  "REPAYMENT_DATE_UNKNOWN",
  "NOT_DISCUSSED",
  "COOLING_PERIOD",
  "COOLING_BIG_DECISION",
  "LARGE_SHARE",
]);
const TONE: Record<string, string> = { GREEN: "border-accent", YELLOW: "border-warn", RED: "border-danger" };
const TEXT: Record<string, string> = { GREEN: "text-accent-text", YELLOW: "text-warn", RED: "text-danger" };

/**
 * Katta qaror oldidan tekshiruv (musofir/SPEC 6.3): kengaytirilgan taklif detektori va sovutish
 * qoidasi. Natija va bayroqlar — yadrodan; qaror taqiqlanmaydi, musofir o'zi tanlaydi.
 */
export function DecisionDialog({ spaceId, homeCurrency, onClose }: { spaceId: string; homeCurrency: string; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const [kind, setKind] = useState<string>("LEND");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [a, setA] = useState<Record<string, string>>({});
  const questions = useQuery({ queryKey: keys.mfQuestions(kind), queryFn: () => call(commands.mfDecisionQuestions(kind)) });
  const asked = questions.data ?? [];
  const input = (choice: string | null): MfDecisionInput => ({
    kind,
    title,
    amount,
    answers: asked.filter((q) => a[q]).map((q) => ({ key: q, reply: a[q] ?? "" })),
    choice,
    note: note.trim() || null,
  });
  const check = useMutation({ mutationFn: () => call(commands.mfCheckDecision(spaceId, input(null))) });
  const record = useMutation({ mutationFn: (choice: string) => call(commands.mfRecordDecision(spaceId, input(choice))), onSuccess: onClose });
  const complete = asked.length > 0 && asked.every((q) => a[q]) && title.trim() !== "" && amount.trim() !== "";
  const changed = () => {
    check.reset();
    record.reset();
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    check.mutate();
  };
  const r = check.data;
  const flagText = (code: string) =>
    t(MF_FLAGS.has(code) ? `mf.flag.${code}` : `offer.flag.${code}`, {
      percent: r?.sharePercent ?? "",
      date: r?.endsOn ? showDate(r.endsOn) : "",
      days: r?.daysLeft ?? 0,
    });
  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("mf.decision.title")} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <form className="card flex max-h-full w-full max-w-2xl flex-col gap-4 overflow-y-auto" onSubmit={submit}>
        <h2 className="text-xl font-semibold">{t("mf.decision.title")}</h2>
        <p className="text-sm text-ink-muted">{t("mf.decision.dialogIntro")}</p>
        <div className="grid gap-3 md:grid-cols-2">
          <label>
            <span className="label">{t("mf.decision.kind")}</span>
            <select
              className="field"
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                changed();
              }}
            >
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`mf.decision.kindName.${k}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="label">{t("mf.decision.amount", { currency: homeCurrency })}</span>
            <AmountInput
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                changed();
              }}
              required
            />
          </label>
          <label className="md:col-span-2">
            <span className="label">{t("mf.decision.what")}</span>
            <input
              className="field"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                changed();
              }}
              required
            />
          </label>
        </div>
        <ErrorText error={questions.error} />
        {asked.map((q) => (
          <div key={q} role="radiogroup" aria-labelledby={`mfq-${q}`} className="flex flex-col gap-1">
            <p id={`mfq-${q}`} className="font-medium">
              {t(OFFER_KEYS.has(q) ? `offer.q.${q}` : `mf.q.${q}`)}
            </p>
            <div className="flex flex-wrap gap-4 text-sm">
              {REPLIES.map((v) => (
                <label key={v} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`mfq-${q}`}
                    checked={a[q] === v}
                    onChange={() => {
                      setA({ ...a, [q]: v });
                      changed();
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
          <div role="status" data-testid="mf-decision-result" className={`card flex flex-col gap-2 border-2 ${TONE[r.verdict] ?? ""}`}>
            <p className={`text-lg font-semibold ${TEXT[r.verdict] ?? ""}`}>{t(`mf.verdict.${r.verdict}`)}</p>
            {r.flags.map((f) => (
              <p key={f.code} className="text-sm">
                <span className={TEXT[f.level] ?? ""}>●</span> {flagText(f.code)}
              </p>
            ))}
            {r.waitUntil && <p className="text-sm font-medium">{t("mf.decision.waitUntil", { date: showDate(r.waitUntil) })}</p>}
            <p className="text-sm text-ink-muted">{t(`mf.decision.advice.${r.verdict}`)}</p>
            <label>
              <span className="label">{t("kk.note")}</span>
              <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
            </label>
            <div role="group" aria-label={t("mf.decision.choose")} className="flex flex-wrap gap-2">
              {CHOICES.map((c) => (
                <button key={c} type="button" className={c === "WAIT" ? "btn-primary" : "btn-ghost"} disabled={record.isPending} onClick={() => record.mutate(c)}>
                  {t(`mf.choice.${c}`)}
                </button>
              ))}
            </div>
            <ErrorText error={record.error} />
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          {!r && (
            <button className="btn-primary" disabled={!complete || check.isPending}>
              {t("offer.check")}
            </button>
          )}
          <button type="button" className="btn-ghost" onClick={onClose}>
            {t("common.close")}
          </button>
        </div>
      </form>
    </div>
  );
}
