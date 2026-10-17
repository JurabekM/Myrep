import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { type CsvMappingDto, type CsvPreviewDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { fetchers, financeKeys } from "../finance/queries";
import { Alert, PrimaryButton, SecondaryButton } from "../finance/ui";
import { useInvalidateFamily } from "./queries";

type Step = "paste" | "map" | "preview" | "done";

/** CSV satr xato kodi → tarjima kaliti. */
function rowErrorKey(code: string) {
  switch (code) {
    case "CSV_BAD_DATE":
      return "csv.rowBadDate" as const;
    case "CSV_DATE_OUT_OF_RANGE":
      return "csv.rowDateOutOfRange" as const;
    default:
      return "csv.rowBadAmount" as const;
  }
}

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

/** Birinchi bo'sh bo'lmagan satrni ustunlarga ajratadi (faqat moslash ro'yxati uchun; tahlil Rustda). */
function sampleColumns(text: string, delimiter: string): string[] {
  const first = text.split(/\r?\n/).find((line) => line.trim() !== "") ?? "";
  const actual = delimiter === "" ? detect(first) : delimiter;
  return first.split(actual).map((cell) => cell.trim().replace(/^"|"$/g, ""));
}

function detect(line: string): string {
  const candidates = [";", ",", "\t"];
  let best = ";";
  let bestCount = -1;
  for (const candidate of candidates) {
    const count = line.split(candidate).length - 1;
    if (count > bestCount) {
      best = candidate;
      bestCount = count;
    }
  }
  return best;
}

/**
 * CSV import ustasi: matn joylash → ustunlarni moslash → ko'rib chiqish → import.
 * Summalar va sanalar Rustda tahlil qilinadi; bu yerda faqat tanlovlar va ko'rsatish.
 */
export function CsvImportWizard({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const invalidate = useInvalidateFamily();
  const categories = useQuery({ queryKey: financeKeys.categories, queryFn: fetchers.categories });
  const [step, setStep] = useState<Step>("paste");
  const [text, setText] = useState("");
  const [delimiter, setDelimiter] = useState("");
  const [hasHeader, setHasHeader] = useState(true);
  const [dateColumn, setDateColumn] = useState(0);
  const [amountColumn, setAmountColumn] = useState(1);
  const [noteColumn, setNoteColumn] = useState<number | null>(null);
  const [categoryId, setCategoryId] = useState("");
  const [skipPositive, setSkipPositive] = useState(true);
  const [preview, setPreview] = useState<CsvPreviewDto | null>(null);
  const [imported, setImported] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  const columns = sampleColumns(text, delimiter);
  const mapping: CsvMappingDto = {
    delimiter: delimiter === "" ? null : delimiter,
    hasHeader,
    dateColumn,
    amountColumn,
    noteColumn,
    categoryId: categoryId === "" ? null : categoryId,
    skipPositive,
  };

  async function runPreview() {
    setBusy(true);
    setError(null);
    try {
      setPreview(unwrap(await commands.previewCsvImport({ text, mapping })));
      setStep("preview");
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    setBusy(true);
    setError(null);
    try {
      setImported(unwrap(await commands.importCsvExpenses({ text, mapping })));
      await invalidate();
      setStep("done");
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-app p-8">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="csv-title"
        className="mx-auto flex w-full max-w-3xl flex-col gap-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 id="csv-title" className="text-2xl font-semibold text-text">
              {t("csv.title")}
            </h1>
            <p className="text-sm text-muted">{t("csv.subtitle")}</p>
          </div>
          <SecondaryButton onClick={onClose}>{t("csv.close")}</SecondaryButton>
        </div>

        {step === "paste" ? (
          <section className="flex flex-col gap-4">
            <label htmlFor="csv-text" className="text-sm text-muted">
              {t("csv.pasteLabel")}
            </label>
            <textarea
              id="csv-text"
              value={text}
              onChange={(event) => {
                setText(event.currentTarget.value);
              }}
              rows={12}
              spellCheck={false}
              className="rounded-lg border border-border bg-app p-3 font-mono text-sm text-text outline-none focus:border-accent"
              placeholder={t("csv.pastePlaceholder")}
            />
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-muted">
                {t("csv.delimiter")}
                <select
                  value={delimiter}
                  onChange={(event) => {
                    setDelimiter(event.currentTarget.value);
                  }}
                  className={SELECT_CLASS}
                >
                  <option value="">{t("csv.delimiterAuto")}</option>
                  <option value=";">;</option>
                  <option value=",">,</option>
                  <option value={"\t"}>{t("csv.delimiterTab")}</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={hasHeader}
                  onChange={(event) => {
                    setHasHeader(event.currentTarget.checked);
                  }}
                />
                {t("csv.hasHeader")}
              </label>
            </div>
            <div>
              <PrimaryButton
                disabled={text.trim() === ""}
                onClick={() => {
                  setStep("map");
                }}
              >
                {t("csv.next")}
              </PrimaryButton>
            </div>
          </section>
        ) : null}

        {step === "map" ? (
          <section className="flex flex-col gap-4">
            <p className="text-sm text-muted">{t("csv.mapHint")}</p>
            <ColumnSelect
              id="csv-date"
              label={t("csv.dateColumn")}
              columns={columns}
              value={dateColumn}
              onChange={(value) => {
                setDateColumn(value ?? 0);
              }}
            />
            <ColumnSelect
              id="csv-amount"
              label={t("csv.amountColumn")}
              columns={columns}
              value={amountColumn}
              onChange={(value) => {
                setAmountColumn(value ?? 0);
              }}
            />
            <ColumnSelect
              id="csv-note"
              label={t("csv.noteColumn")}
              columns={columns}
              value={noteColumn}
              onChange={setNoteColumn}
              optional={t("csv.noColumn")}
            />
            <div className="flex flex-col gap-2">
              <label htmlFor="csv-category" className="text-sm text-muted">
                {t("csv.category")}
              </label>
              <select
                id="csv-category"
                value={categoryId}
                onChange={(event) => {
                  setCategoryId(event.currentTarget.value);
                }}
                className={SELECT_CLASS}
              >
                <option value="">{t("family.noCategory")}</option>
                {(categories.isSuccess ? categories.data : []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={skipPositive}
                onChange={(event) => {
                  setSkipPositive(event.currentTarget.checked);
                }}
              />
              {t("csv.skipPositive")}
            </label>
            <div className="flex flex-wrap gap-2">
              <SecondaryButton
                onClick={() => {
                  setStep("paste");
                }}
              >
                {t("csv.back")}
              </SecondaryButton>
              <PrimaryButton
                disabled={busy || dateColumn === amountColumn}
                onClick={() => {
                  void runPreview();
                }}
              >
                {t("csv.preview")}
              </PrimaryButton>
            </div>
            {dateColumn === amountColumn ? <Alert>{t("csv.sameColumn")}</Alert> : null}
          </section>
        ) : null}

        {step === "preview" && preview !== null ? (
          <section className="flex flex-col gap-4">
            <p className="text-sm text-muted">
              {t("csv.previewSummary", {
                importable: preview.importable,
                skipped: preview.skipped,
                failed: preview.failed,
              })}
            </p>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-raised text-left text-xs text-subtle">
                  <tr>
                    <th className="px-3 py-2">{t("csv.colLine")}</th>
                    <th className="px-3 py-2">{t("csv.colDate")}</th>
                    <th className="px-3 py-2">{t("csv.colAmount")}</th>
                    <th className="px-3 py-2">{t("csv.colNote")}</th>
                    <th className="px-3 py-2">{t("csv.colStatus")}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row) => (
                    <tr key={row.line} className="border-t border-border">
                      <td className="px-3 py-2 text-subtle">{row.line}</td>
                      <td className="px-3 py-2 text-text">{row.date}</td>
                      <td className="px-3 py-2 text-text">{row.amount?.formatted ?? "—"}</td>
                      <td className="px-3 py-2 text-muted">{row.note ?? ""}</td>
                      <td className="px-3 py-2">
                        {row.error !== null ? (
                          <span className="text-danger">{t(rowErrorKey(row.error))}</span>
                        ) : row.skipped ? (
                          <span className="text-subtle">{t("csv.rowSkipped")}</span>
                        ) : (
                          <span className="text-muted">{t("csv.rowOk")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap gap-2">
              <SecondaryButton
                onClick={() => {
                  setStep("map");
                }}
              >
                {t("csv.back")}
              </SecondaryButton>
              <PrimaryButton
                disabled={busy || preview.failed > 0 || preview.importable === 0}
                onClick={() => {
                  void runImport();
                }}
              >
                {t("csv.import", { count: preview.importable })}
              </PrimaryButton>
            </div>
            {preview.failed > 0 ? <Alert>{t("csv.fixErrors")}</Alert> : null}
          </section>
        ) : null}

        {step === "done" ? (
          <section className="flex flex-col gap-4">
            <p className="text-base text-text">{t("csv.done", { count: imported })}</p>
            <div>
              <PrimaryButton onClick={onClose}>{t("csv.close")}</PrimaryButton>
            </div>
          </section>
        ) : null}

        {error !== null ? <Alert>{error}</Alert> : null}
      </div>
    </div>
  );
}

function ColumnSelect({
  id,
  label,
  columns,
  value,
  onChange,
  optional,
}: {
  id: string;
  label: string;
  columns: string[];
  value: number | null;
  onChange: (value: number | null) => void;
  optional?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm text-muted">
        {label}
      </label>
      <select
        id={id}
        value={value === null ? "" : String(value)}
        onChange={(event) => {
          const raw = event.currentTarget.value;
          onChange(raw === "" ? null : Number(raw));
        }}
        className={SELECT_CLASS}
      >
        {optional !== undefined ? <option value="">{optional}</option> : null}
        {columns.map((column, index) => (
          <option key={`${id}-${String(index)}`} value={String(index)}>
            {String(index + 1)}: {column === "" ? "—" : column}
          </option>
        ))}
      </select>
    </div>
  );
}
