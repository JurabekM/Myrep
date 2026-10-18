import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkShiftDto, type KkShiftInput } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const REASONS = ["UNRECORDED_EXPENSE", "CHANGE_ERROR", "GIVEN_ON_CREDIT", "OWNER_TOOK", "UNKNOWN"] as const;

const EMPTY: KkShiftInput = { opening: null, counted: null, handedOver: null, reason: null, note: null };

/**
 * Sotuvchi smenasi (ADR-0003, `kk_shift_close`): ochilish (oldingi smenada qolgani), o'z naqd tushumi
 * va nasiya to'lovlari → kutilgan; sanalgan → farq; egasiga topshirilgan → keyingi smenaga qolgani.
 */
export function KkShiftScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const draft = useQuery({
    queryKey: keys.kkShiftDraft(spaceId, JSON.stringify(EMPTY)),
    queryFn: () => call(commands.kkShiftDraft(spaceId, EMPTY)),
  });
  const d = draft.error ? undefined : draft.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.shift.title")}</h1>
      <p className="text-ink-muted">{t("kk.shift.intro")}</p>
      <ErrorText error={draft.error} />
      {d?.closed && (
        <p role="status" className="card">
          {t("kk.shift.closedToday")}
        </p>
      )}
      {d && !d.closed && <ShiftForm spaceId={spaceId} base={d} />}
      <KkShiftsTable spaceId={spaceId} title={t("kk.shift.history")} />
    </section>
  );
}

function Line({ label, value, testId, strong }: { label: string; value: string; testId?: string; strong?: boolean }) {
  return (
    <tr className={`border-t border-line ${strong ? "font-semibold" : ""}`}>
      <th scope="row" className="py-1 pr-3 text-left font-normal">
        {strong ? <span className="font-semibold">{label}</span> : label}
      </th>
      <td data-testid={testId} className="py-1 text-right tabular-nums">
        {value}
      </td>
    </tr>
  );
}

function ShiftForm({ spaceId, base }: { spaceId: string; base: KkShiftDto }) {
  const { t } = useTranslation();
  const [opening, setOpening] = useState("");
  const [counted, setCounted] = useState("");
  const [handed, setHanded] = useState("");
  const [reason, setReason] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const input: KkShiftInput = {
    opening: base.openingKnown ? null : opening.trim() || null,
    counted: counted.trim() || null,
    handedOver: handed.trim() || null,
    reason,
    note: note.trim() || null,
  };
  // Har o'zgarishda yadro qayta hisoblaydi (UI hisoblamaydi).
  const preview = useQuery({
    queryKey: keys.kkShiftDraft(spaceId, JSON.stringify({ ...input, reason: null, note: null })),
    queryFn: () => call(commands.kkShiftDraft(spaceId, { ...input, reason: null, note: null })),
  });
  const close = useMutation({ mutationFn: () => call(commands.kkCloseShift(spaceId, input)) });
  const p = preview.error ? base : (preview.data ?? base);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    close.mutate();
  };
  return (
    <form className="card flex flex-col gap-4" aria-label={t("kk.shift.form")} onSubmit={submit}>
      <h2 className="text-lg font-semibold">{t("kk.shift.day", { date: showDate(p.day) })}</h2>
      {!base.openingKnown && (
        <label className="max-w-sm">
          <span className="label">{t("kk.shift.openingInput")}</span>
          <AmountInput value={opening} onChange={(e) => setOpening(e.target.value)} aria-describedby="kk-shift-opening-hint" />
        </label>
      )}
      {!base.openingKnown && (
        <p id="kk-shift-opening-hint" className="-mt-2 text-xs text-ink-muted">
          {t("kk.shift.openingHint")}
        </p>
      )}
      <table className="w-full text-sm">
        <tbody>
          <Line label={t("kk.shift.opening")} value={p.opening.formatted} />
          <Line label={t("kk.shift.cashSales")} value={`+ ${p.cashSales.formatted}`} />
          <Line label={t("kk.shift.creditPayments")} value={`+ ${p.creditPayments.formatted}`} />
          <Line label={t("kk.shift.expected")} value={p.expected.formatted} testId="kk-shift-expected" strong />
        </tbody>
      </table>
      <p className="text-xs text-ink-muted">{t("kk.shift.cardInfo", { amount: p.cardIn.formatted })}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className="label">{t("kk.shift.counted")}</span>
          <AmountInput value={counted} onChange={(e) => setCounted(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("kk.shift.handedOver")}</span>
          <AmountInput value={handed} onChange={(e) => setHanded(e.target.value)} />
        </label>
      </div>
      {p.difference && (
        <div className="flex flex-col gap-2">
          <p role="status" data-testid="kk-shift-difference" className={p.status === "EXACT" ? "text-lg" : "text-lg text-warn"}>
            {t(`kk.cash.status.${p.status}`, { amount: p.difference.formatted })}
          </p>
          {p.left && <p className="text-sm">{t("kk.shift.left", { amount: p.left.formatted })}</p>}
          {p.suggestSearch && (
            <p role="note" className="text-sm text-warn">
              {t("kk.cash.suggestSearch")}
            </p>
          )}
        </div>
      )}
      {p.status && p.status !== "EXACT" && (
        <fieldset>
          <legend className="label">{t("kk.cash.reason")}</legend>
          <div className="flex flex-col gap-1">
            {REASONS.map((r) => (
              <label key={r} className="flex items-center gap-2">
                <input type="radio" name="kk-shift-reason" checked={reason === r} onChange={() => setReason(r)} />
                {t(`kk.cash.reasons.${r}`)}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <label>
        <span className="label">{t("kk.note")}</span>
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <p className="text-sm text-ink-muted">{t("kk.shift.finalWarning")}</p>
      <ErrorText error={close.error} />
      <button className="btn-primary self-start" disabled={close.isPending}>
        {t("kk.shift.close")}
      </button>
    </form>
  );
}

/** Smenalar: egasida — barcha sotuvchilarniki («Kassa» bo'limida), sotuvchida — o'ziniki. */
export function KkShiftsTable({ spaceId, title, hideEmpty }: { spaceId: string; title: string; hideEmpty?: boolean }) {
  const { t } = useTranslation();
  const shifts = useQuery({ queryKey: keys.kkShifts(spaceId), queryFn: () => call(commands.kkShifts(spaceId)) });
  const rows = shifts.error ? [] : (shifts.data ?? []);
  if (hideEmpty && rows.length === 0) return null;
  return (
    <section className="card flex flex-col gap-2" aria-label={title}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <ErrorText error={shifts.error} />
      {rows.length === 0 && !shifts.error && <p className="text-sm text-ink-muted">{t("kk.shift.none")}</p>}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.col.date")}</th>
                <th className="py-1 pr-3 font-normal">{t("kk.shift.device")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.shift.expected")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.cash.countedShort")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.cash.difference")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.shift.handedShort")}</th>
                <th className="py-1 font-normal">{t("kk.cash.reason")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id} data-testid="kk-shift-row" className="border-t border-line">
                  <td className="py-1 pr-3">{showDate(s.day)}</td>
                  <td className="py-1 pr-3">{s.deviceName}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{s.expected.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{s.counted.formatted}</td>
                  <td className={`py-1 pr-3 text-right tabular-nums ${s.status === "EXACT" ? "" : "text-warn"}`}>{s.difference.formatted}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{s.handedOver.formatted}</td>
                  <td className="py-1">
                    {s.reason ? t(`kk.cash.reasons.${s.reason}`) : "—"}
                    {s.note ? <span className="text-ink-muted"> · {s.note}</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
