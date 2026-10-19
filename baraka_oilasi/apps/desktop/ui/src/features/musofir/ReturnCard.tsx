import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfOverviewDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { DecisionDialog } from "./DecisionDialog";

const VERDICT_TEXT: Record<string, string> = { GREEN: "text-accent-text", YELLOW: "text-warn", RED: "text-danger" };

/**
 * «Qaytdim» va sovutish davri (musofir/SPEC 6.3, 7-qonun): qaytgandan keyin 90 kun katta qarorlar
 * oldidan tekshiruv. Qaror taqiqlanmaydi — tanlov o'zgarmas jurnalga yoziladi (oilaga yuborilmaydi).
 */
export function ReturnCard({ spaceId, d, homeCurrency }: { spaceId: string; d: MfOverviewDto; homeCurrency: string }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [checking, setChecking] = useState(false);
  const c = d.cooling;
  const clear = useMutation({ mutationFn: () => call(commands.mfSetReturn(spaceId, { returnedOn: null, broughtHome: null })) });
  return (
    <section className="card flex flex-col gap-3" aria-label={t("mf.return.title")}>
      <h2 className="text-lg font-semibold">{t("mf.return.title")}</h2>
      {editing ? (
        <ReturnForm spaceId={spaceId} d={d} homeCurrency={homeCurrency} onDone={() => setEditing(false)} />
      ) : c ? (
        <div className="flex flex-col gap-2 text-sm">
          <p data-testid="mf-cooling" className={c.inCooling ? "text-warn" : "text-accent-text"}>
            {c.inCooling ? t("mf.return.cooling", { count: c.daysLeft, date: c.endsOn ? showDate(c.endsOn) : "" }) : t("mf.return.over", { date: c.endsOn ? showDate(c.endsOn) : "" })}
          </p>
          <p className="text-ink-muted">
            {t("mf.return.returnedLine", { date: showDate(c.returnedOn) })}
            {c.broughtHome && ` · ${t("mf.return.broughtLine", { amount: c.broughtHome.formatted })}`}
          </p>
          {c.inCooling && <p className="text-xs text-ink-muted">{t("mf.return.rule")}</p>}
          <ErrorText error={clear.error} />
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost" onClick={() => setEditing(true)}>
              {t("mf.return.change")}
            </button>
            <button className="btn-ghost" disabled={clear.isPending} onClick={() => clear.mutate()}>
              {t("mf.return.unmark")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm text-ink-muted">{t("mf.return.intro")}</p>
          <button className="btn-ghost self-start" onClick={() => setEditing(true)}>
            {t("mf.return.mark")}
          </button>
        </>
      )}
      <DecisionsLog spaceId={spaceId} onCheck={() => setChecking(true)} />
      {checking && <DecisionDialog spaceId={spaceId} homeCurrency={homeCurrency} onClose={() => setChecking(false)} />}
    </section>
  );
}

function ReturnForm({ spaceId, d, homeCurrency, onDone }: { spaceId: string; d: MfOverviewDto; homeCurrency: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [on, setOn] = useState(d.cooling?.returnedOn ?? "");
  const [brought, setBrought] = useState(d.cooling?.broughtHome?.plain ?? "");
  const save = useMutation({
    mutationFn: () => call(commands.mfSetReturn(spaceId, { returnedOn: on || null, broughtHome: brought.trim() || null })),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-col gap-3" aria-label={t("mf.return.form")} onSubmit={submit}>
      <label>
        <span className="label">{t("mf.return.date")}</span>
        <input className="field w-48" type="date" value={on} onChange={(e) => setOn(e.target.value)} required />
      </label>
      <label>
        <span className="label">{t("mf.return.brought", { currency: homeCurrency })}</span>
        <AmountInput value={brought} onChange={(e) => setBrought(e.target.value)} />
      </label>
      <p className="text-xs text-ink-muted">{t("mf.return.broughtHint")}</p>
      <ErrorText error={save.error} />
      <div className="flex gap-2">
        <button className="btn-primary" disabled={save.isPending}>
          {t("common.save")}
        </button>
        <button type="button" className="btn-ghost" onClick={onDone}>
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}

/** Katta qarorlar jurnali (o'zgarmas): tekshiruv natijasi va musofirning tanlovi. */
function DecisionsLog({ spaceId, onCheck }: { spaceId: string; onCheck: () => void }) {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: keys.mfDecisions(spaceId), queryFn: () => call(commands.mfDecisions(spaceId)) });
  const list = q.error ? [] : (q.data ?? []);
  return (
    <div className="flex flex-col gap-2 border-t border-line pt-3">
      <h3 className="font-semibold">{t("mf.decision.log")}</h3>
      <p className="text-sm text-ink-muted">{t("mf.decision.intro")}</p>
      <ErrorText error={q.error} />
      {list.length > 0 && (
        <ul className="text-sm">
          {list.map((x) => (
            <li key={x.id} data-testid="mf-decision" className="flex flex-wrap justify-between gap-2 border-t border-line py-1">
              <span>
                {showDate(x.decidedOn)} · {x.title} · <span className="tabular-nums">{x.amount.formatted}</span>
              </span>
              <span>
                <span className={VERDICT_TEXT[x.verdict] ?? ""}>{t(`mf.verdict.${x.verdict}`)}</span>
                {" · "}
                {t(`mf.choice.${x.choice}`)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <button className="btn-primary self-start" onClick={onCheck}>
        {t("mf.decision.open")}
      </button>
    </div>
  );
}
