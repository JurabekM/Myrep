import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useDialog } from "../../lib/useDialog";

export type EntryMode = "SALE" | "EXPENSE" | "OWNER_DRAW" | "OWNER_CONTRIBUTION" | "TRANSFER" | "OPENING";
type Wallet = "CASH" | "CARD";

/**
 * Kasb-kor yozuvi (kasbkor/SPEC 2): tushum, chiqim, «egasi oldi», kapital kiritish, hamyonlar
 * orasida o'tkazma yoki boshlang'ich qoldiq. Summa matn ko'rinishida yadroga beriladi.
 */
export function KkEntryDialog({ spaceId, mode, onClose }: { spaceId: string; mode: EntryMode; onClose: () => void }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onClose);
  const categories = useQuery({ queryKey: keys.categories(spaceId), queryFn: () => call(commands.categories(spaceId)), enabled: mode === "EXPENSE" });
  const [amount, setAmount] = useState("");
  const [wallet, setWallet] = useState<Wallet>(mode === "TRANSFER" ? "CARD" : "CASH");
  const [toWallet, setToWallet] = useState<Wallet>("CASH");
  const [categoryId, setCategoryId] = useState("");
  const [occurredOn, setOccurredOn] = useState("");
  const [note, setNote] = useState("");

  const save = useMutation({
    mutationFn: async () => {
      const date = occurredOn || null;
      const text = note.trim() || null;
      if (mode === "SALE") return void (await call(commands.kkRecordSale(spaceId, { amount, channel: wallet, occurredOn: date, note: text })));
      if (mode === "EXPENSE") {
        const id = categoryId || categories.data?.[0]?.id || "";
        return void (await call(
          commands.recordExpense(spaceId, { amount, categoryId: id, channel: wallet, memberId: null, occurredOn: date, necessity: null, obligationId: null, isGift: false, isOstentation: false, fundedByDebt: false, note: text }),
        ));
      }
      await call(commands.kkRecordMove(spaceId, { kind: mode, wallet, toWallet: mode === "TRANSFER" ? toWallet : null, amount, occurredOn: date, note: text }));
    },
    onSuccess: onClose,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  const walletPicker = (label: string, value: Wallet, onChange: (w: Wallet) => void) => (
    <fieldset>
      <legend className="label">{label}</legend>
      <div className="flex gap-2">
        {(["CASH", "CARD"] as const).map((w) => (
          <button key={w} type="button" aria-pressed={value === w} className={value === w ? "btn-primary" : "btn-ghost"} onClick={() => onChange(w)}>
            {t(`kk.wallet.${w}`)}
          </button>
        ))}
      </div>
    </fieldset>
  );

  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="kk-entry-title" className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4">
      <div className="card w-full max-w-md">
        <h2 id="kk-entry-title" className="mb-1 text-xl font-semibold">
          {t(`kk.action.${mode}`)}
        </h2>
        <p className="mb-4 text-sm text-ink-muted">{t(`kk.hint.${mode}`)}</p>
        <form className="flex flex-col gap-4" onSubmit={submit}>
          <label>
            <span className="label">{t("common.amount")}</span>
            <AmountInput autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          {mode === "EXPENSE" && (
            <label>
              <span className="label">{t("kk.category")}</span>
              <select className="field" value={categoryId || categories.data?.[0]?.id || ""} onChange={(e) => setCategoryId(e.target.value)}>
                {categories.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.customName ?? t(c.nameKey)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {walletPicker(mode === "TRANSFER" ? t("kk.fromWallet") : t("kk.walletLabel"), wallet, setWallet)}
          {mode === "TRANSFER" && walletPicker(t("kk.toWallet"), toWallet, setToWallet)}
          <label>
            <span className="label">{t("kk.date")}</span>
            <input type="date" className="field" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} />
          </label>
          <label>
            <span className="label">{mode === "SALE" ? t("kk.saleNote") : t("kk.note")}</span>
            <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <ErrorText error={save.error} />
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" disabled={save.isPending}>
              {t("common.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
