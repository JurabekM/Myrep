import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type StudyDebtInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { BorrowCheckFields, StudyDebtWarnings } from "../../components/BorrowCheckFields";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

const NECESSITIES = ["ZARUR", "KERAK", "HAVAS"] as const;
const NO_ANSWERS: StudyDebtInput = { need: "", alternatives: [], withInterest: null };

/** Tez xarajat kiritish: toifa kategoriyadan olinadi va oʻzgartirilishi mumkin (havas — neytral rangda). */
export function ExpensesScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)) });
  const summary = useQuery({ queryKey: keys.summary(spaceId, null), queryFn: () => call(commands.monthlySummary(spaceId, null, null)) });
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [necessity, setNecessity] = useState<string | null>(null);
  const [channel, setChannel] = useState<"CASH" | "CARD">("CASH");
  // «O'zimga sarmoya» belgisi (uy/SPEC 2G.3). Bu ekran faqat Uy menyusida (Kasb-kor, Musofir va
  // sotuvchi menyularida yo'q; Kasb-kor va Musofir belgisi — o'z yozuv oynalarida). Rejalar faqat belgi qo'yilganda o'qiladi.
  const [selfInvestment, setSelfInvestment] = useState(false);
  const learning = useQuery({ queryKey: keys.learning(spaceId), queryFn: () => call(commands.learningOverview(spaceId, null)), enabled: selfInvestment });
  const [memberId, setMemberId] = useState("");
  const [planId, setPlanId] = useState("");
  // Oʻqish puli qarzga boʻlsa — 2D.6 «Toʻxta va oʻyla» (uy/SPEC 2G.2): javoblar oldindan tanlanmaydi,
  // avval «Tekshirish» (ogohlantirishlar), keyin «Oʻyladim, saqlash» — qarz qoʻshishdagi kabi.
  const [onDebt, setOnDebt] = useState(false);
  const [debt, setDebtState] = useState<StudyDebtInput>(NO_ANSWERS);
  const [warnings, setWarnings] = useState<string[] | null>(null);
  const setDebt = (v: StudyDebtInput) => {
    setDebtState(v);
    setWarnings(null);
  };
  const studyDebt = selfInvestment && onDebt;
  const answered = debt.need !== "" && debt.withInterest !== null;
  const members = learning.data?.members ?? [];
  const names = new Map(members.map((m) => [m.memberId, m.displayName]));
  // Faqat ochiq (`ACTIVE`/`PAUSED`) rejalar; a'zo tanlangan bo'lsa — uning rejalari.
  const plans = (learning.data?.plans ?? []).filter((p) => (p.status === "ACTIVE" || p.status === "PAUSED") && (memberId === "" || p.memberId === memberId));
  const plan = plans.find((p) => p.id === planId);

  const save = useMutation({
    mutationFn: async () => {
      if (studyDebt && warnings === null) {
        setWarnings(await call(commands.previewStudyDebt(debt)));
        return false;
      }
      await call(
        commands.recordExpense(spaceId, {
          amount,
          categoryId,
          channel,
          // Reja tanlansa — xarajat reja a'zosiniki (yadro mosligini tekshiradi).
          memberId: selfInvestment ? memberId || plan?.memberId || null : null,
          occurredOn: null,
          necessity,
          obligationId: null,
          isGift: false,
          isOstentation: false,
          fundedByDebt: studyDebt,
          note: null,
          selfInvestment,
          learningPlanId: selfInvestment && plan ? plan.id : null,
          studyDebt: studyDebt ? debt : null,
        }),
      );
      return true;
    },
    onSuccess: (saved) => {
      if (!saved) return;
      setAmount("");
      setNecessity(null);
      setSelfInvestment(false);
      setPlanId("");
      setOnDebt(false);
      setDebt(NO_ANSWERS);
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  const selected = categories.data?.find((c) => c.id === categoryId);
  const by = summary.data?.byNecessity;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("expense.title")}</h1>
      <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label>
          <span className="label">{t("common.amount")}</span>
          <AmountInput autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("expense.category")}</span>
          <select className="field" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
            <option value="" disabled>—</option>
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.customName ?? t(c.nameKey)}</option>
            ))}
          </select>
        </label>
        <div className="flex gap-2">
          {NECESSITIES.map((n) => {
            const active = (necessity ?? selected?.defaultNecessity) === n;
            return (
              <button key={n} type="button" aria-pressed={active} className={active ? "btn-primary" : "btn-ghost"} onClick={() => setNecessity(n)}>
                {t(`necessity.${n}`)}
              </button>
            );
          })}
        </div>
        <div className="flex gap-2">
          {(["CASH", "CARD"] as const).map((c) => (
            <button key={c} type="button" aria-pressed={channel === c} className={channel === c ? "btn-primary" : "btn-ghost"} onClick={() => setChannel(c)}>
              {t(`income.channel.${c}`)}
            </button>
          ))}
        </div>
        <fieldset className="flex flex-col gap-3 md:col-span-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={selfInvestment} onChange={(e) => setSelfInvestment(e.target.checked)} />
            {t("expense.selfInvestment")}
          </label>
          <p className="text-sm text-ink-muted">{t("expense.selfInvestmentHint")}</p>
          {selfInvestment && (
            <div className="grid gap-4 md:grid-cols-2">
              {members.length > 1 && (
                <label>
                  <span className="label">{t("expense.member")}</span>
                  <select
                    className="field"
                    value={memberId}
                    onChange={(e) => {
                      setMemberId(e.target.value);
                      setPlanId("");
                    }}
                  >
                    <option value="">—</option>
                    {members.map((m) => (
                      <option key={m.memberId} value={m.memberId}>
                        {m.displayName}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                <span className="label">{t("expense.plan")}</span>
                <select className="field" value={planId} onChange={(e) => setPlanId(e.target.value)}>
                  <option value="">—</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {members.length > 1 ? `${p.skill} · ${names.get(p.memberId) ?? ""}` : p.skill}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 md:col-span-2">
                <input type="checkbox" checked={onDebt} onChange={(e) => setOnDebt(e.target.checked)} />
                {t("expense.studyOnDebt")}
              </label>
              {onDebt && (
                <>
                  <p role="note" className="text-sm text-warn md:col-span-2">
                    {t("expense.studyOnDebtHint")}
                  </p>
                  <BorrowCheckFields value={debt} onChange={(v) => setDebt({ ...debt, ...v })} />
                  <fieldset className="md:col-span-2">
                    <legend className="label">{t("expense.studyDebt.interest")}</legend>
                    <div className="flex flex-wrap gap-4">
                      {([true, false] as const).map((v) => (
                        <label key={String(v)} className="flex items-center gap-2">
                          <input type="radio" name="withInterest" required checked={debt.withInterest === v} onChange={() => setDebt({ ...debt, withInterest: v })} />
                          {t(`expense.studyDebt.interest.${v ? "YES" : "NO"}`)}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  {warnings && <StudyDebtWarnings warnings={warnings} />}
                </>
              )}
            </div>
          )}
        </fieldset>
        <div className="md:col-span-2"><ErrorText error={save.error} /></div>
        <div className="md:col-span-2">
          <button className="btn-primary" disabled={save.isPending || (studyDebt && !answered)}>
            {!studyDebt ? t("common.save") : warnings === null ? t("friction.check") : t("friction.confirm")}
          </button>
        </div>
      </form>
      {by && (
        <div className="grid gap-4 md:grid-cols-4">
          <Total label={t("necessity.ZARUR")} value={by.zarur.formatted} tone="text-zarur" />
          <Total label={t("necessity.KERAK")} value={by.kerak.formatted} tone="text-kerak" />
          <Total label={t("necessity.HAVAS")} value={by.havas.formatted} tone="text-havas" />
          <Total label={t("audit.sadaqa")} value={by.sadaqa.formatted} tone="text-accent-text" />
          {summary.data && <Total label={t("expense.selfInvestmentTotal")} value={summary.data.selfInvestment.total.formatted} tone="text-accent-text" />}
        </div>
      )}
    </section>
  );
}

function Total({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="card">
      <p className={`text-sm ${tone}`}>{label}</p>
      <p className="text-lg font-medium tabular-nums">{value}</p>
    </div>
  );
}
