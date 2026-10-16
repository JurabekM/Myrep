import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type VentureIdeaDto, type VentureIdeaInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

const SCENARIOS = ["PESSIMISTIC", "BASE", "OPTIMISTIC"] as const;

type Draft = {
  title: string;
  skillId: string;
  capex: { title: string; amount: string }[];
  scenarios: Record<string, { income: string; expense: string }>;
  partnered: boolean;
  share: string;
};

const blank = (): Draft => ({
  title: "",
  skillId: "",
  capex: [{ title: "", amount: "" }],
  scenarios: Object.fromEntries(SCENARIOS.map((s) => [s, { income: "", expense: "" }])),
  partnered: true,
  share: "50",
});

/** Foiz matni → basis points (butun son; pul emas). */
function toBp(v: string): number {
  const m = /^(\d{1,3})(?:[.,](\d{1,2}))?$/.exec(v.trim());
  if (!m) throw new CoreError({ code: "INVALID_PERCENT", field: "workerShareBp" });
  return Number(m[1]) * 100 + Number((m[2] ?? "").padEnd(2, "0"));
}

function toInput(d: Draft): VentureIdeaInput {
  return {
    title: d.title,
    skillId: d.skillId || null,
    capex: d.capex.filter((c) => c.title.trim() !== "" || c.amount.trim() !== ""),
    scenarios: SCENARIOS.map((name) => ({ name, income: d.scenarios[name]?.income ?? "", expense: d.scenarios[name]?.expense ?? "" })),
    workerShareBp: d.partnered ? toBp(d.share) : null,
  };
}

function fromDto(i: VentureIdeaDto): Draft {
  return {
    title: i.title,
    skillId: i.skillId ?? "",
    capex: i.capexLines.map((c) => ({ title: c.title, amount: c.amount.plain })),
    scenarios: Object.fromEntries(i.scenarios.map((s) => [s.name, { income: s.income.plain, expense: s.expense.plain }])),
    partnered: i.workerShareBp != null,
    share: i.workerShareBp == null ? "50" : String(i.workerShareBp / 100).replace(".", ","),
  };
}

/**
 * «Hunardan ishga» (uy/SPEC 2E.4): oiladagi bekor yotgan hunar → mini biznes-hisob, uch stsenariy
 * («hisob-kitobni uch marta qildim»), qoplanish muddati; bir bosishda sheriklik qoralamasi.
 */
export function IdeasScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const ideas = useQuery({ queryKey: keys.ideas(spaceId), queryFn: () => call(commands.ventureIdeas(spaceId)) });
  const [editing, setEditing] = useState<VentureIdeaDto | "new" | null>(null);
  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("ideas.title")}</h1>
        <button className="btn-primary" onClick={() => setEditing("new")}>
          {t("ideas.new")}
        </button>
      </div>
      <aside className="card flex flex-col gap-2 border-accent/40">
        <p className="text-sm font-semibold text-accent-text">{t("mentor.name")}</p>
        <p>{t("ideas.intro")}</p>
      </aside>
      <Skills spaceId={spaceId} />
      {editing && <IdeaEditor spaceId={spaceId} idea={editing === "new" ? null : editing} onDone={() => setEditing(null)} />}
      <ErrorText error={ideas.error} />
      {(ideas.data ?? []).map((i) => (
        <IdeaCard key={i.id} spaceId={spaceId} idea={i} onEdit={() => setEditing(i)} />
      ))}
    </section>
  );
}

function Skills({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const skills = useQuery({ queryKey: keys.skills(spaceId), queryFn: () => call(commands.skills(spaceId)) });
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const [f, setF] = useState({ title: "", memberId: "" });
  const add = useMutation({
    mutationFn: () => call(commands.addSkill(spaceId, { title: f.title, memberId: f.memberId || null, note: null })),
    onSuccess: (list) => {
      qc.setQueryData(keys.skills(spaceId), list);
      setF({ title: "", memberId: "" });
    },
  });
  const del = useMutation({ mutationFn: (id: string) => call(commands.deleteSkill(spaceId, id)), onSuccess: (list) => qc.setQueryData(keys.skills(spaceId), list) });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  return (
    <div className="card flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("ideas.skills")}</h2>
      <p className="text-sm text-ink-muted">{t("ideas.skillsHint")}</p>
      <div className="flex flex-wrap gap-2">
        {(skills.data ?? []).map((s) => (
          <span key={s.id} className="flex items-center gap-2 rounded-full border border-line px-3 py-1 text-sm">
            {s.title}
            {s.memberName && <span className="text-ink-muted">· {s.memberName}</span>}
            <button aria-label={t("ideas.removeSkill", { name: s.title })} className="text-ink-muted hover:text-danger" onClick={() => del.mutate(s.id)}>
              ×
            </button>
          </span>
        ))}
      </div>
      <form className="flex flex-wrap items-end gap-2" onSubmit={submit}>
        <label className="min-w-48 flex-1">
          <span className="label">{t("ideas.skill")}</span>
          <input className="field" placeholder={t("ideas.skillPlaceholder")} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
        </label>
        <label>
          <span className="label">{t("ideas.who")}</span>
          <select className="field" value={f.memberId} onChange={(e) => setF({ ...f, memberId: e.target.value })}>
            <option value="">—</option>
            {(household.data?.members ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.displayName}
              </option>
            ))}
          </select>
        </label>
        <button className="btn-ghost" disabled={add.isPending}>
          + {t("ideas.addSkill")}
        </button>
      </form>
      <ErrorText error={add.error ?? del.error} />
    </div>
  );
}

