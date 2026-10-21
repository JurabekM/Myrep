import { useMutation, useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type MemberDto, type MfTermsDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { PURPOSES, draftFrom, PurposeShares, type SharesDraft, sharesInput } from "./PurposeShares";

/** Kelishuv matni ulushlardan (foydalanuvchi o'zgartirishi mumkin). Faqat matn — hisob yadroda. */
function itemsFrom(t: TFunction, d: SharesDraft, receiver: string | null): string[] {
  const parts = PURPOSES.filter((p) => (d[p] ?? "").trim() !== "").map((p) => t("mf.terms.part", { percent: (d[p] ?? "").trim(), purpose: t(`mf.purpose.${p}`).toLowerCase() }));
  return [
    t("mf.terms.item1", { parts: parts.join(", ") }),
    receiver ? t("mf.terms.item2", { name: receiver }) : t("mf.terms.item2Any"),
    t("mf.terms.item3"),
    t("mf.terms.item4"),
  ];
}

/**
 * «Ikki qirg'oq» shartlari (musofir/SPEC 5): standart maqsad ulushlari, kim qabul qiladi va oila bilan
 * kelishuv matni — Uy makonidagi oilaviy kelishuv (kattalar PIN bilan tasdiqlaydi).
 */
export function MfTermsCard({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const terms = useQuery({ queryKey: keys.mfTerms(spaceId), queryFn: () => call(commands.mfTerms(spaceId)) });
  const household = useQuery({ queryKey: keys.household, queryFn: () => call(commands.household()) });
  const [editing, setEditing] = useState(false);
  const d = terms.error ? undefined : terms.data;
  return (
    <section className="card flex flex-col gap-3" aria-label={t("mf.terms.title")}>
      <h2 className="text-lg font-semibold">{t("mf.terms.title")}</h2>
      <p className="text-sm text-ink-muted">{t("mf.terms.intro")}</p>
      <ErrorText error={terms.error} />
      {d && !editing && <TermsView d={d} members={household.data?.members ?? []} />}
      {d && editing && <TermsForm spaceId={spaceId} d={d} members={household.data?.members ?? []} onDone={() => setEditing(false)} />}
      {d && !editing && (
        <button className="btn-ghost self-start" onClick={() => setEditing(true)}>
          {d.shares.length === 0 ? t("mf.terms.set") : t("mf.terms.change")}
        </button>
      )}
    </section>
  );
}

function TermsView({ d, members }: { d: MfTermsDto; members: MemberDto[] }) {
  const { t } = useTranslation();
  if (d.shares.length === 0) return <p className="text-sm">{t("mf.terms.none")}</p>;
  const receiver = members.find((m) => m.id === d.receiverMemberId)?.displayName;
  const a = d.agreement;
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p data-testid="mf-terms-shares">{d.shares.map((s) => `${t(`mf.purpose.${s.purpose}`)} ${s.percent} %`).join(" · ")}</p>
      {receiver && <p className="text-ink-muted">{t("mf.terms.receiverLine", { name: receiver })}</p>}
      {a && (
        <div data-testid="mf-terms-agreement" className="flex flex-col gap-1">
          <p className={a.status === "ACTIVE" ? "text-accent-text" : "text-warn"}>{t(`mf.terms.status.${a.status}`)}</p>
          <ul className="text-ink-muted">
            {a.adults.map((x) => (
              <li key={x.memberId}>
                {x.name}: {x.agreedOn ? `✓ ${showDate(x.agreedOn)}` : t("mf.terms.notYet")}
              </li>
            ))}
          </ul>
          {a.status !== "ACTIVE" && <p className="text-xs text-ink-muted">{t("mf.terms.confirmWhere")}</p>}
        </div>
      )}
    </div>
  );
}

function TermsForm({ spaceId, d, members, onDone }: { spaceId: string; d: MfTermsDto; members: MemberDto[]; onDone: () => void }) {
  const { t } = useTranslation();
  const [shares, setShares] = useState<SharesDraft>(draftFrom(d.shares));
  const [receiverId, setReceiverId] = useState(d.receiverMemberId ?? "");
  const receiverName = members.find((m) => m.id === receiverId)?.displayName ?? null;
  const [title, setTitle] = useState(d.agreement?.title ?? t("mf.terms.defaultTitle"));
  // Matn qo'lda o'zgartirilmagan bo'lsa — ulushlar va qabul qiluvchidan qayta tuziladi.
  const [items, setItems] = useState<string | null>(d.agreement ? d.agreement.items.join("\n") : null);
  const text = items ?? itemsFrom(t, shares, receiverName).join("\n");
  const save = useMutation({
    mutationFn: () =>
      call(
        commands.mfSetTerms(spaceId, {
          shares: sharesInput(shares),
          receiverMemberId: receiverId || null,
          title,
          items: text.split("\n"),
        }),
      ),
    onSuccess: onDone,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form className="flex flex-col gap-3" aria-label={t("mf.terms.form")} onSubmit={submit}>
      <PurposeShares legend={t("mf.purposesLegend")} value={shares} onChange={setShares} />
      <label>
        <span className="label">{t("mf.terms.receiver")}</span>
        <select className="field" value={receiverId} onChange={(e) => setReceiverId(e.target.value)}>
          <option value="">{t("mf.terms.anyone")}</option>
          {members.map((m) => (
            <option key={m.id} value={m.id}>
              {m.displayName}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="label">{t("family.titleField")}</span>
        <input className="field" value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        <span className="label">{t("mf.terms.text")}</span>
        <textarea className="field min-h-32" value={text} onChange={(e) => setItems(e.target.value)} />
      </label>
      {items !== null && (
        <button type="button" className="btn-ghost self-start px-3 py-1 text-sm" onClick={() => setItems(null)}>
          {t("mf.terms.regenerate")}
        </button>
      )}
      <p className="text-xs text-ink-muted">{t("mf.terms.resetHint")}</p>
      <ErrorText error={save.error} />
      <div className="flex gap-2">
        <button className="btn-primary" disabled={save.isPending}>
          {t("common.save")}
        </button>
        <button type="button" className="btn-ghost" onClick={onDone}>
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
