import { useQuery } from "@tanstack/react-query";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { type CenterRowDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { Alert, Card, Field, SecondaryButton } from "../finance/ui";
import { kindKey, statusKey } from "./labels";
import { agreementKeys } from "./queries";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const KINDS = ["", "PARTNERSHIP", "LOAN", "FAMILY", "OTHER"] as const;
const STATUSES = ["", "DRAFT", "SIGNED", "IN_DISPUTE", "ENDED"] as const;

/**
 * Kelishuvlar markazi (SPEC 2F, D13A): barcha kelishuvlar jadvali — turi, holati, keyingi ko'rik, ochiq hodisalar,
 * nizolar, zanjir. Filtr (tur, holat) va qidiruv. TanStack Table (ADR).
 */
export function CenterTable({ onOpen }: { onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const center = useQuery({
    queryKey: agreementKeys.center,
    queryFn: () => commands.getAgreementsCenter().then(unwrap),
  });
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<(typeof KINDS)[number]>("");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("");

  const columns = useMemo<ColumnDef<CenterRowDto>[]>(
    () => [
      { id: "title", header: t("center.colTitle"), accessorKey: "title" },
      {
        id: "kind",
        header: t("center.colKind"),
        accessorFn: (row) => t(kindKey(row.kind)),
      },
      {
        id: "status",
        header: t("center.colStatus"),
        accessorFn: (row) => t(statusKey(row.status)),
      },
      {
        id: "review",
        header: t("center.colReview"),
        accessorFn: (row) =>
          row.reviewDate === null
            ? "—"
            : row.reviewDue
              ? `${row.reviewDate} · ${t("center.due")}`
              : row.reviewDate,
      },
      {
        id: "incidents",
        header: t("center.colIncidents"),
        accessorFn: (row) => String(row.openIncidents),
      },
      {
        id: "disputes",
        header: t("center.colDisputes"),
        accessorFn: (row) => String(row.openDisputes),
      },
      {
        id: "chain",
        header: t("center.colChain"),
        accessorFn: (row) =>
          row.familyPending > 0
            ? t("center.familyPending", { count: row.familyPending })
            : row.chainOk
              ? t("center.chainOk")
              : t("center.chainBroken"),
      },
    ],
    [t],
  );
  const data = useMemo(() => {
    const rows = center.data?.rows ?? [];
    const needle = search.trim().toLowerCase();
    return rows.filter(
      (row) =>
        (kind === "" || row.kind === kind) &&
        (status === "" || row.status === status) &&
        (needle === "" || row.title.toLowerCase().includes(needle)),
    );
  }, [center.data, search, kind, status]);
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <Card title={t("center.title")}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Field
          id="center-search"
          label={t("center.search")}
          value={search}
          onChange={(event) => {
            setSearch(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="center-kind" className="text-sm text-muted">
            {t("center.filterKind")}
          </label>
          <select
            id="center-kind"
            className={SELECT_CLASS}
            value={kind}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setKind(KINDS.find((k) => k === value) ?? "");
            }}
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k === "" ? t("center.all") : t(kindKey(k))}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="center-status" className="text-sm text-muted">
            {t("center.filterStatus")}
          </label>
          <select
            id="center-status"
            className={SELECT_CLASS}
            value={status}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setStatus(STATUSES.find((s) => s === value) ?? "");
            }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === "" ? t("center.all") : t(statusKey(s))}
              </option>
            ))}
          </select>
        </div>
      </div>
      {center.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {center.isSuccess && center.data.rows.length === 0 ? (
        <p className="text-sm text-muted">{t("agreements.empty")}</p>
      ) : null}
      {center.isSuccess && center.data.rows.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm" aria-label={t("center.title")}>
            <thead className="bg-raised text-left text-xs text-subtle">
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                  <th className="px-3 py-2" />
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-t border-border text-text">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                  <td className="px-3 py-2">
                    <SecondaryButton
                      className="h-8 px-2 text-xs"
                      onClick={() => {
                        onOpen(row.original.id);
                      }}
                    >
                      {t("agreements.open")}
                    </SecondaryButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted">{t("center.noMatch")}</p>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
