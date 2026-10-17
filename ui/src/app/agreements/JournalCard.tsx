import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type AgreementDto, type JournalDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton } from "../finance/ui";
import { journalKindKey } from "./labels";
import { agreementFetchers, agreementKeys } from "./queries";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const KINDS = ["CONTRIBUTION", "PROFIT_DISTRIBUTION", "LOAN_PAYMENT", "CORRECTION"] as const;

/** Append-only jurnal: yozuvlar, zanjir holati, yangi yozuv (faqat hisob yurituvchi qurilmada). */
export function JournalCard({ agreement }: { agreement: AgreementDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const journal = useQuery({
    queryKey: agreementKeys.journal(agreement.id),
    queryFn: agreementFetchers.journal(agreement.id),
  });
  const [kind, setKind] = useState<(typeof KINDS)[number]>("CONTRIBUTION");
  const [party, setParty] = useState(agreement.answers.parties[0]?.id ?? "");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const next: JournalDto = unwrap(
        await commands.appendJournalEntry({
          agreementId: agreement.id,
          kind,
          partyId: party,
          amount,
          date: null,
          note: note.trim() === "" ? null : note,
        }),
      );
      queryClient.setQueryData(agreementKeys.journal(agreement.id), next);
      await queryClient.invalidateQueries({ queryKey: agreementKeys.one(agreement.id) });
      setAmount("");
      setNote("");
    } catch (caught) {
      setError(message(caught));
    }
  }

  const nameOf = (id: string) => agreement.answers.parties.find((p) => p.id === id)?.name ?? id;

  return (
    <Card title={t("agreements.journalTitle")}>
      {journal.isSuccess ? (
        <>
          <p className={`text-sm ${journal.data.chainOk ? "text-muted" : "text-danger"}`}>
            {journal.data.chainOk
              ? t("agreements.chainOk", { count: journal.data.entries.length })
              : t("agreements.chainBroken", { seq: journal.data.firstBroken ?? 0 })}
          </p>
          {journal.data.entries.length === 0 ? (
            <p className="text-sm text-muted">{t("agreements.journalEmpty")}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {journal.data.entries.map((entry) => (
                <li
                  key={entry.seq}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-app px-4 py-3"
                >
                  <span className="flex flex-col gap-1">
                    <span className="text-sm text-text">
                      {String(entry.seq)}. {t(journalKindKey(entry.kind))} · {nameOf(entry.partyId)}
                    </span>
                    <span className="text-xs text-subtle">
                      {entry.date}
                      {entry.note !== null ? ` · ${entry.note}` : ""} · {entry.hash.slice(0, 12)}…
                    </span>
                  </span>
                  <span className="text-sm text-text">{entry.amount.formatted}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
      {agreement.canWriteJournal ? (
        <form className="flex flex-col gap-4" onSubmit={(event) => void add(event)}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label htmlFor="journal-kind" className="text-sm text-muted">
                {t("agreements.journalKindLabel")}
              </label>
              <select
                id="journal-kind"
                className={SELECT_CLASS}
                value={kind}
                onChange={(event) => {
                  const value = event.currentTarget.value;
                  setKind(KINDS.find((k) => k === value) ?? "CONTRIBUTION");
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
              <label htmlFor="journal-party" className="text-sm text-muted">
                {t("agreements.party")}
              </label>
              <select
                id="journal-party"
                className={SELECT_CLASS}
                value={party}
                onChange={(event) => {
                  setParty(event.currentTarget.value);
                }}
              >
                {agreement.answers.parties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <Field
              id="journal-amount"
              label={t("agreements.amount")}
              inputMode="numeric"
              value={amount}
              onChange={(event) => {
                setAmount(event.currentTarget.value);
              }}
            />
            <Field
              id="journal-note"
              label={t("agreements.note")}
              value={note}
              onChange={(event) => {
                setNote(event.currentTarget.value);
              }}
            />
          </div>
          <div>
            <PrimaryButton type="submit" disabled={amount.trim() === "" || party === ""}>
              {t("agreements.journalAdd")}
            </PrimaryButton>
          </div>
        </form>
      ) : (
        <p className="text-xs text-subtle">{t("agreements.journalReadOnly")}</p>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
