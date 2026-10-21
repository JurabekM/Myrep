import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { type BorrowCheckInput, commands, type IssuedReceiptDto, type ScheduleLineInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { BorrowCheckFields } from "../../components/BorrowCheckFields";
import { ErrorText } from "../../components/ErrorText";
import { ScheduleEditor } from "../../components/ScheduleEditor";
import { call } from "../../lib/api";

type Direction = "BORROWED" | "LENT";

/**
 * Qarz tilxati (uy/SPEC 2D.5) = `Agreement(type = LOAN)`: foizsiz, toʻlov rejasi majburiy, guvohlar
 * bilan. Saqlanganda kelishuv, jurnal va qarz yozuvi yaratiladi; PDF tizimning «Saqlash» oynasi
 * orqali yoziladi. Tekshiruv va formatlash yadroda.
 */
export function ReceiptScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [direction, setDirection] = useState<Direction>("BORROWED");
  const [creditorType, setCreditorType] = useState("FRIEND");
  const [lender, setLender] = useState("");
  const [borrower, setBorrower] = useState("");
  const [amount, setAmount] = useState("");
  const [place, setPlace] = useState("");
  const [schedule, setSchedule] = useState<ScheduleLineInput[]>([{ date: "", amount: "" }]);
  const [witnesses, setWitnesses] = useState("");
  const [note, setNote] = useState("");
  const [check, setCheck] = useState<BorrowCheckInput>({ need: "NECESSITY", alternatives: [] });
  const [issued, setIssued] = useState<IssuedReceiptDto | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      const borrowed = direction === "BORROWED";
      const receipt = await call(
        commands.issueLoanReceipt(spaceId, {
          direction,
          creditorType: borrowed ? creditorType : null,
          reason: null,
          receipt: {
            lender,
            borrower,
            amount,
            currency: "UZS",
            issuedOn: null,
            place,
            schedule,
            witnesses: witnesses.split(","),
            note: note.trim() === "" ? null : note,
          },
          isNew: borrowed,
          borrowCheck: borrowed ? check : null,
        }),
      );
      // Tilxat saqlandi; PDF oynasi bekor qilinsa ham keyin «Qarzlar» ekranidan chop etiladi.
      await call(commands.exportAgreementReceipt(spaceId, receipt.agreementId));
      return receipt;
    },
    onSuccess: setIssued,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setIssued(null);
    save.mutate();
  };

  if (issued) {
    return (
      <section className="flex max-w-3xl flex-col gap-5">
        <h1 className="text-2xl font-semibold">{t("receipt.title")}</h1>
        <div role="status" className="card flex flex-col gap-3">
          <p>{t("receipt.saved")}</p>
          <p className="text-sm text-ink-muted">{t("receipt.code")}</p>
          <code className="text-xl tracking-wider text-accent-text">{issued.shortCode}</code>
          <div>
            <button className="btn-ghost" onClick={() => setIssued(null)}>{t("receipt.another")}</button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("receipt.title")}</h1>
      <p className="text-sm text-ink-muted">{t("receipt.intro")}</p>
      <form className="card grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <div className="flex flex-wrap gap-4 md:col-span-2" role="radiogroup" aria-label={t("receipt.direction")}>
          {(["BORROWED", "LENT"] as const).map((d) => (
            <label key={d} className="flex items-center gap-2">
              <input type="radio" name="direction" checked={direction === d} onChange={() => setDirection(d)} />
              {t(`receipt.direction.${d}`)}
            </label>
          ))}
        </div>
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
        <ScheduleEditor value={schedule} onChange={setSchedule} />
        <label className="md:col-span-2">
          <span className="label">{t("receipt.witnesses")}</span>
          <input className="field" value={witnesses} onChange={(e) => setWitnesses(e.target.value)} />
        </label>
        <label className="md:col-span-2">
          <span className="label">{t("common.note")}</span>
          <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        {direction === "BORROWED" && (
          <>
            <label>
              <span className="label">{t("debts.creditorType")}</span>
              <select className="field" value={creditorType} onChange={(e) => setCreditorType(e.target.value)}>
                {(["RELATIVE", "FRIEND", "OTHER"] as const).map((c) => <option key={c} value={c}>{t(`debts.creditor.${c}`)}</option>)}
              </select>
            </label>
            <BorrowCheckFields value={check} onChange={setCheck} />
          </>
        )}
        <div className="md:col-span-2"><ErrorText error={save.error} /></div>
        <div>
          <button className="btn-primary" disabled={save.isPending}>{t("receipt.save")}</button>
        </div>
      </form>
    </section>
  );
}
