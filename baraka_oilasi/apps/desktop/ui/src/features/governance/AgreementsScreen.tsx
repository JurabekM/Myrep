import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper, flexRender, getCoreRowModel, getFilteredRowModel, getSortedRowModel, type SortingState, useReactTable } from "@tanstack/react-table";
import { type FormEvent, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { type AgreementSummaryDto, commands, type FamilyAgreementDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";
import { showDate } from "../../lib/date";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";
import { ReminderText } from "./GovernanceView";

/** To'rtta shablon (uy/SPEC 2F.10) va erkin kelishuv. Bandlar matni — i18n'dan boshlang'ich qiymat. */
const TEMPLATES = ["CHORES", "MONEY_PLACE", "WANT_LIMIT", "COUNCIL", "OTHER"] as const;
const TEMPLATE_ITEMS = 3;
const TYPES = ["ALL", "PARTNERSHIP", "FAMILY", "LOAN"] as const;

const column = createColumnHelper<AgreementSummaryDto>();

/**
 * Kelishuvlar markazi (D13A): barcha kelishuvlar — turi, holati, keyingi ko'rik, ochiq hodisa va
 * nizolar; filtr va qidiruv. Oilaviy kelishuvlar shu yerda yaratiladi va kattalar tasdiqlaydi.
 */
export function AgreementsScreen({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const [view, setView] = useState<"center" | "family">("center");
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("agreements.title")}</h1>
      <div role="tablist" className="flex gap-1 border-b border-line">
        {(["center", "family"] as const).map((x) => (
          <button
            key={x}
            role="tab"
            aria-selected={view === x}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${view === x ? "border-accent text-ink" : "border-transparent text-ink-muted hover:text-ink"}`}
            onClick={() => setView(x)}
          >
            {t(`agreements.tab.${x}`)}
          </button>
        ))}
      </div>
      {view === "center" ? <Center spaceId={spaceId} onFamily={() => setView("family")} /> : <Family spaceId={spaceId} />}
    </section>
  );
}

function Center({ spaceId, onFamily }: { spaceId: string; onFamily: () => void }) {
  const { t } = useTranslation();
  const openPartnership = useUi((s) => s.openPartnership);
  const q = useQuery({ queryKey: keys.agreements(spaceId), queryFn: () => call(commands.agreementsCenter(spaceId)) });
  const [type, setType] = useState<(typeof TYPES)[number]>("ALL");
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);
  const rows = useMemo(() => (q.data ?? []).filter((a) => type === "ALL" || a.agreementType === type), [q.data, type]);
  const columns = useMemo(
    () => [
      column.accessor("title", { header: () => t("agreements.col.title") }),
      column.accessor("agreementType", { header: () => t("agreements.col.type"), cell: (c) => t(`agreements.type.${c.getValue()}`) }),
      column.accessor("status", { header: () => t("agreements.col.status"), cell: (c) => <StatusText status={c.getValue()} /> }),
      column.accessor("nextReview", {
        header: () => t("agreements.col.nextReview"),
        sortUndefined: "last",
        cell: (c) => (
          <span className="tabular-nums">
            {c.getValue() ? showDate(c.getValue() ?? "") : "—"}
            {c.row.original.reminder && (
              <span className="block text-xs">
                <ReminderText r={c.row.original.reminder} />
              </span>
            )}
          </span>
        ),
      }),
      column.accessor("openIncidents", { header: () => t("agreements.col.incidents"), cell: (c) => <Count n={c.getValue()} tone="text-warn" /> }),
      column.accessor("openDisputes", { header: () => t("agreements.col.disputes"), cell: (c) => <Count n={c.getValue()} tone="text-danger" /> }),
    ],
    [t],
  );
  // TanStack Table v8 barqaror bo'lmagan funksiyalar qaytaradi — React Compiler bu komponentni
  // memoizatsiya qilmaydi (jadval kichik, qayta chizish arzon).
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: rows,
    columns,
    state: { globalFilter: search, sorting },
    onGlobalFilterChange: setSearch,
    onSortingChange: setSorting,
    globalFilterFn: (row, _id, value: string) => row.original.title.toLowerCase().includes(value.trim().toLowerCase()),
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  const open = (a: AgreementSummaryDto) => {
    if (a.agreementType === "PARTNERSHIP") openPartnership(a.refId, a.status === "DRAFT" || a.status === "SIGNED" ? "contract" : "governance");
    else if (a.agreementType === "FAMILY") onFamily();
  };
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <label>
          <span className="label">{t("agreements.filter")}</span>
          <select className="field" value={type} onChange={(e) => setType(e.target.value as (typeof TYPES)[number])}>
            {TYPES.map((x) => (
              <option key={x} value={x}>
                {t(`agreements.type.${x}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0 flex-1">
          <span className="label">{t("agreements.search")}</span>
          <input className="field" type="search" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
      </div>
      <ErrorText error={q.error} />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-sidebar text-ink-muted">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => {
                  const dir = h.column.getIsSorted();
                  return (
                    <th key={h.id} className="px-3 py-2 font-medium" aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}>
                      <button className="hover:text-ink" onClick={h.column.getToggleSortingHandler()}>
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {dir === "asc" ? " ↑" : dir === "desc" ? " ↓" : ""}
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((r) => (
              <tr key={r.id} className="cursor-pointer border-t border-line align-top hover:bg-surface" onClick={() => open(r.original)}>
                {r.getVisibleCells().map((c) => (
                  <td key={c.id} className="px-3 py-2">
                    {flexRender(c.column.columnDef.cell, c.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {table.getRowModel().rows.length === 0 && <p className="p-4 text-ink-muted">{t("agreements.empty")}</p>}
      </div>
    </div>
  );
}

function StatusText({ status }: { status: string }) {
  const { t } = useTranslation();
  const tone = status === "ACTIVE" ? "text-accent-text" : status === "IN_DISPUTE" ? "text-danger" : "text-ink-muted";
  return <span className={tone}>{t(`agreements.status.${status}`)}</span>;
}

function Count({ n, tone }: { n: number; tone: string }) {
  return <span className={`tabular-nums ${n > 0 ? tone : "text-ink-muted"}`}>{n}</span>;
}

type Draft = { id: string | null; templateKey: string; title: string; items: string[]; reviewDate: string };

function Family({ spaceId }: { spaceId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: keys.family(spaceId), queryFn: () => call(commands.familyAgreements(spaceId)) });
  const [draft, setDraft] = useState<Draft | null>(null);
  const fromTemplate = (k: string): Draft => ({
    id: null,
    templateKey: k,
    title: t(`family.tpl.${k}.title`),
    items: k === "OTHER" ? [""] : Array.from({ length: TEMPLATE_ITEMS }, (_, i) => t(`family.tpl.${k}.item${i + 1}`)),
    reviewDate: "",
  });
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: keys.family(spaceId) });
    void qc.invalidateQueries({ queryKey: keys.agreements(spaceId) });
    void qc.invalidateQueries({ queryKey: keys.reminders(spaceId) });
  };
  const save = useMutation({
    mutationFn: (d: Draft) => {
      const input = { templateKey: d.templateKey, title: d.title, items: d.items, reviewDate: d.reviewDate.trim() === "" ? null : d.reviewDate };
      return call(d.id ? commands.updateFamilyAgreement(spaceId, d.id, input) : commands.createFamilyAgreement(spaceId, input));
    },
    onSuccess: () => {
      setDraft(null);
      refresh();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (draft) save.mutate(draft);
  };
  return (
    <div className="flex flex-col gap-4">
      <p className="text-ink-muted">{t("family.intro")}</p>
      {!draft && (
        <div className="flex flex-wrap gap-2">
          {TEMPLATES.map((k) => (
            <button key={k} className="btn-ghost" onClick={() => setDraft(fromTemplate(k))}>
              {t(`family.tpl.${k}.title`)}
            </button>
          ))}
        </div>
      )}
      {draft && (
        <form className="card flex flex-col gap-3" onSubmit={submit} aria-label={t("family.edit")}>
          <label>
            <span className="label">{t("family.titleField")}</span>
            <input className="field" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
          </label>
          <fieldset className="flex flex-col gap-2">
            <legend className="label">{t("family.items")}</legend>
            {draft.items.map((it, i) => (
              <div key={i} className="flex gap-2">
                <input
                  className="field min-w-0 flex-1"
                  aria-label={t("family.itemN", { n: i + 1 })}
                  value={it}
                  onChange={(e) => setDraft({ ...draft, items: draft.items.map((x, j) => (j === i ? e.target.value : x)) })}
                />
                <button type="button" className="btn-ghost px-3" aria-label={t("family.removeItem", { n: i + 1 })} onClick={() => setDraft({ ...draft, items: draft.items.filter((_, j) => j !== i) })}>
                  ×
                </button>
              </div>
            ))}
            <button type="button" className="btn-ghost self-start px-3 py-1 text-sm" onClick={() => setDraft({ ...draft, items: [...draft.items, ""] })}>
              + {t("family.addItem")}
            </button>
          </fieldset>
          <label className="max-w-xs">
            <span className="label">{t("family.reviewDate")}</span>
            <input className="field tabular-nums" placeholder="01.03.2027" value={draft.reviewDate} onChange={(e) => setDraft({ ...draft, reviewDate: e.target.value })} />
          </label>
          {draft.id && <p className="text-sm text-warn">{t("family.editResets")}</p>}
          <ErrorText error={save.error} />
          <div className="flex gap-2">
            <button className="btn-primary" disabled={save.isPending}>
              {t("common.save")}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setDraft(null)}>
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}
      <ErrorText error={list.error} />
      {list.data?.length === 0 && !draft && <p className="text-ink-muted">{t("family.empty")}</p>}
      {(list.data ?? []).map((f) => (
        <FamilyCard
          key={f.id}
          spaceId={spaceId}
          f={f}
          onChanged={refresh}
          onEdit={() => setDraft({ id: f.id, templateKey: f.templateKey, title: f.title, items: f.items, reviewDate: f.reviewDate ? showDate(f.reviewDate) : "" })}
        />
      ))}
    </div>
  );
}

function FamilyCard({ spaceId, f, onChanged, onEdit }: { spaceId: string; f: FamilyAgreementDto; onChanged: () => void; onEdit: () => void }) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState<{ memberId: string; name: string } | null>(null);
  const [pin, setPin] = useState("");
  const confirm = useMutation({
    mutationFn: () => call(commands.confirmFamilyAgreement(spaceId, pin, f.id, confirming?.memberId ?? "")),
    onSuccess: () => {
      setConfirming(null);
      setPin("");
      onChanged();
    },
  });
  const remove = useMutation({ mutationFn: () => call(commands.deleteFamilyAgreement(spaceId, f.id)), onSuccess: onChanged });
  return (
    <article className={`card flex flex-col gap-3 ${f.status === "ACTIVE" ? "border-accent/60" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{f.title}</h2>
        <span className={f.status === "ACTIVE" ? "text-sm text-accent-text" : "text-sm text-warn"}>{t(`family.status.${f.status}`)}</span>
      </div>
      <ol className="list-decimal pl-6">
        {f.items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ol>
      <p className="text-sm text-ink-muted">
        {f.reviewDate ? t("family.reviewOn", { date: showDate(f.reviewDate) }) : t("family.noReview")} · {t("partnership.hashCode", { code: f.hashCode })}
      </p>
      <div className="flex flex-col gap-2">
        {f.adults.map((a) => (
          <div key={a.memberId} className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2">
            <span>{a.name}</span>
            {a.agreedOn ? (
              <span className="text-sm text-accent-text">✓ {t("partnership.agreedOn", { date: showDate(a.agreedOn) })}</span>
            ) : (
              <button className="btn-ghost px-3 py-1 text-sm" onClick={() => setConfirming({ memberId: a.memberId, name: a.name })}>
                {t("family.confirmAs", { name: a.name })}
              </button>
            )}
          </div>
        ))}
      </div>
      {confirming && (
        <form
          className="flex flex-wrap items-end gap-2 rounded border border-accent/60 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            confirm.mutate();
          }}
        >
          <label>
            <span className="label">{t("family.pinFor", { name: confirming.name })}</span>
            <input className="field tabular-nums" type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(e) => setPin(e.target.value)} />
          </label>
          <button className="btn-primary" disabled={confirm.isPending || pin === ""}>
            {t("family.confirm")}
          </button>
          <button type="button" className="btn-ghost" onClick={() => setConfirming(null)}>
            {t("common.cancel")}
          </button>
        </form>
      )}
      <ErrorText error={confirm.error ?? remove.error} />
      <div className="flex gap-2">
        <button className="btn-ghost px-3 py-1 text-sm" onClick={onEdit}>
          {t("family.editButton")}
        </button>
        <button className="btn-ghost px-3 py-1 text-sm" disabled={remove.isPending} onClick={() => remove.mutate()}>
          {t("family.delete")}
        </button>
      </div>
    </article>
  );
}
