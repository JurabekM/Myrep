import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type KkGrowthSettingsDto, type KkItemDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const RESULTS = ["OK", "ADJUSTED", "FAULTY"] as const;

/**
 * «Tarozingni to'g'ri tut» (kasbkor/SPEC 8.1, 8.4): oylik tarozi tekshiruvi (ilova o'lchamaydi — odatni
 * eslatadi va qayd etadi) va yillik inventarizatsiya (sanalgan miqdorlar bitta yozuvda).
 */
export function KkMeasureScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const settings = useQuery({ queryKey: keys.kkGrowthSettings(spaceId), queryFn: () => call(commands.kkGrowthSettings(spaceId)) });
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("kk.measure.title")}</h1>
      <p className="text-ink-muted">{t("kk.measure.intro")}</p>
      {settings.data && <Scale spaceId={spaceId} s={settings.data} />}
      <Inventory spaceId={spaceId} />
    </section>
  );
}

function Scale({ spaceId, s }: { spaceId: string; s: KkGrowthSettingsDto }) {
  const { t } = useTranslation();
  const scale = useQuery({ queryKey: keys.kkScale(spaceId), queryFn: () => call(commands.kkScale(spaceId)) });
  const [result, setResult] = useState<(typeof RESULTS)[number]>("OK");
  const [note, setNote] = useState("");
  const check = useMutation({
    mutationFn: () => call(commands.kkScaleCheck(spaceId, { result, checkedOn: null, note: note.trim() || null })),
    onSuccess: () => setNote(""),
  });
  const reminder = useMutation({
    mutationFn: (on: boolean) =>
      call(
        commands.kkSetGrowthSettings(spaceId, {
          reserveMonths: s.reserveMonths,
          maxBadPercent: s.maxBadPercent,
          zakatMonth: s.zakatMonth,
          zakatDay: s.zakatDay,
          goldPrice: s.goldPrice?.plain ?? null,
          nisabGrams: s.nisabGrams,
          stockValuation: s.stockValuation,
          scaleReminder: on,
        }),
      ),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    check.mutate();
  };
  const sc = scale.data;
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.measure.scale")}>
      <h2 className="text-lg font-semibold">{t("kk.measure.scale")}</h2>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={s.scaleReminder} onChange={(e) => reminder.mutate(e.target.checked)} />
        {t("kk.measure.reminder")}
      </label>
      {sc?.due && (
        <p role="note" data-testid="kk-scale-due" className="text-sm text-warn">
          {t("kk.measure.due")}
        </p>
      )}
      <form className="flex flex-col gap-3" aria-label={t("kk.measure.checkTitle")} onSubmit={submit}>
        <fieldset>
          <legend className="label">{t("kk.measure.result")}</legend>
          <div className="flex flex-wrap gap-2">
            {RESULTS.map((r) => (
              <button key={r} type="button" aria-pressed={result === r} className={result === r ? "btn-primary" : "btn-ghost"} onClick={() => setResult(r)}>
                {t(`kk.measure.res.${r}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <label>
          <span className="label">{t("kk.measure.note")}</span>
          <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <ErrorText error={check.error ?? reminder.error} />
        <button className="btn-primary self-start" disabled={check.isPending}>
          {t("kk.measure.checkSave")}
        </button>
      </form>
      {sc && sc.checks.length > 0 && (
        <ul className="flex flex-col gap-1 border-t border-line pt-2 text-sm">
          {sc.checks.slice(0, 6).map((c) => (
            <li key={c.id}>
              {showDate(c.checkedOn)} — {t(`kk.measure.res.${c.result}`)}
              {c.note ? <span className="text-ink-muted"> · {c.note}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Inventory({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const stock = useQuery({ queryKey: keys.kkStock(spaceId), queryFn: () => call(commands.kkStock(spaceId)) });
  const counts = useQuery({ queryKey: keys.kkStockCounts(spaceId), queryFn: () => call(commands.kkStockCounts(spaceId)) });
  const [counted, setCounted] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const save = useMutation({
    mutationFn: (items: KkItemDto[]) =>
      call(commands.kkInventory(spaceId, { countedOn: null, reason, lines: items.map((i) => ({ itemId: i.id, counted: counted[i.id] ?? "" })) })),
    onSuccess: () => {
      setCounted({});
      setReason("");
    },
  });
  const items = stock.data?.items ?? [];
  return (
    <section className="card flex flex-col gap-3" aria-label={t("kk.measure.inventory")}>
      <h2 className="text-lg font-semibold">{t("kk.measure.inventory")}</h2>
      <p className="text-sm text-ink-muted">{t("kk.measure.inventoryHint")}</p>
      {items.length === 0 && <p className="text-sm text-ink-muted">{t("kk.stock.empty")}</p>}
      {items.length > 0 && (
        <form
          className="flex flex-col gap-3"
          aria-label={t("kk.measure.inventoryForm")}
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(items);
          }}
        >
          <table className="w-full text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="py-1 pr-3 font-normal">{t("kk.stock.name")}</th>
                <th className="py-1 pr-3 text-right font-normal">{t("kk.measure.book")}</th>
                <th className="py-1 font-normal">{t("kk.measure.counted")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => {
                const unit = t(`kk.unit.${i.unit}`);
                return (
                  <tr key={i.id} className="border-t border-line">
                    <td className="py-1 pr-3">{i.name}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">
                      {i.qty} {unit}
                    </td>
                    <td className="py-1">
                      <input
                        className="field w-32 tabular-nums"
                        inputMode="decimal"
                        aria-label={t("kk.measure.countedNamed", { name: i.name, unit })}
                        value={counted[i.id] ?? ""}
                        onChange={(e) => setCounted({ ...counted, [i.id]: e.target.value })}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <label>
            <span className="label">{t("kk.measure.reason")}</span>
            <input className="field" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <ErrorText error={save.error} />
          <button className="btn-primary self-start" disabled={save.isPending}>
            {t("kk.measure.inventorySave")}
          </button>
        </form>
      )}
      {counts.data && counts.data.length > 0 && (
        <ul className="flex flex-col gap-1 border-t border-line pt-2 text-sm">
          {counts.data.map((c) => (
            <li key={c.id} data-testid="kk-count-row">
              {t("kk.measure.countLine", {
                date: showDate(c.countedOn),
                counted: c.counted,
                changed: c.changed,
                before: c.valueBefore.formatted,
                after: c.valueAfter.formatted,
              })}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
