import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkAgreementStateDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";

/** Shablon yurist ko'rigidan o'tmagan bo'lsa — ogohlantirish (BARAKA_OILASI 9, `reviewStatus`). */
export function TemplateReviewNote({ status }: { status: string | undefined }) {
  const { t } = useTranslation();
  if (status !== "PENDING") return null;
  return (
    <p role="note" className="card border-warn py-3 text-sm text-warn">
      {t("kk.agr.reviewPending")}
    </p>
  );
}

/** Kelishuv holati: qoralama / imzolangan (versiya) / tugagan; imzolanmagan o'zgarishlar va yetishmayotganlar. */
export function AgreementStatus({ state, testId }: { state: KkAgreementStateDto; testId: string }) {
  const { t } = useTranslation();
  const label =
    state.status === "SIGNED"
      ? t("kk.agr.status.SIGNED", { n: state.signedVersions, date: showDate(state.signedOn ?? "") })
      : state.status === "ENDED"
        ? t("kk.agr.status.ENDED", { date: showDate(state.endedOn ?? "") })
        : t("kk.agr.status.DRAFT");
  return (
    <div className="flex flex-col gap-1 text-sm">
      <p data-testid={testId} className={state.status === "SIGNED" ? "text-accent-text" : "text-ink-muted"}>
        {label}
      </p>
      {state.status !== "ENDED" && state.signedVersions > 0 && state.unsignedChanges && (
        <p role="note" className="text-warn">
          {t("kk.agr.unsignedChanges")}
        </p>
      )}
      {state.missing.length > 0 && (
        <p role="note" className="text-warn">
          {t("kk.agr.missing", { fields: state.missing.map((m) => t(`kk.agr.field.${m}`)).join(", ") })}
        </p>
      )}
    </div>
  );
}

/** Imzolash: qog'oz nusxa imzolangan sana; keyingi versiyada — yangi shartlar qachondan amal qiladi. */
export function SignForm({ spaceId, id, name, state, onDone }: { spaceId: string; id: string; name: string; state: KkAgreementStateDto; onDone: () => void }) {
  const { t } = useTranslation();
  const [signedOn, setSignedOn] = useState("");
  const [from, setFrom] = useState("");
  const save = useMutation({
    mutationFn: () => call(commands.kkSignAgreement(spaceId, id, { signedOn: signedOn || null, effectiveFrom: from || null })),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-col gap-3 rounded-md border border-line p-3" aria-label={t("kk.agr.signTitle", { name })} onSubmit={submit}>
      <p className="text-sm text-ink-muted">{t("kk.agr.signHint")}</p>
      <div className="flex flex-wrap items-end gap-3">
        <label>
          <span className="label">{t("kk.agr.signedOn")}</span>
          <input type="date" className="field" value={signedOn} onChange={(e) => setSignedOn(e.target.value)} />
        </label>
        {state.signedVersions > 0 && (
          <label>
            <span className="label">{t("kk.agr.effectiveFrom")}</span>
            <input type="date" className="field" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
        )}
      </div>
      <ErrorText error={save.error} />
      <button className="btn-primary self-start" disabled={save.isPending}>
        {t("kk.agr.signSave")}
      </button>
    </form>
  );
}

/** Kelishuvni tugatish (ajralish yoki ta'minotni to'xtatish): yozuvlar saqlanadi. */
export function EndForm({ spaceId, id, name, onDone }: { spaceId: string; id: string; name: string; onDone: () => void }) {
  const { t } = useTranslation();
  const [on, setOn] = useState("");
  const save = useMutation({ mutationFn: () => call(commands.kkEndAgreement(spaceId, id, on || null)), onSuccess: onDone });
  return (
    <form
      className="flex flex-wrap items-end gap-3 rounded-md border border-line p-3"
      aria-label={t("kk.agr.endTitle", { name })}
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <label>
        <span className="label">{t("kk.agr.endedOn")}</span>
        <input type="date" className="field" value={on} onChange={(e) => setOn(e.target.value)} />
      </label>
      <button className="btn-primary">{t("kk.agr.endSave")}</button>
      <div className="w-full">
        <ErrorText error={save.error} />
      </div>
    </form>
  );
}

/** PDF va o'chirish tugmalari (o'chirish — faqat imzolanmagan kelishuvda). */
export function AgreementFileActions({ spaceId, id, name, state }: { spaceId: string; id: string; name: string; state: KkAgreementStateDto }) {
  const { t } = useTranslation();
  const pdf = useMutation({ mutationFn: () => call(commands.exportKkAgreement(spaceId, id)) });
  const del = useMutation({ mutationFn: () => call(commands.kkDeleteAgreement(spaceId, id)) });
  return (
    <>
      <button className="btn-ghost" aria-label={t("kk.agr.pdfNamed", { name })} onClick={() => pdf.mutate()}>
        {t("kk.agr.pdf")}
      </button>
      {state.signedVersions === 0 && (
        <button className="btn-ghost" aria-label={t("kk.agr.deleteNamed", { name })} onClick={() => del.mutate()}>
          {t("kk.agr.delete")}
        </button>
      )}
      {pdf.data === true && (
        <span role="status" className="self-center text-sm text-ink-muted">
          {t("kk.agr.pdfSaved")}
        </span>
      )}
      <ErrorText error={pdf.error ?? del.error} />
    </>
  );
}

/** Telefon va uni saqlashga rozilik (OQ-Y3): rozilik belgilanmasa, yadro telefonni qabul qilmaydi. */
export function PhoneFields({ phone, consent, onPhone, onConsent }: { phone: string; consent: boolean; onPhone: (v: string) => void; onConsent: (v: boolean) => void }) {
  const { t } = useTranslation();
  return (
    <>
      <label>
        <span className="label">{t("kk.agr.phone")}</span>
        <input className="field" inputMode="tel" value={phone} onChange={(e) => onPhone(e.target.value)} />
      </label>
      <label className="flex items-center gap-2 self-end pb-2 text-sm">
        <input type="checkbox" checked={consent} onChange={(e) => onConsent(e.target.checked)} />
        {t("kk.agr.phoneConsent")}
      </label>
    </>
  );
}
