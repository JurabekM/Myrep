import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkGateDto, type KkGrowthSettingsDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

const USABLE = ["RESERVE", "WORKING", "EXPANSION", "SADAQA"] as const;

/**
 * Kengayish darvozasi (kasbkor/SPEC 6): beshala shart va har biri uchun keyingi qadam; «Hisob kuni»
 * konvertlari (soliq zaxirasi — 8.2); foizli kreditga halol muqobillar. Hisob yadroda.
 */
export function KkGateScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const gate = useQuery({ queryKey: keys.kkGate(spaceId), queryFn: () => call(commands.kkGate(spaceId)) });
  const settings = useQuery({ queryKey: keys.kkGrowthSettings(spaceId), queryFn: () => call(commands.kkGrowthSettings(spaceId)) });
  const g = gate.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.gate.title")}</h1>
      <p className="text-ink-muted">{t("kk.gate.intro")}</p>
      <ErrorText error={gate.error} />
      {g && (
        <>
          <div data-testid="kk-gate-status" className={`card py-4 ${g.open ? "border-accent/60" : "border-warn"}`}>
            <p className={`text-xl font-semibold ${g.open ? "text-accent-text" : "text-warn"}`}>
              {g.open ? t("kk.gate.open") : t("kk.gate.closed", { count: g.reasons.length })}
            </p>
          </div>
          <Conditions g={g} />
          <Funds spaceId={spaceId} g={g} />
        </>
      )}
      <Alternatives />
      {settings.data && <Thresholds spaceId={spaceId} s={settings.data} />}
    </section>
  );
}

