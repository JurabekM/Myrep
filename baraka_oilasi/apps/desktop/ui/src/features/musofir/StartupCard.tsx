import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MfOverviewDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

/**
 * Qaytgandan keyingi ish (musofir/SPEC 6.2, 6.6): ish boshlash summasi — qaytish jamg'armasi maqsadining
 * bir qismi; Uy makonidagi «Hunardan ishga» g'oyasiga bog'lanadi. Bo'linish (yashash uchun) — yadrodan.
 */
export function StartupCard({ spaceId, d, homeCurrency }: { spaceId: string; d: MfOverviewDto; homeCurrency: string }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const setSpace = useUi((x) => x.setSpace);
  const setScreen = useUi((x) => x.setScreen);
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const uyId = household.data?.spaces.find((s) => s.kind === "UY")?.id ?? null;
  const s = d.startup;
  const openIdeas = () => {
    if (!uyId) return;
    setSpace(uyId);
    setScreen("ideas");
  };
  return (
    <section className="card flex flex-col gap-3" aria-label={t("mf.startup.title")}>
      <h2 className="text-lg font-semibold">{t("mf.startup.title")}</h2>
      {editing && uyId ? (
        <StartupForm spaceId={spaceId} uyId={uyId} d={d} homeCurrency={homeCurrency} onDone={() => setEditing(false)} />
      ) : s ? (
        <div data-testid="mf-startup" className="flex flex-col gap-1 text-sm">
          <p>
            {t("mf.startup.amountLine", { amount: s.startup.formatted })}
            {s.ideaTitle && <span className="text-ink-muted"> · {s.ideaTitle}</span>}
          </p>
          {s.living && <p className="text-ink-muted">{t("mf.startup.livingLine", { amount: s.living.formatted, percent: s.startupPercent })}</p>}
          {s.exceedsTarget && <p className="text-warn">{t("mf.startup.exceeds")}</p>}
        </div>
      ) : (
        <p className="text-sm text-ink-muted">{t("mf.startup.intro")}</p>
      )}
      {!editing && (
        <div className="flex flex-wrap gap-2">
          {uyId && (
            <button className="btn-ghost" onClick={() => setEditing(true)}>
              {s ? t("mf.startup.change") : t("mf.startup.set")}
            </button>
          )}
          <button className="btn-ghost" disabled={!uyId} onClick={openIdeas}>
            {t("mf.startup.openIdeas")}
          </button>
        </div>
      )}
    </section>
  );
}

function StartupForm({ spaceId, uyId, d, homeCurrency, onDone }: { spaceId: string; uyId: string; d: MfOverviewDto; homeCurrency: string; onDone: () => void }) {
  const { t } = useTranslation();
  const ideas = useQuery({ queryKey: keys.ideas(uyId), queryFn: () => call(commands.ventureIdeas(uyId)) });
  const [ideaId, setIdeaId] = useState(d.startup?.ideaId ?? "");
  const [amount, setAmount] = useState(d.startup?.startup.plain ?? "");
  const save = useMutation({
    mutationFn: (clear: boolean) =>
      call(
        commands.mfSetPlan(spaceId, {
          reserveMonths: d.reserve?.months ?? null,
          startup: clear ? null : amount.trim() || null,
          startupIdeaId: clear ? null : ideaId || null,
        }),
      ),
    onSuccess: onDone,
  });
  const pickIdea = (id: string) => {
    setIdeaId(id);
    // G'oyaning boshlang'ich sarmoyasi — taklif (uy valyutasida bo'lsa).
    const capex = ideas.data?.find((i) => i.id === id)?.capex;
    if (capex && capex.currency === homeCurrency) setAmount(capex.plain);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(false);
  };
  return (
    <form className="flex flex-col gap-3" aria-label={t("mf.startup.form")} onSubmit={submit}>
      <label>
        <span className="label">{t("mf.startup.idea")}</span>
        <select className="field" value={ideaId} onChange={(e) => pickIdea(e.target.value)}>
          <option value="">{t("mf.startup.noIdea")}</option>
          {ideas.data?.map((i) => (
            <option key={i.id} value={i.id}>
              {i.title} · {i.capex.formatted}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">{t("mf.startup.amount", { currency: homeCurrency })}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
      </label>
      <p className="text-xs text-ink-muted">{t("mf.startup.hint")}</p>
      <ErrorText error={save.error} />
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={save.isPending}>
          {t("common.save")}
        </button>
        {d.startup && (
          <button type="button" className="btn-ghost" disabled={save.isPending} onClick={() => save.mutate(true)}>
            {t("mf.startup.remove")}
          </button>
        )}
        <button type="button" className="btn-ghost" onClick={onDone}>
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
