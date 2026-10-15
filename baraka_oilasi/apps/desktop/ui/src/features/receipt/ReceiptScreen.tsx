import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type ScheduleLineInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";

/**
 * Qarz tilxati (uy/SPEC 2D.5): foizsiz, toʻlov rejasi majburiy, guvohlar bilan.
 * Tekshiruv va formatlash yadroda; PDF tizimning «Saqlash» oynasi orqali yoziladi.
 */
export function ReceiptScreen() {
  const { t } = useTranslation();
  const [lender, setLender] = useState("");
  const [borrower, setBorrower] = useState("");
  const [amount, setAmount] = useState("");
  const [place, setPlace] = useState("");
  const [schedule, setSchedule] = useState<ScheduleLineInput[]>([{ date: "", amount: "" }]);
  const [witnesses, setWitnesses] = useState("");
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);

  const save = useMutation({
    mutationFn: () =>
      call(
        commands.exportLoanReceipt({
          lender,
          borrower,
          amount,
          currency: "UZS",
          issuedOn: null,
          place,
          schedule,
          witnesses: witnesses.split(","),
          note: note.trim() === "" ? null : note,
        }),
      ),
    onSuccess: setSaved,
  });

  const setLine = (i: number, patch: Partial<ScheduleLineInput>) =>
    setSchedule((rows) => rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setSaved(false);
    save.mutate();
  };

  return (
    <section className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("receipt.title")}</h1>
      <p className="text-sm text-ink-muted">{t("receipt.intro")}</p>
      <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label>
          <span className="label">{t("receipt.lender")}</span>
          <input className="field" value={lender} onChange={(e) => setLender(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("receipt.borrower")}</span>
          <input className="field" value={borrower} onChange={(e) => setBorrower(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("receipt.amount")}</span>
          <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("receipt.place")}</span>
          <input className="field" value={place} onChange={(e) => setPlace(e.target.value)} required />
        </label>

        <fieldset className="md:col-span-2">
          <legend className="label">{t("receipt.schedule")}</legend>
          <div className="flex flex-col gap-2">
            {schedule.map((row, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  aria-label={`${t("receipt.lineDate")} ${i + 1}`}
                  inputMode="numeric"
                  placeholder="15.11.2026"
                  className="field max-w-40 tabular-nums"
                  value={row.date}
                  onChange={(e) => setLine(i, { date: e.target.value })}
                  required
                />
                <AmountInput aria-label={`${t("common.amount")} ${i + 1}`} value={row.amount} onChange={(e) => setLine(i, { amount: e.target.value })} required />
                <button type="button" className="btn-ghost" disabled={schedule.length === 1} onClick={() => setSchedule((rows) => rows.filter((_, j) => j !== i))}>
                  {t("receipt.removeLine")}
                </button>
              </div>
            ))}
          </div>
          <button type="button" className="btn-ghost mt-2" onClick={() => setSchedule((rows) => [...rows, { date: "", amount: "" }])}>
            {t("receipt.addLine")}
          </button>
        </fieldset>

        <label className="md:col-span-2">
          <span className="label">{t("receipt.witnesses")}</span>
          <input className="field" value={witnesses} onChange={(e) => setWitnesses(e.target.value)} />
        </label>
        <label className="md:col-span-2">
          <span className="label">{t("common.note")}</span>
          <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <div className="md:col-span-2"><ErrorText error={save.error} /></div>
        {saved && <p role="status" className="text-sm text-accent-text md:col-span-2">{t("receipt.saved")}</p>}
        <div>
          <button className="btn-primary" disabled={save.isPending}>{t("receipt.save")}</button>
        </div>
      </form>
    </section>
  );
}