function Conditions({ g }: { g: KkGateDto }) {
  const { t } = useTranslation();
  const setScreen = useUi((s) => s.setScreen);
  const detail = (code: string): string => {
    switch (code) {
      case "RESERVE":
        return g.requiredReserve
          ? t("kk.gate.detail.RESERVE", { reserve: g.reserve.formatted, required: g.requiredReserve.formatted, months: g.requiredMonths, coverage: g.coverageMonths ?? "—" })
          : t("kk.gate.detail.RESERVE_NO_HISTORY", { reserve: g.reserve.formatted });
      case "PROFIT":
        return g.trueProfits.length > 0 ? t("kk.gate.detail.PROFIT", { list: g.trueProfits.map((p) => p.formatted).join(" · ") }) : t("kk.gate.detail.PROFIT_NONE");
      case "RECEIVABLES":
        return t("kk.gate.detail.RECEIVABLES", { bad: g.badDebtPercent, max: g.maxBadPercent, amount: g.receivables90.formatted });
      case "INTEREST_DEBT":
        return g.hasInterestDebt ? (g.hasPayoffPlan ? t("kk.gate.detail.DEBT_PLAN") : t("kk.gate.detail.DEBT_NO_PLAN")) : t("kk.gate.detail.NO_DEBT");
      default:
        return t("kk.gate.detail.PLAN", { count: g.plans });
    }
  };
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.gate.conditions")}>
      <h2 className="text-lg font-semibold">{t("kk.gate.conditions")}</h2>
      <ol className="flex flex-col gap-3">
        {g.conditions.map((c, i) => (
          <li key={c.code} data-testid={`kk-gate-${c.code}`} className="flex gap-3 border-t border-line pt-3">
            <span aria-hidden="true" className={`text-lg ${c.ok ? "text-accent-text" : "text-warn"}`}>
              {c.ok ? "✓" : "✗"}
            </span>
            <div className="flex-1">
              <p className="font-medium">
                {i + 1}. {t(`kk.gate.cond.${c.code}`)} <span className="sr-only">{c.ok ? t("kk.gate.met") : t("kk.gate.notMet")}</span>
              </p>
              <p className="text-sm text-ink-muted">{detail(c.code)}</p>
              {!c.ok && <p className="text-sm text-warn">{t(`kk.gate.next.${c.code}`)}</p>}
              {c.code === "PLAN" && (
                <button className="btn-ghost mt-2 px-3 py-1 text-sm" onClick={() => setScreen("ideas")}>
                  {t("kk.gate.planButton")}
                </button>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Funds({ spaceId, g }: { spaceId: string; g: KkGateDto }) {
  const { t } = useTranslation();
  const [fund, setFund] = useState<(typeof USABLE)[number]>("RESERVE");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const use = useMutation({
    mutationFn: () => call(commands.kkUseFund(spaceId, { fund, amount, usedOn: null, note: note.trim() || null })),
    onSuccess: () => {
      setAmount("");
      setNote("");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    use.mutate();
  };
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.funds.title")}>
      <h2 className="text-lg font-semibold">{t("kk.funds.title")}</h2>
      <p className="text-sm text-ink-muted">{t("kk.funds.intro")}</p>
      <div className="grid gap-3 md:grid-cols-3">
        {g.funds.map((f) => (
          <div key={f.fund} className="rounded-md border border-line p-3">
            <p className="text-sm text-ink-muted">{t(`kk.funds.name.${f.fund}`)}</p>
            <p data-testid={`kk-fund-${f.fund}`} className="text-xl font-semibold tabular-nums">
              {f.balance.formatted}
            </p>
            <p className="text-xs text-ink-muted">{t("kk.funds.flow", { added: f.added.formatted, used: f.used.formatted })}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-ink-muted">{t("kk.funds.taxHint")}</p>
      <form className="flex flex-wrap items-end gap-3 border-t border-line pt-3" aria-label={t("kk.funds.use")} onSubmit={submit}>
        <label>
          <span className="label">{t("kk.funds.fund")}</span>
          <select className="field" value={fund} onChange={(e) => setFund(e.target.value as (typeof USABLE)[number])}>
            {USABLE.map((f) => (
              <option key={f} value={f}>
                {t(`kk.funds.name.${f}`)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="label">{t("kk.funds.amount")}</span>
          <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <label className="min-w-48 flex-1">
          <span className="label">{t("kk.funds.note")}</span>
          <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <button className="btn-primary" disabled={use.isPending}>
          {t("kk.funds.useButton")}
        </button>
        <div className="w-full">
          <ErrorText error={use.error} />
        </div>
      </form>
    </section>
  );
}

function Alternatives() {
  const { t } = useTranslation();
  const setScreen = useUi((s) => s.setScreen);
  const openOffer = useUi((s) => s.openOffer);
  return (
    <section className="card flex flex-col gap-2" aria-label={t("kk.gate.altTitle")}>
      <h2 className="text-lg font-semibold">{t("kk.gate.altTitle")}</h2>
      <ul className="list-disc pl-5 text-sm">
        {["SAVINGS", "PARTNERSHIP", "SUPPLIER", "QARZ"].map((k) => (
          <li key={k}>{t(`kk.gate.alt.${k}`)}</li>
        ))}
      </ul>
      <p className="text-sm text-ink-muted">{t("kk.gate.altNoAds")}</p>
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost" onClick={() => setScreen("kkSuppliers")}>
          {t("nav.kkSuppliers")}
        </button>
        <button className="btn-ghost" onClick={openOffer}>
          {t("kk.gate.checkOffer")}
        </button>
      </div>
    </section>
  );
}

/** Darvoza chegaralari (OQ-K6): boshqa sozlamalar o'zgarmaydi. */
function Thresholds({ spaceId, s }: { spaceId: string; s: KkGrowthSettingsDto }) {
  const { t } = useTranslation();
  const [months, setMonths] = useState(String(s.reserveMonths));
  const [bad, setBad] = useState(s.maxBadPercent);
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.kkSetGrowthSettings(spaceId, {
          reserveMonths: Number.parseInt(months, 10) || 0,
          maxBadPercent: bad,
          zakatMonth: s.zakatMonth,
          zakatDay: s.zakatDay,
          goldPrice: s.goldPrice?.plain ?? null,
          nisabGrams: s.nisabGrams,
          stockValuation: s.stockValuation,
          scaleReminder: s.scaleReminder,
        }),
      ),
  });
  return (
    <form
      className="card flex flex-wrap items-end gap-3"
      aria-label={t("kk.gate.thresholds")}
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <h2 className="w-full text-lg font-semibold">{t("kk.gate.thresholds")}</h2>
      <label>
        <span className="label">{t("kk.gate.reserveMonths")}</span>
        <input className="field tabular-nums" inputMode="numeric" value={months} onChange={(e) => setMonths(e.target.value)} />
      </label>
      <label>
        <span className="label">{t("kk.gate.maxBad")}</span>
        <input className="field tabular-nums" inputMode="decimal" value={bad} onChange={(e) => setBad(e.target.value)} />
      </label>
      <button className="btn-ghost">{t("common.save")}</button>
      <div className="w-full">
        <ErrorText error={save.error} />
      </div>
    </form>
  );
}
