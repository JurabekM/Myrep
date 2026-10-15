import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

const NECESSITIES = ["ZARUR", "KERAK", "HAVAS"] as const;

/** Tez xarajat kiritish: toifa kategoriyadan olinadi va oʻzgartirilishi mumkin (havas — neytral rangda). */
export function ExpensesScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)) });
  const summary = useQuery({ queryKey: keys.summary(spaceId, null), queryFn: () => call(commands.monthlySummary(spaceId, null, null)) });
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [necessity, setNecessity] = useState<string | null>(null);
  const [channel, setChannel] = useState<"CASH" | "CARD">("CASH");

  const save = useMutation({
    mutationFn: () =>
      call(
        commands.recordExpense(spaceId, {
          amount,
          categoryId,
          channel,
          memberId: null,
          occurredOn: null,
          necessity,
          obligationId: null,
          isGift: false,
          isOstentation: false,
          fundedByDebt: false,
          note: null,
        }),
      ),
    onSuccess: () => {
      setAmount("");
      setNecessity(null);
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
        <div className="md:col-span-2"><ErrorText error={save.error} /></div>
        <div className="md:col-span-2">
          <button className="btn-primary" disabled={save.isPending}>{t("common.save")}</button>
        </div>
      </form>
      {by && (
        <div className="grid gap-4 md:grid-cols-4">
          <Total label={t("necessity.ZARUR")} value={by.zarur.formatted} tone="text-zarur" />
          <Total label={t("necessity.KERAK")} value={by.kerak.formatted} tone="text-kerak" />
          <Total label={t("necessity.HAVAS")} value={by.havas.formatted} tone="text-havas" />
          <Total label={t("audit.sadaqa")} value={by.sadaqa.formatted} tone="text-accent" />
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
