import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type PartnershipDto, type VentureDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Field, PrimaryButton, SecondaryButton, Stat } from "../finance/ui";
import { journalKindKey } from "./labels";
import { agreementKeys } from "./queries";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const KINDS = ["VENTURE_INCOME", "VENTURE_EXPENSE", "FORCE_MAJEURE"] as const;

/**
 * Sheriklik kassa daftari (SPEC 2E.3, D13): davr yozuvlari (D8A jurnali), davr yakuni, yopish va avtomatik
 * taqsimot, fors-major, «katta foyda» ogohlantirishi, sherik uchun davr hisoboti PDF. Biznes puli uy pulidan
 * ajratilgan. Kapital egasi qurilmasida — faqat o'qish.
 */
export function VentureCard({ partnership }: { partnership: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const venture = useQuery({
    queryKey: agreementKeys.venture(partnership.id),
    queryFn: () => commands.getVenture(partnership.id).then(unwrap),
  });
  const [kind, setKind] = useState<(typeof KINDS)[number]>("VENTURE_INCOME");
  const [party, setParty] = useState(partnership.parties[0]?.partyId ?? "");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [endOn, setEndOn] = useState("");
  const [forceNote, setForceNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pdfPath, setPdfPath] = useState<string | null>(null);

  async function apply(action: () => Promise<VentureDto>): Promise<boolean> {
    setError(null);
    try {
      queryClient.setQueryData(agreementKeys.venture(partnership.id), await action());
      await queryClient.invalidateQueries({ queryKey: agreementKeys.partnerships });
      await queryClient.invalidateQueries({
        queryKey: agreementKeys.journal(partnership.agreementId),
      });
      return true;
    } catch (caught) {
      setError(message(caught));
      return false;
    }
  }

  async function addEntry(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await apply(() =>
      commands
        .addVentureEntry({
          partnershipId: partnership.id,
          kind,
          partyId: party,
          amount,
          date: null,
          note: note.trim() === "" ? null : note,
        })
        .then(unwrap),
    );
    if (ok) {
      setAmount("");
      setNote("");
    }
  }

  async function closePeriod(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await apply(() =>
      commands
        .closeVenturePeriod({
          partnershipId: partnership.id,
          endOn,
          forceMajeureNote: forceNote.trim() === "" ? null : forceNote,
        })
        .then(unwrap),
    );
    if (ok) {
      setEndOn("");
      setForceNote("");
    }
  }

  async function createPdf(periodId: string) {
    setError(null);
    try {
      setPdfPath(unwrap(await commands.createPeriodReportPdf(periodId)));
    } catch (caught) {
      setError(message(caught));
    }
  }

  const nameOf = (id: string) => partnership.parties.find((p) => p.partyId === id)?.name ?? id;

  if (!venture.isSuccess) {
    return venture.isError ? <Alert>{t("errors.generic")}</Alert> : null;
  }
  const data = venture.data;

  return (
    <section
      aria-label={t("venture.title")}
      className="flex flex-col gap-3 rounded-lg border border-border bg-raised px-4 py-3"
    >
      <h4 className="text-sm font-medium text-text">{t("venture.title")}</h4>
      <p className="text-xs text-subtle">{t("venture.hint")}</p>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label={t("venture.income")} value={data.open.income.formatted} />
        <Stat label={t("venture.expense")} value={data.open.expense.formatted} />
        <Stat
          label={t("venture.net")}
          value={data.open.net.formatted}
          hint={
            data.open.startOn !== null
              ? t("venture.openSince", { date: data.open.startOn })
              : t("venture.firstPeriod")
          }
        />
      </div>
      {data.spike ? (
        <p className="rounded-lg border border-warning/40 px-3 py-2 text-sm text-warning">
          {t("venture.spike")}
        </p>
      ) : null}
      {data.open.entries.length === 0 ? (
        <p className="text-sm text-muted">{t("venture.noEntries")}</p>
      ) : (
        <ul className="flex flex-col gap-1 text-sm text-text">
          {data.open.entries.map((entry) => (
            <li key={entry.seq} className="flex flex-wrap justify-between gap-2">
              <span>
                {entry.date} · {t(journalKindKey(entry.kind))} · {nameOf(entry.partyId)}
                {entry.note !== null ? ` · ${entry.note}` : ""}
              </span>
              <span className={entry.kind === "VENTURE_INCOME" ? "text-success" : "text-muted"}>
                {entry.amount.formatted}
              </span>
            </li>
          ))}
        </ul>
      )}
      {data.canWrite ? (
        <>
          <form
            className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
            onSubmit={(event) => void addEntry(event)}
          >
            <div className="flex flex-col gap-2">
              <label htmlFor={`venture-kind-${partnership.id}`} className="text-sm text-muted">
                {t("venture.kindLabel")}
              </label>
              <select
                id={`venture-kind-${partnership.id}`}
                className={SELECT_CLASS}
                value={kind}
                onChange={(event) => {
                  const value = event.currentTarget.value;
                  setKind(KINDS.find((k) => k === value) ?? "VENTURE_INCOME");
                }}
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {t(journalKindKey(k))}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor={`venture-party-${partnership.id}`} className="text-sm text-muted">
                {t("venture.partyLabel")}
              </label>
              <select
                id={`venture-party-${partnership.id}`}
                className={SELECT_CLASS}
                value={party}
                onChange={(event) => {
                  setParty(event.currentTarget.value);
                }}
              >
                {partnership.parties.map((p) => (
                  <option key={p.partyId} value={p.partyId}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <Field
              id={`venture-amount-${partnership.id}`}
              label={t("venture.amount")}
              inputMode="numeric"
              value={amount}
              onChange={(event) => {
                setAmount(event.currentTarget.value);
              }}
            />
            <Field
              id={`venture-note-${partnership.id}`}
              label={t("venture.note")}
              value={note}
              onChange={(event) => {
                setNote(event.currentTarget.value);
              }}
            />
            <div className="flex items-end">
              <PrimaryButton type="submit" disabled={amount.trim() === "" || party === ""}>
                {t("venture.add")}
              </PrimaryButton>
            </div>
          </form>
          <form className="grid gap-3 sm:grid-cols-3" onSubmit={(event) => void closePeriod(event)}>
            <Field
              id={`venture-end-${partnership.id}`}
              label={t("venture.endOn")}
              type="date"
              value={endOn}
              onChange={(event) => {
                setEndOn(event.currentTarget.value);
              }}
            />
            <Field
              id={`venture-force-${partnership.id}`}
              label={t("venture.forceNote")}
              value={forceNote}
              onChange={(event) => {
                setForceNote(event.currentTarget.value);
              }}
            />
            <div className="flex items-end">
              <SecondaryButton type="submit" disabled={endOn === ""}>
                {t("venture.close")}
              </SecondaryButton>
            </div>
          </form>
        </>
      ) : (
        <p className="text-xs text-subtle">{t("venture.readOnly")}</p>
      )}

      {data.periods.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h5 className="text-sm font-medium text-text">{t("venture.periodsTitle")}</h5>
          {data.periods.map((period) => (
            <div
              key={period.id}
              className="flex flex-col gap-1 rounded-lg border border-border bg-app px-3 py-2 text-sm"
            >
              <div className="flex flex-wrap justify-between gap-2 text-text">
                <span>
                  {period.startOn} — {period.endOn}
                </span>
                <span className={period.net.minor.startsWith("-") ? "text-danger" : "text-success"}>
                  {period.net.formatted}
                </span>
              </div>
              <ul className="text-xs text-muted">
                {period.distribution.map((row) => (
                  <li key={row.partyId}>
                    {row.name} ({row.shareBp / 100} %): {row.amount.formatted}
                    {row.buyoutDeduction !== null
                      ? ` · ${t("venture.buyoutDeduction", { amount: row.buyoutDeduction.formatted })}`
                      : ""}
                  </li>
                ))}
              </ul>
              {period.forceMajeureNote !== null ? (
                <p className="text-xs text-warning">
                  {t("venture.forceMajeure", { note: period.forceMajeureNote })}
                </p>
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-subtle">
                  {t("venture.chainHead", { head: period.chainHead.slice(0, 12) })}
                </span>
                <SecondaryButton
                  className="h-8 px-2 text-xs"
                  onClick={() => {
                    void createPdf(period.id);
                  }}
                >
                  {t("venture.pdf")}
                </SecondaryButton>
              </div>
            </div>
          ))}
          {pdfPath !== null ? (
            <span className="text-xs text-subtle">{t("venture.pdfSaved", { path: pdfPath })}</span>
          ) : null}
        </div>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </section>
  );
}
