import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  type AttachmentInput,
  type ClosePeriodInput,
  commands,
  type VentureEntryDto,
  type VentureLedgerDto,
  type VenturePeriodDto,
} from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call, CoreError } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";

const KINDS = ["INCOME", "EXPENSE", "FORCE_MAJEURE"] as const;
const CATEGORIES: Record<string, string[]> = {
  INCOME: ["ORDER", "OTHER"],
  EXPENSE: ["MATERIAL", "WAGE", "RENT", "EQUIPMENT", "TRANSPORT", "OTHER"],
};
/** Yadrodagi chegaralar bilan bir xil (`MAX_ATTACHMENTS`, `MAX_ATTACHMENT_BYTES`). */
const MAX_FILES = 5;
const MAX_BYTES = 5 * 1024 * 1024;

const pad = (n: number) => String(n).padStart(2, "0");
/** Sana maydoni uchun boshlang'ich qiymat (faqat ko'rsatish, hisob emas). */
const todayText = () => {
  const d = new Date();
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
};
const optional = (v: string) => (v.trim() === "" ? null : v);

async function readFiles(list: FileList | null): Promise<AttachmentInput[]> {
  const files = Array.from(list ?? []);
  if (files.length > MAX_FILES) throw new CoreError({ code: "TOO_MANY_ATTACHMENTS", field: "attachments" });
  if (files.some((f) => f.size > MAX_BYTES)) throw new CoreError({ code: "ATTACHMENT_TOO_LARGE", field: "attachments" });
  return Promise.all(files.map(async (f) => ({ fileName: f.name, bytes: Array.from(new Uint8Array(await f.arrayBuffer())) })));
}

/**
 * Sheriklik kassa daftari (uy/SPEC 2E.3): biznes puli uy pulidan alohida. Har yozuv kelishuv
 * jurnaliga ham tushadi; yopilgan davr o'zgarmaydi — xato faqat tuzatuvchi yozuv bilan.
 */
