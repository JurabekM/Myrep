import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

/** «Kelajagim»: odat (streak) summadan oldin; pul olish — PIN va sabab bilan (friction). */
export function VaultScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const vault = useQuery({ queryKey: keys.vault(spaceId), queryFn: () => call(commands.vault(spaceId)) });
  const [withdrawing, setWithdrawing] = useState(false);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [pin, setPin] = useState("");
  const [initial, setInitial] = useState("");

  const withdraw = useMutation({
    mutationFn: () => call(commands.withdrawFromVault(spaceId, pin, amount, reason)),
    onSuccess: () => {
      setWithdrawing(false);
      setAmount("");
      setReason("");
    },
    onSettled: () => setPin(""),
  });
  const addInitial = useMutation({ mutationFn: () => call(commands.recordInitialBalance(spaceId, initial)), onSuccess: () => setInitial("") });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    withdraw.mutate();
  };

  const v = vault.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("vault.title")}</h1>
      <div className="card">
        <p className="text-sm text-ink-muted">{t("vault.habitFirst")}</p>
        <p className="kpi">{v ? t("home.streak", { count: v.streak.currentWeeks }) : "…"}</p>
        <p className="mt-2 text-sm text-ink-muted">{t("vault.balance")}</p>
        <p className="text-xl font-medium tabular-nums">{v?.balance.formatted ?? "…"}</p>
      </div>

      {v && v.history.length === 0 && (
        <form className="card flex items-end gap-3" onSubmit={(e) => { e.preventDefault(); addInitial.mutate(); }}>
          <label className="flex-1">
            <span className="label">{t("vault.initial")}</span>
            <AmountInput value={initial} onChange={(e) => setInitial(e.target.value)} />
          </label>
          <button className="btn-ghost" disabled={!initial}>{t("common.save")}</button>
        </form>
      )}

      {withdrawing ? (
        <form className="card flex flex-col gap-3" onSubmit={submit}>
          <p className="text-warn">{t("vault.withdrawHint")}</p>
          <label>
            <span className="label">{t("common.amount")}</span>
            <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("vault.reason")}</span>
            <input className="field" value={reason} onChange={(e) => setReason(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("lock.pin")}</span>
            <input className="field tracking-widest" type="password" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} required />
          </label>
          <ErrorText error={withdraw.error} />
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setWithdrawing(false)}>{t("common.cancel")}</button>
            <button className="btn-primary" disabled={withdraw.isPending}>{t("vault.withdraw")}</button>
          </div>
        </form>
      ) : (
        <div>
          <button className="btn-ghost" onClick={() => setWithdrawing(true)}>{t("vault.withdraw")}</button>
        </div>
      )}

      <div className="card">
        <h2 className="mb-3 font-semibold">{t("vault.history")}</h2>
        <ul className="divide-y divide-line">
          {v?.history.map((h) => (
            <li key={h.id} className="flex justify-between py-2 tabular-nums">
              <span className="text-ink-muted">{h.occurredOn}</span>
              <span>{h.amount.formatted}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
