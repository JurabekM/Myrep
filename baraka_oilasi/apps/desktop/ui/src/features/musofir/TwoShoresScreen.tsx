import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MemberDto, type MfRemittanceDto, type MfTwoShoresDto } from "../../bindings";
import { AmountInput } from "../../components/AmountInput";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { PURPOSES } from "./PurposeShares";

type Channel = "CASH" | "CARD";

/** Maqsadlar qoldig'i (yadrodan tayyor): olingan, sarflangan, qoldiq. */
export function PurposesTable({ v }: { v: MfTwoShoresDto }) {
  const { t } = useTranslation();
  if (v.purposes.length === 0) return <p className="text-sm text-ink-muted">{t("mf.shores.noneYet")}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-ink-muted">
          <tr>
            <th className="py-1 pr-3 font-normal">{t("mf.shores.purpose")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("mf.shores.received")}</th>
            <th className="py-1 pr-3 text-right font-normal">{t("mf.shores.spent")}</th>
            <th className="py-1 text-right font-normal">{t("mf.shores.balance")}</th>
          </tr>
        </thead>
        <tbody>
          {v.purposes.map((p) => (
            <tr key={p.purpose} data-testid={`mf-purpose-${p.purpose}`} className="border-t border-line">
              <td className="py-1 pr-3">{t(`mf.purpose.${p.purpose}`)}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{p.received.formatted}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{p.spent.formatted}</td>
              <td className={`py-1 text-right tabular-nums ${p.overspent ? "text-warn" : ""}`}>{p.balance.formatted}</td>
            </tr>
          ))}
          <tr className="border-t border-line font-semibold">
            <td className="py-1 pr-3">{t("mf.shores.total")}</td>
            <td className="py-1 pr-3 text-right tabular-nums">{v.received.formatted}</td>
            <td className="py-1 pr-3 text-right tabular-nums">{v.spent.formatted}</td>
            <td data-testid="mf-shores-balance" className="py-1 text-right tabular-nums">
              {v.balance.formatted}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/**
 * Uy tomoni «Ikki qirg'oq» (musofir/SPEC 5): kelgan pulni qabul qilish (Uy makonida daromad), maqsad
 * bo'yicha xarajat va maqsadlar qoldig'i. Uydagi oila qurilmasida (ADR-0004) musofirning shaxsiy
 * ma'lumoti yo'q — bu ekran faqat yuborilganlar bilan ishlaydi.
 */
export function TwoShoresScreen({ mfSpaceId, uySpaceId }: { mfSpaceId: string; uySpaceId: string }) {
  const { t } = useTranslation();
  const v = useQuery({ queryKey: keys.mfTwoShores(mfSpaceId), queryFn: () => call(commands.mfTwoShores(mfSpaceId)) });
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const members = household.data?.members ?? [];
  const d = v.error ? undefined : v.data;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("mf.shores.title")}</h1>
      <p className="text-ink-muted">{t("mf.shores.intro")}</p>
      <ErrorText error={v.error} />
      {d && (
        <>
          {d.overspent && (
            <p role="note" data-testid="mf-shores-overspent" className="card border-warn py-3 text-sm">
              {t("mf.shores.overspent")}
            </p>
          )}
          <section className="card flex flex-col gap-2" aria-label={t("mf.shores.purposes")}>
            <h2 className="text-lg font-semibold">{t("mf.shores.purposes")}</h2>
            <PurposesTable v={d} />
          </section>
          <section className="card flex flex-col gap-3" aria-label={t("mf.shores.incoming")}>
            <h2 className="text-lg font-semibold">
              {t("mf.shores.incoming")}
              {d.pending > 0 && <span className="ml-2 text-sm font-normal text-warn">{t("mf.shores.pending", { count: d.pending })}</span>}
            </h2>
            {d.remittances.length === 0 && <p className="text-sm text-ink-muted">{t("mf.shores.noRemittances")}</p>}
            {d.remittances.map((r) => (
              <Remittance key={r.moveId} mfSpaceId={mfSpaceId} r={r} members={members} />
            ))}
          </section>
          <SpendForm mfSpaceId={mfSpaceId} uySpaceId={uySpaceId} />
          {d.spends.length > 0 && <Spends uySpaceId={uySpaceId} v={d} />}
        </>
      )}
    </section>
  );
}

