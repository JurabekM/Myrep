import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type ExportResultDto, type ImportReportDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Field, PrimaryButton, SecondaryButton } from "../finance/ui";

/**
 * `.baraka` almashish (DESKTOP_PROMPT 6.3, D14): parol bilan shifrlangan eksport (to'liq yoki inkremental)
 * va import — avval ko'rik (nima qo'shiladi, ziddiyatlar, forklar), so'ng tasdiqlab qo'llash.
 * Fork bo'lsa import to'xtaydi; hech qachon avtomatik birlashtirilmaydi.
 */
export function ExchangeCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [exportPath, setExportPath] = useState("");
  const [exportPassword, setExportPassword] = useState("");
  const [since, setSince] = useState("");
  const [exportResult, setExportResult] = useState<ExportResultDto | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [importPath, setImportPath] = useState("");
  const [importPassword, setImportPassword] = useState("");
  const [preview, setPreview] = useState<ImportReportDto | null>(null);
  const [applied, setApplied] = useState<ImportReportDto | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  async function doExport(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setExportError(null);
    setExportResult(null);
    try {
      setExportResult(
        unwrap(
          await commands.exportBaraka({
            path: exportPath.trim() === "" ? null : exportPath,
            password: exportPassword,
            since: since.trim() === "" ? null : `${since}T00:00:00Z`,
          }),
        ),
      );
      setExportPassword("");
    } catch (caught) {
      setExportError(message(caught));
    }
  }

  async function doPreview(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setImportError(null);
    setApplied(null);
    setPreview(null);
    try {
      setPreview(
        unwrap(await commands.previewBarakaImport({ path: importPath, password: importPassword })),
      );
    } catch (caught) {
      setImportError(message(caught));
    }
  }

  async function doApply() {
    setImportError(null);
    try {
      const report = unwrap(
        await commands.applyBarakaImport({ path: importPath, password: importPassword }),
      );
      setApplied(report);
      setPreview(null);
      setImportPassword("");
      await queryClient.invalidateQueries();
    } catch (caught) {
      setImportError(message(caught));
    }
  }

  return (
    <section
      aria-labelledby="exchange-heading"
      className="flex flex-col gap-6 rounded-xl border border-border bg-surface p-6"
    >
      <div>
        <h2 id="exchange-heading" className="text-sm font-medium text-text">
          {t("exchange.title")}
        </h2>
        <p className="mt-1 text-sm text-muted">{t("exchange.hint")}</p>
      </div>

      <form className="flex flex-col gap-3" onSubmit={(event) => void doExport(event)}>
        <h3 className="text-sm font-medium text-text">{t("exchange.exportTitle")}</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Field
            id="export-path"
            label={t("exchange.exportPath")}
            value={exportPath}
            onChange={(event) => {
              setExportPath(event.currentTarget.value);
            }}
          />
          <Field
            id="export-password"
            label={t("exchange.password")}
            type="password"
            autoComplete="new-password"
            value={exportPassword}
            onChange={(event) => {
              setExportPassword(event.currentTarget.value);
            }}
          />
          <Field
            id="export-since"
            label={t("exchange.since")}
            type="date"
            value={since}
            onChange={(event) => {
              setSince(event.currentTarget.value);
            }}
          />
        </div>
        <div>
          <PrimaryButton type="submit" disabled={exportPassword.length < 8}>
            {t("exchange.exportButton")}
          </PrimaryButton>
        </div>
        {exportResult !== null ? (
          <p className="text-sm text-success" role="status">
            {t("exchange.exportDone", {
              path: exportResult.path,
              rows: exportResult.rows,
              tables: exportResult.tables,
            })}
          </p>
        ) : null}
        {exportError !== null ? <Alert>{exportError}</Alert> : null}
      </form>

      <form className="flex flex-col gap-3" onSubmit={(event) => void doPreview(event)}>
        <h3 className="text-sm font-medium text-text">{t("exchange.importTitle")}</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="import-path"
            label={t("exchange.importPath")}
            value={importPath}
            onChange={(event) => {
              setImportPath(event.currentTarget.value);
            }}
          />
          <Field
            id="import-password"
            label={t("exchange.importPassword")}
            type="password"
            autoComplete="off"
            value={importPassword}
            onChange={(event) => {
              setImportPassword(event.currentTarget.value);
            }}
          />
        </div>
        <div>
          <SecondaryButton
            type="submit"
            disabled={importPath.trim() === "" || importPassword.length < 8}
          >
            {t("exchange.previewButton")}
          </SecondaryButton>
        </div>
        {preview !== null ? (
          <ReportView report={preview} title={t("exchange.previewTitle")}>
            {preview.blocked ? (
              <p className="text-sm text-danger">
                {preview.householdMismatch
                  ? t("exchange.householdMismatch")
                  : t("exchange.blocked")}
              </p>
            ) : (
              <div>
                <PrimaryButton
                  onClick={() => {
                    void doApply();
                  }}
                >
                  {t("exchange.applyButton")}
                </PrimaryButton>
              </div>
            )}
          </ReportView>
        ) : null}
        {applied !== null ? (
          <ReportView report={applied} title={t("exchange.appliedTitle")}>
            <p className="text-sm text-success" role="status">
              {t("exchange.appliedDone")}
            </p>
          </ReportView>
        ) : null}
        {importError !== null ? <Alert>{importError}</Alert> : null}
      </form>
    </section>
  );
}

function ReportView({
  report,
  title,
  children,
}: {
  report: ImportReportDto;
  title: string;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  const insertedTotal = report.inserted.reduce((sum, item) => sum + item.count, 0);
  const updatedTotal = report.updated.reduce((sum, item) => sum + item.count, 0);
  return (
    <div
      className="flex flex-col gap-2 rounded-lg border border-border bg-app px-4 py-3"
      aria-label={title}
      role="region"
    >
      <p className="text-sm font-medium text-text">{title}</p>
      <p className="text-xs text-subtle">
        {t("exchange.source", { device: report.deviceId, at: report.exportedAt })}
      </p>
      <p className="text-sm text-text">
        {t("exchange.summary", {
          inserted: insertedTotal,
          updated: updatedTotal,
          journal: report.journalAppended,
        })}
      </p>
      {report.inserted.length > 0 || report.updated.length > 0 ? (
        <ul className="text-xs text-muted">
          {report.inserted.map((item) => (
            <li key={`i-${item.table}`}>
              {item.table}: +{item.count}
            </li>
          ))}
          {report.updated.map((item) => (
            <li key={`u-${item.table}`}>
              {item.table}: ↻{item.count}
            </li>
          ))}
        </ul>
      ) : null}
      {report.forks.length > 0 ? (
        <ul className="text-sm text-danger">
          {report.forks.map((fork) => (
            <li key={fork.agreementId}>
              {t("exchange.fork", { agreement: fork.agreementId, seq: fork.firstBroken })}
            </li>
          ))}
        </ul>
      ) : null}
      {report.conflicts.length > 0 ? (
        <ul className="text-sm text-warning">
          {report.conflicts.map((conflict) => (
            <li key={`${conflict.table}-${conflict.id}`}>
              {t("exchange.conflict", {
                table: conflict.table,
                id: conflict.id.slice(0, 8),
                reason: conflict.reason,
              })}
            </li>
          ))}
        </ul>
      ) : null}
      {children}
    </div>
  );
}
