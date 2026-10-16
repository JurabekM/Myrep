import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type OfferAnswersInput } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";

const QUESTIONS = ["guaranteed", "lossShared", "realActivity", "recruitment", "urgency", "written"] as const;
const REPLIES = ["YES", "NO", "UNKNOWN"] as const;
const TONE: Record<string, string> = { GREEN: "border-accent", YELLOW: "border-warn", RED: "border-danger" };
const TEXT: Record<string, string> = { GREEN: "text-accent-text", YELLOW: "text-warn", RED: "text-danger" };

/**
 * «Kafolatlangan foyda» detektori (uy/SPEC 2E.5): tavakkalsiz, kafolatlangan foyda va'da qilinsa —
 * u yerda yo ribo, yo firibgarlik bor. Qaror jadvali yadroda; hech narsa saqlanmaydi.
 */
export function OfferCheckDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const [a, setA] = useState<Record<string, string>>({});
  const check = useMutation({ mutationFn: (input: OfferAnswersInput) => call(commands.checkOffer(input)) });
  const complete = QUESTIONS.every((q) => a[q]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    check.mutate({
      guaranteed: a.guaranteed ?? "",
      lossShared: a.lossShared ?? "",
      realActivity: a.realActivity ?? "",
      recruitment: a.recruitment ?? "",
      urgency: a.urgency ?? "",
      written: a.written ?? "",
    });
  };
  const r = check.data;
  return (
    <div role="dialog" aria-modal="true" aria-label={t("offer.title")} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <form className="card flex max-h-full w-full max-w-2xl flex-col gap-4 overflow-y-auto" onSubmit={submit}>
        <h2 className="text-xl font-semibold">{t("offer.title")}</h2>
        <p className="text-sm text-ink-muted">{t("offer.intro")}</p>
        {QUESTIONS.map((q) => (
          <div key={q} role="radiogroup" aria-labelledby={`offer-${q}`} className="flex flex-col gap-1">
            <p id={`offer-${q}`} className="font-medium">
              {t(`offer.q.${q}`)}
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
          <div role="status" className={`card flex flex-col gap-2 border-2 ${TONE[r.verdict] ?? ""}`}>
            <p className={`text-lg font-semibold ${TEXT[r.verdict] ?? ""}`}>{t(`offer.verdict.${r.verdict}`)}</p>
            {r.flags.map((f) => (
              <p key={f.code} className="text-sm">
                <span className={TEXT[f.level] ?? ""}>●</span> {t(`offer.flag.${f.code}`)}
              </p>
            ))}
            <p className="text-sm text-ink-muted">{t(`offer.advice.${r.verdict}`)}</p>
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