function ChannelButtons({ value, onChange }: { value: Channel; onChange: (c: Channel) => void }) {
  const { t } = useTranslation();
  return (
    <fieldset>
      <legend className="label">{t("mf.channel")}</legend>
      <div className="flex gap-2">
        {(["CARD", "CASH"] as const).map((c) => (
          <button key={c} type="button" aria-pressed={value === c} className={value === c ? "btn-primary" : "btn-ghost"} onClick={() => onChange(c)}>
            {t(`kk.channel.${c}`)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function Remittance({ mfSpaceId, r, members }: { mfSpaceId: string; r: MfRemittanceDto; members: MemberDto[] }) {
  const { t } = useTranslation();
  const [received, setReceived] = useState(r.expected?.plain ?? "");
  const [memberId, setMemberId] = useState("");
  const [channel, setChannel] = useState<Channel>("CARD");
  const confirm = useMutation({
    mutationFn: () => call(commands.mfConfirmReceipt(mfSpaceId, r.moveId, { received, channel, memberId: memberId || null, receivedOn: null, note: null })),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    confirm.mutate();
  };
  const shares = r.shares.map((s) => `${t(`mf.purpose.${s.purpose}`)} ${s.percent} %`).join(" · ");
  return (
    <article data-testid="mf-remittance" aria-label={t("mf.shores.sentOn", { date: showDate(r.sentOn) })} className="flex flex-col gap-2 border-t border-line pt-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p>
          <span className="font-medium">{t("mf.shores.sentOn", { date: showDate(r.sentOn) })}</span> · <span className="tabular-nums">{r.sent.formatted}</span>
          {r.note && <span className="text-ink-muted"> · {r.note}</span>}
        </p>
        {r.receipt ? (
          <span className="text-accent-text">
            {t("mf.shores.receivedLine", { amount: r.receipt.received.formatted, date: showDate(r.receipt.receivedOn) })}
            {r.receipt.memberName && ` · ${r.receipt.memberName}`}
          </span>
        ) : (
          <span className="text-warn">{t("mf.shores.onTheWay")}</span>
        )}
      </div>
      <p className="text-ink-muted">{shares}</p>
      {r.allocation.length > 0 && <p className="tabular-nums text-ink-muted">{r.allocation.map((a) => `${t(`mf.purpose.${a.purpose}`)}: ${a.amount.formatted}`).join(" · ")}</p>}
      {!r.receipt && (
        <form className="flex flex-wrap items-end gap-3" aria-label={t("mf.shores.confirmForm")} onSubmit={submit}>
          <label>
            <span className="label">{t("mf.shores.receivedAmount")}</span>
            <AmountInput value={received} onChange={(e) => setReceived(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("mf.shores.who")}</span>
            <select className="field" value={memberId} onChange={(e) => setMemberId(e.target.value)}>
              <option value="">—</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.displayName}
                </option>
              ))}
            </select>
          </label>
          <ChannelButtons value={channel} onChange={setChannel} />
          <button className="btn-primary" disabled={confirm.isPending}>
            {t("mf.shores.confirm")}
          </button>
          <div className="w-full">
            <ErrorText error={confirm.error} />
          </div>
        </form>
      )}
    </article>
  );
}

function SpendForm({ mfSpaceId, uySpaceId }: { mfSpaceId: string; uySpaceId: string }) {
  const { t } = useTranslation();
  const categories = useQuery({ queryKey: keys.categories(uySpaceId), queryFn: () => call(commands.categories(uySpaceId)) });
  const [purpose, setPurpose] = useState<string>("HOUSEHOLD");
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [channel, setChannel] = useState<Channel>("CASH");
  const [note, setNote] = useState("");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.mfRecordSpend(mfSpaceId, {
          purpose,
          amount,
          categoryId: categoryId || categories.data?.[0]?.id || "",
          channel,
          occurredOn: null,
          note: note.trim() || null,
        }),
      ),
    onSuccess: () => {
      setAmount("");
      setNote("");
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="card grid gap-3 md:grid-cols-2" aria-label={t("mf.shores.spendForm")} onSubmit={submit}>
      <h2 className="text-lg font-semibold md:col-span-2">{t("mf.shores.spendForm")}</h2>
      <label>
        <span className="label">{t("mf.shores.purpose")}</span>
        <select className="field" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
          {PURPOSES.map((p) => (
            <option key={p} value={p}>
              {t(`mf.purpose.${p}`)}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">{t("common.amount")}</span>
        <AmountInput value={amount} onChange={(e) => setAmount(e.target.value)} required />
      </label>
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
      <ChannelButtons value={channel} onChange={setChannel} />
      <label className="md:col-span-2">
        <span className="label">{t("kk.note")}</span>
        <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="md:col-span-2">
        <ErrorText error={save.error} />
      </div>
      <button className="btn-primary self-start md:col-span-2 md:justify-self-start" disabled={save.isPending}>
        {t("mf.shores.saveSpend")}
      </button>
    </form>
  );
}

function Spends({ uySpaceId, v }: { uySpaceId: string; v: MfTwoShoresDto }) {
  const { t } = useTranslation();
  const categories = useQuery({ queryKey: keys.categories(uySpaceId), queryFn: () => call(commands.categories(uySpaceId)) });
  const category = (id: string) => {
    const c = categories.data?.find((x) => x.id === id);
    return c ? (c.customName ?? t(c.nameKey)) : "";
  };
  return (
    <section className="card flex flex-col gap-2" aria-label={t("mf.shores.spends")}>
      <h2 className="text-lg font-semibold">{t("mf.shores.spends")}</h2>
      <ul>
        {v.spends.map((s) => (
          <li key={s.expenseId} data-testid="mf-spend" className="flex flex-wrap justify-between gap-2 border-t border-line py-1 text-sm">
            <span>
              {showDate(s.occurredOn)} · {t(`mf.purpose.${s.purpose}`)}
              <span className="text-ink-muted"> · {[category(s.categoryId), s.note].filter(Boolean).join(" · ")}</span>
            </span>
            <span className="tabular-nums">{s.amount.formatted}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