function IdeaEditor({ spaceId, idea, onDone }: { spaceId: string; idea: VentureIdeaDto | null; onDone: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const skills = useQuery({ queryKey: keys.skills(spaceId), queryFn: () => call(commands.skills(spaceId)) });
  const [d, setD] = useState<Draft>(idea ? fromDto(idea) : blank());
  const save = useMutation({
    mutationFn: () => {
      const input = toInput(d);
      return call(idea ? commands.updateVentureIdea(spaceId, idea.id, input) : commands.createVentureIdea(spaceId, input));
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.ideas(spaceId) });
      onDone();
    },
  });
  const sc = (name: string, patch: Partial<{ income: string; expense: string }>) =>
    setD({ ...d, scenarios: { ...d.scenarios, [name]: { income: "", expense: "", ...d.scenarios[name], ...patch } } });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card flex flex-col gap-4" onSubmit={submit} aria-label={t("ideas.editor")}>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>
          <span className="label">{t("ideas.ideaTitle")}</span>
          <input className="field" value={d.title} onChange={(e) => setD({ ...d, title: e.target.value })} required />
        </label>
        <label>
          <span className="label">{t("ideas.skill")}</span>
          <select className="field" value={d.skillId} onChange={(e) => setD({ ...d, skillId: e.target.value })}>
            <option value="">—</option>
            {(skills.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="font-semibold">{t("ideas.capex")}</h3>
        <p className="text-sm text-ink-muted">{t("ideas.capexHint")}</p>
        {d.capex.map((c, i) => (
          <div key={i} className="grid items-end gap-2 sm:grid-cols-[1fr_12rem_auto]">
            <input
              className="field"
              aria-label={t("ideas.capexItem", { n: i + 1 })}
              value={c.title}
              onChange={(e) => setD({ ...d, capex: d.capex.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)) })}
            />
            <AmountInput aria-label={t("ideas.capexAmount", { n: i + 1 })} value={c.amount} onChange={(e) => setD({ ...d, capex: d.capex.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)) })} />
            <button type="button" className="btn-ghost px-3 py-2 text-sm" onClick={() => setD({ ...d, capex: d.capex.filter((_, j) => j !== i) })}>
              ×
            </button>
          </div>
        ))}
        <button type="button" className="btn-ghost self-start text-sm" onClick={() => setD({ ...d, capex: [...d.capex, { title: "", amount: "" }] })}>
          + {t("ideas.addCapex")}
        </button>
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="font-semibold">{t("ideas.scenarios")}</h3>
        <p className="text-sm text-ink-muted">{t("ideas.scenariosHint")}</p>
        <div className="grid gap-3 md:grid-cols-3">
          {SCENARIOS.map((name) => (
            <div key={name} className="flex flex-col gap-2 rounded border border-line p-3">
              <p className="font-semibold">{t(`ideas.scenario.${name}`)}</p>
              <label>
                <span className="label">{t("ideas.monthlyIncome")}</span>
                <AmountInput value={d.scenarios[name]?.income ?? ""} onChange={(e) => sc(name, { income: e.target.value })} />
              </label>
              <label>
                <span className="label">{t("ideas.monthlyExpense")}</span>
                <AmountInput value={d.scenarios[name]?.expense ?? ""} onChange={(e) => sc(name, { expense: e.target.value })} />
              </label>
            </div>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={d.partnered} onChange={(e) => setD({ ...d, partnered: e.target.checked })} />
          {t("ideas.partnered")}
        </label>
        {d.partnered && (
          <label>
            <span className="label">{t("ideas.workerShare")}</span>
            <input className="field w-28 tabular-nums" inputMode="decimal" value={d.share} onChange={(e) => setD({ ...d, share: e.target.value })} />
          </label>
        )}
      </div>
      <ErrorText error={save.error} />
      <div className="flex gap-2">
        <button className="btn-primary" disabled={save.isPending}>
          {t("ideas.calculate")}
        </button>
        <button type="button" className="btn-ghost" onClick={onDone}>
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}

function IdeaCard({ spaceId, idea, onEdit }: { spaceId: string; idea: VentureIdeaDto; onEdit: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const setScreen = useUi((s) => s.setScreen);
  const [drafting, setDrafting] = useState(false);
  const [names, setNames] = useState({ provider: "", me: "" });
  const del = useMutation({ mutationFn: () => call(commands.deleteVentureIdea(spaceId, idea.id)), onSuccess: () => void qc.invalidateQueries({ queryKey: keys.ideas(spaceId) }) });
  const draft = useMutation({
    mutationFn: () => call(commands.draftPartnershipFromIdea(spaceId, idea.id, { capitalProviderName: names.provider, myName: names.me })),
    onSuccess: () => {
      void qc.invalidateQueries();
      setScreen("partnerships");
    },
  });
  const months = (n: number | null) => (n == null ? t("ideas.never") : t("ideas.months", { n }));
  return (
    <article className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">
          {idea.title}
          {idea.skillTitle && <span className="ml-2 text-sm font-normal text-ink-muted">{idea.skillTitle}</span>}
        </h2>
        <span className="text-sm">
          {t("ideas.capexTotal")}: <span className="font-semibold tabular-nums text-accent">{idea.capex.formatted}</span>
        </span>
      </div>
      <table className="w-full text-sm tabular-nums">
        <thead className="text-left text-ink-muted">
          <tr>
            <th className="py-1" />
            <th className="text-right">{t("ideas.net")}</th>
            <th className="text-right">{t("ideas.payback")}</th>
            {idea.workerShareBp != null && <th className="text-right">{t("ideas.worker")}</th>}
            {idea.workerShareBp != null && <th className="text-right">{t("ideas.investor")}</th>}
            {idea.workerShareBp != null && <th className="text-right">{t("ideas.investorPayback")}</th>}
          </tr>
        </thead>
        <tbody>
          {idea.scenarios.map((s) => (
            <tr key={s.name} className="border-t border-line">
              <td className="py-1">{t(`ideas.scenario.${s.name}`)}</td>
              <td className={`text-right ${s.net.minor.startsWith("-") ? "text-danger" : ""}`}>{s.net.formatted}</td>
              <td className="text-right font-semibold">{months(s.paybackMonths)}</td>
              {idea.workerShareBp != null && <td className="text-right">{s.workerMonthly?.formatted}</td>}
              {idea.workerShareBp != null && <td className="text-right">{s.investorMonthly?.formatted}</td>}
              {idea.workerShareBp != null && <td className="text-right">{months(s.investorPaybackMonths)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      {idea.warnings.map((w) => (
        <p key={w} className="text-sm text-warn">
          {t(`ideas.warning.${w}`)}
        </p>
      ))}
      <p className="text-xs text-ink-muted">{t("ideas.disclaimer")}</p>
      {drafting && (
        <div className="grid gap-2 rounded border border-line p-3 sm:grid-cols-2">
          <label>
            <span className="label">{t("ideas.providerName")}</span>
            <input className="field" value={names.provider} onChange={(e) => setNames({ ...names, provider: e.target.value })} />
          </label>
          <label>
            <span className="label">{t("ideas.myName")}</span>
            <input className="field" value={names.me} onChange={(e) => setNames({ ...names, me: e.target.value })} />
          </label>
          <button className="btn-primary self-start" disabled={draft.isPending} onClick={() => draft.mutate()}>
            {t("ideas.createDraft")}
          </button>
        </div>
      )}
      <ErrorText error={del.error ?? draft.error} />
      <div className="flex flex-wrap gap-2">
        {idea.partnershipId ? (
          <button className="btn-ghost" onClick={() => setScreen("partnerships")}>
            {t("ideas.openDraft")}
          </button>
        ) : (
          !drafting && (
            <button className="btn-primary" onClick={() => setDrafting(true)}>
              {t("ideas.toContract")}
            </button>
          )
        )}
        <button className="btn-ghost" onClick={onEdit}>
          {t("ideas.edit")}
        </button>
        <button className="btn-ghost" onClick={() => del.mutate()}>
          {t("ideas.delete")}
        </button>
      </div>
    </article>
  );
}