export function LedgerView({ spaceId, partnershipId }: { spaceId: string; partnershipId: string }) {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: keys.ledger(spaceId, partnershipId), queryFn: () => call(commands.ventureLedger(spaceId, partnershipId)) });
  const [correcting, setCorrecting] = useState<VentureEntryDto | null>(null);
  const [viewing, setViewing] = useState<{ url: string; name: string } | null>(null);
  const l = q.data;
  if (!l) return <ErrorText error={q.error} />;
  const open = async (attachmentId: string) => {
    const a = await call(commands.ventureAttachment(spaceId, partnershipId, attachmentId));
    // CSP faqat `data:` rasmlarga ruxsat beradi (`blob:` yo'q) — base64 ga o'tkazamiz.
    let bin = "";
    for (let i = 0; i < a.bytes.length; i += 0x8000) bin += String.fromCharCode(...a.bytes.slice(i, i + 0x8000));
    setViewing({ url: `data:${a.mime};base64,${btoa(bin)}`, name: a.fileName });
  };
  return (
    <div className="flex flex-col gap-4">
      <Balances l={l} />
      {l.writable ? (
        <EntryForm spaceId={spaceId} l={l} correcting={correcting} onDone={() => setCorrecting(null)} />
      ) : (
        <p className="rounded border border-line px-3 py-2 text-sm text-ink-muted">{t(`venture.readOnly.${l.readOnlyReason ?? "NOT_ACTIVE"}`, { name: l.keeperName ?? "" })}</p>
      )}
      <OpenPeriod spaceId={spaceId} l={l} />
      <Entries l={l} onCorrect={l.writable ? setCorrecting : null} onOpen={(id) => void open(id)} />
      {l.periods.map((p) => (
        <ClosedPeriod key={p.id} spaceId={spaceId} l={l} p={p} />
      ))}
      {viewing && (
        <div role="dialog" aria-modal="true" aria-label={viewing.name} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4" onClick={() => setViewing(null)}>
          <div className="card flex max-h-full max-w-3xl flex-col gap-2">
            <p className="text-sm">{viewing.name}</p>
            <img src={viewing.url} alt={viewing.name} className="max-h-[70vh] object-contain" />
            <button className="btn-ghost self-start" onClick={() => setViewing(null)}>
              {t("common.close")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Balances({ l }: { l: VentureLedgerDto }) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {l.balances.map((b) => (
        <div key={b.partyId} className="card flex flex-col gap-1">
          <p className="text-sm text-ink-muted">
            {b.name} · {t(`partnership.role.${b.role}`)}
            {b.isMe ? ` · ${t("venture.we")}` : ""}
          </p>
          <p className="text-xl font-semibold tabular-nums">{b.capital.formatted}</p>
          <p className="text-xs text-ink-muted">{t("venture.capital")}</p>
          {b.carriedLoss.minor !== "0" && <p className="text-sm text-warn">{t("venture.carriedLoss", { amount: b.carriedLoss.formatted })}</p>}
        </div>
      ))}
      {l.buyout && (
        <div className="card flex flex-col gap-1 md:col-span-2">
          <p className="text-sm">{t("venture.buyoutProgress", { buyer: l.buyout.buyerName, seller: l.buyout.sellerName, paid: l.buyout.paid, total: l.buyout.total })}</p>
          {l.buyout.nextNo != null && (
            <p className="text-sm text-ink-muted">
              {t("venture.buyoutNext", { n: l.buyout.nextNo, date: showDate(l.buyout.nextDate ?? ""), amount: l.buyout.nextPayment?.formatted ?? "" })}
            </p>
          )}
          {l.buyout.overdue.length > 0 && <p className="text-sm text-warn">{t("venture.buyoutOverdue", { list: l.buyout.overdue.join(", ") })}</p>}
        </div>
      )}
      <p className={`text-xs md:col-span-2 ${l.chainOk ? "text-ink-muted" : "text-danger"}`}>
        {t(l.chainOk ? "venture.chainOk" : "venture.chainBroken", { code: l.chainCode })}
      </p>
    </div>
  );
}

function EntryForm({ spaceId, l, correcting, onDone }: { spaceId: string; l: VentureLedgerDto; correcting: VentureEntryDto | null; onDone: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [kind, setKind] = useState<string>("INCOME");
  const [f, setF] = useState({ category: "ORDER", amount: "", date: todayText(), note: "" });
  const [files, setFiles] = useState<FileList | null>(null);
  const [formKey, setFormKey] = useState(0);
  const add = useMutation({
    mutationFn: async () =>
      call(
        commands.addVentureEntry(spaceId, l.partnershipId, {
          kind: correcting ? "CORRECTION" : kind,
          category: correcting || kind === "FORCE_MAJEURE" ? null : f.category,
          amount: f.amount,
          occurredOn: f.date,
          note: optional(f.note),
          correctsEntryId: correcting?.id ?? null,
          attachments: await readFiles(files),
        }),
      ),
    onSuccess: (dto) => {
      qc.setQueryData(keys.ledger(spaceId, l.partnershipId), dto);
      setF({ ...f, amount: "", note: "" });
      setFiles(null);
      setFormKey((k) => k + 1);
      onDone();
    },
  });
  const reset = add.reset;
  useEffect(() => reset(), [correcting, reset]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    add.mutate();
  };
  const pickKind = (k: string) => {
    setKind(k);
    setF({ ...f, category: CATEGORIES[k]?.[0] ?? "OTHER" });
  };
  return (
    <form className="card flex flex-col gap-3" onSubmit={submit} aria-label={t("venture.addEntry")}>
      <h2 className="text-lg font-semibold">{correcting ? t("venture.correctTitle") : t("venture.addEntry")}</h2>
      {correcting ? (
        <p className="text-sm">
          {t("venture.correctHint", { date: showDate(correcting.occurredOn), kind: t(`venture.kind.${correcting.kind}`), amount: correcting.amount.formatted })}
        </p>
      ) : (
        <div className="flex flex-wrap gap-4 text-sm">
          {KINDS.map((k) => (
            <label key={k} className="flex items-center gap-2">
              <input type="radio" name="ventureKind" checked={kind === k} onChange={() => pickKind(k)} />
              {t(`venture.kind.${k}`)}
            </label>
          ))}
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {!correcting && CATEGORIES[kind] && (
          <label>
            <span className="label">{t("venture.category")}</span>
            <select className="field" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
              {CATEGORIES[kind].map((c) => (
                <option key={c} value={c}>
                  {t(`venture.cat.${c}`)}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          <span className="label">{correcting ? t("venture.correctAmount") : t("common.amount")}</span>
          <AmountInput value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} required />
        </label>
        <label>
          <span className="label">{t("venture.date")}</span>
          <input className="field tabular-nums" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} required />
        </label>
        <label className="sm:col-span-2">
          <span className="label">{t(correcting || kind === "FORCE_MAJEURE" ? "venture.noteRequired" : "common.note")}</span>
          <input className="field" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
        </label>
        <div className="sm:col-span-2">
          <span className="label">{t(kind === "FORCE_MAJEURE" ? "venture.evidence" : "venture.receipt")}</span>
          <label className="btn-ghost inline-flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm">
            📎 {t("venture.pickFiles")}
            <input key={formKey} type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf" className="sr-only" onChange={(e: ChangeEvent<HTMLInputElement>) => setFiles(e.target.files)} />
          </label>
          <span className="ml-3 text-sm text-ink-muted">{files && files.length > 0 ? Array.from(files, (f) => f.name).join(", ") : t("venture.noFiles")}</span>
        </div>
      </div>
      {kind === "FORCE_MAJEURE" && !correcting && <p className="text-sm text-ink-muted">{t("venture.forceMajeureHint")}</p>}
      <ErrorText error={add.error} />
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={add.isPending}>
          {t("venture.save")}
        </button>
        {correcting && (
          <button type="button" className="btn-ghost" onClick={onDone}>
            {t("common.cancel")}
          </button>
        )}
      </div>
    </form>
  );
}

function OpenPeriod({ spaceId, l }: { spaceId: string; l: VentureLedgerDto }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [end, setEnd] = useState(todayText());
  const [channel, setChannel] = useState("CASH");
  const [neg, setNeg] = useState<{ partyId: string; note: string } | null>(null);
  const [prices, setPrices] = useState<Record<number, string>>({});
  const input = (): ClosePeriodInput => ({
    endOn: end,
    channel,
    negligence: neg,
    buyoutPrices: Object.entries(prices)
      .filter(([, v]) => v.trim() !== "")
      .map(([no, price]) => ({ no: Number(no), price })),
  });
  const preview = useMutation({ mutationFn: () => call(commands.venturePeriodPreview(spaceId, l.partnershipId, input())) });
  const close = useMutation({
    mutationFn: () => call(commands.closeVenturePeriod(spaceId, l.partnershipId, input())),
    onSuccess: (dto) => {
      qc.setQueryData(keys.ledger(spaceId, l.partnershipId), dto);
      preview.reset();
      setNeg(null);
      setPrices({});
    },
  });
  const o = l.open;
  const workers = l.balances.filter((b) => b.role === "WORKER");
  const pv = preview.data;
  return (
    <div className="card flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{t("venture.openPeriod", { n: o.no, from: showDate(o.from) })}</h2>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <Total label={t("venture.total.income")} value={o.income.formatted} />
        <Total label={t("venture.total.expense")} value={o.expense.formatted} />
        {o.forceMajeure.minor !== "0" && <Total label={t("venture.total.forceMajeure")} value={o.forceMajeure.formatted} />}
        {o.corrections.minor !== "0" && <Total label={t("venture.total.corrections")} value={o.corrections.formatted} />}
        <Total label={t("venture.total.result")} value={o.result.formatted} strong />
      </dl>
      {l.writable && o.entries > 0 && (
        <div className="flex flex-col gap-3 border-t border-line pt-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              <span className="label">{t("venture.endOn")}</span>
              <input className="field tabular-nums" value={end} onChange={(e) => setEnd(e.target.value)} />
            </label>
            <label>
              <span className="label">{t("venture.channel")}</span>
              <select className="field" value={channel} onChange={(e) => setChannel(e.target.value)}>
                <option value="CASH">{t("venture.channelCash")}</option>
                <option value="CARD">{t("venture.channelCard")}</option>
              </select>
            </label>
          </div>
          {l.kind === "MUDARABA" && workers.length > 0 && (
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={neg !== null} onChange={(e) => setNeg(e.target.checked ? { partyId: workers[0]?.partyId ?? "", note: "" } : null)} />
                {t("venture.negligence")}
              </label>
              {neg && (
                <input className="field" aria-label={t("venture.negligenceNote")} placeholder={t("venture.negligenceNote")} value={neg.note} onChange={(e) => setNeg({ ...neg, note: e.target.value })} />
              )}
            </div>
          )}
          {pv?.buyout && [...pv.buyout.paid, ...pv.buyout.unpaid].length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-ink-muted">{t("venture.priceHint")}</p>
              <div className="grid gap-2 sm:grid-cols-3">
                {[...pv.buyout.paid, ...pv.buyout.unpaid].map((n) => (
                  <label key={n}>
                    <span className="label">{t("venture.priceOf", { n })}</span>
                    <AmountInput value={prices[n] ?? ""} placeholder={t("venture.pricePlaceholder")} onChange={(e) => setPrices({ ...prices, [n]: e.target.value })} />
                  </label>
                ))}
              </div>
            </div>
          )}
          <ErrorText error={preview.error ?? close.error} />
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost" disabled={preview.isPending} onClick={() => preview.mutate()}>
              {t("venture.preview")}
            </button>
            {pv && (
              <button className="btn-primary" disabled={close.isPending} onClick={() => close.mutate()}>
                {t("venture.closePeriod")}
              </button>
            )}
          </div>
          {pv && <Distribution p={pv} />}
          {pv && <p className="text-sm text-ink-muted">{t("venture.closeWarning")}</p>}
        </div>
      )}
    </div>
  );
}

function Total({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <dt className="text-ink-muted">{label}</dt>
      <dd className={`tabular-nums ${strong ? "text-lg font-semibold text-accent" : ""}`}>{value}</dd>
    </div>
  );
}

/** Taqsimot jadvali — barcha summalar yadrodan (UI hisoblamaydi). */
function Distribution({ p }: { p: VenturePeriodDto }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2">
      {p.recovered.minor !== "0" && <p className="text-sm">{t("venture.recoveredNote", { amount: p.recovered.formatted })}</p>}
      <table className="w-full text-sm tabular-nums">
        <thead className="text-left text-ink-muted">
          <tr>
            <th className="py-1">{t("venture.col.party")}</th>
            <th className="text-right">{t("venture.col.share")}</th>
            <th className="text-right">{t("venture.col.recovered")}</th>
            <th className="text-right">{t("venture.col.payout")}</th>
            <th className="text-right">{t("venture.col.capital")}</th>
          </tr>
        </thead>
        <tbody>
          {p.parties.map((x) => (
            <tr key={x.partyId} className="border-t border-line">
              <td className="py-1">
                {x.name}
                {x.isMe ? ` (${t("venture.we")})` : ""}
              </td>
              <td className={`text-right ${x.share.minor.startsWith("-") ? "text-danger" : ""}`}>{x.share.formatted}</td>
              <td className="text-right">{x.recovered.formatted}</td>
              <td className="text-right font-semibold">{x.payout.formatted}</td>
              <td className="text-right">{x.capitalAfter.formatted}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.parties.some((x) => x.liability.minor !== "0") && (
        <p className="text-sm text-warn">
          {t("venture.liability", { name: p.negligentParty ?? "", amount: p.parties.find((x) => x.liability.minor !== "0")?.liability.formatted ?? "" })}
        </p>
      )}
      {p.buyout && (
        <p className="text-sm">
          {p.buyout.paid.length > 0 ? t("venture.buyoutPaid", { list: p.buyout.paid.join(", "), amount: p.buyout.amount.formatted }) : t("venture.buyoutNone")}
          {p.buyout.unpaid.length > 0 ? ` ${t("venture.buyoutUnpaid", { list: p.buyout.unpaid.join(", ") })}` : ""}
        </p>
      )}
      <p className="text-sm text-accent-text">{p.myIncome.minor === "0" ? t("venture.myIncomeNone") : t("venture.myIncome", { amount: p.myIncome.formatted })}</p>
      <p className="text-xs text-ink-muted">{t(`venture.policy.${p.lossPolicy}`)}</p>
    </div>
  );
}

function Entries({ l, onCorrect, onOpen }: { l: VentureLedgerDto; onCorrect: ((e: VentureEntryDto) => void) | null; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  if (l.entries.length === 0) return <p className="text-ink-muted">{t("venture.empty")}</p>;
  return (
    <div className="card overflow-x-auto">
      <h2 className="mb-2 text-lg font-semibold">{t("venture.entries")}</h2>
      <table className="w-full text-sm tabular-nums">
        <thead className="text-left text-ink-muted">
          <tr>
            <th className="py-1">{t("venture.date")}</th>
            <th>{t("venture.col.kind")}</th>
            <th>{t("common.note")}</th>
            <th className="text-right">{t("common.amount")}</th>
            <th className="pl-3">{t("venture.col.period")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {l.entries.map((e) => (
            <tr key={e.id} className="border-t border-line align-top">
              <td className="whitespace-nowrap py-1 pr-2">{showDate(e.occurredOn)}</td>
              <td className="pr-2">
                {t(`venture.kind.${e.kind}`)}
                {e.category ? <span className="text-ink-muted"> · {t(`venture.cat.${e.category}`)}</span> : null}
              </td>
              <td>
                {e.note}
                {e.corrected && <span className="ml-1 text-xs text-warn">({t("venture.corrected")})</span>}
                {e.attachments.map((a) => (
                  <button key={a.id} className="ml-2 rounded border border-line px-1 text-xs text-ink-muted hover:text-ink" onClick={() => onOpen(a.id)} disabled={!a.mime.startsWith("image/")}>
                    📎 {a.fileName}
                  </button>
                ))}
              </td>
              <td className={`text-right ${e.effect.minor.startsWith("-") ? "text-danger" : ""}`}>{e.effect.formatted}</td>
              <td className="whitespace-nowrap pl-3 text-xs text-ink-muted" title={`${t("venture.hashTitle")}: ${e.hashCode}`}>
                {e.periodNo != null ? t("venture.closedIn", { n: e.periodNo }) : t("venture.open")}
              </td>
              <td className="text-right">
                {onCorrect && e.kind !== "CORRECTION" && (
                  <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => onCorrect(e)}>
                    {t("venture.correct")}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClosedPeriod({ spaceId, l, p }: { spaceId: string; l: VentureLedgerDto; p: VenturePeriodDto }) {
  const { t } = useTranslation();
  const pdf = useMutation({ mutationFn: () => call(commands.exportVentureReport(spaceId, l.partnershipId, p.id ?? "")) });
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("venture.closedPeriod", { n: p.no, from: showDate(p.startOn), to: showDate(p.endOn) })}</h2>
        <span className="rounded border border-line px-2 py-0.5 text-xs text-ink-muted">🔒 {t("venture.locked")}</span>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <Total label={t("venture.total.income")} value={p.income.formatted} />
        <Total label={t("venture.total.expense")} value={p.expense.formatted} />
        {p.forceMajeure.minor !== "0" && <Total label={t("venture.total.forceMajeure")} value={p.forceMajeure.formatted} />}
        <Total label={t("venture.total.result")} value={p.result.formatted} strong />
      </dl>
      <Distribution p={p} />
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn-ghost" onClick={() => pdf.mutate()}>
          {t("venture.reportPdf")}
        </button>
        {p.chainCode && <span className="text-xs text-ink-muted">{t("venture.chainAt", { code: p.chainCode })}</span>}
      </div>
      <ErrorText error={pdf.error} />
    </div>
  );
}
