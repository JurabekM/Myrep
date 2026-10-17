import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { type ChannelDto, type IncomeOutcomeDto, commands } from "../../bindings/bindings";
import { CommandError, unwrap } from "./command-error";
import { type FinanceErrorKey, errorKey } from "./errors";
import { fetchers, financeKeys, useInvalidateFinance } from "./queries";
import { Alert, Field, PrimaryButton, SecondaryButton } from "./ui";

/** Daromad tez kiritish (Ctrl+N): summa → Enter → ulush taklifi → Enter. */
export function QuickEntry({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFinance();
  const recent = useQuery({ queryKey: financeKeys.recent, queryFn: fetchers.recent });
  const [amount, setAmount] = useState("");
  const [source, setSource] = useState("");
  const [channel, setChannel] = useState<ChannelDto>("CASH");
  const [outcome, setOutcome] = useState<IncomeOutcomeDto | null>(null);
  const [error, setError] = useState<FinanceErrorKey | null>(null);
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

  // So'nggi manbalar tugma sifatida: bir xil manba qayta yoziladi.
  const sources = [...new Set((recent.data ?? []).map((income) => income.source))].slice(0, 5);

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || amount.trim() === "") {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = unwrap(
        await commands.createIncome({
          amount,
          source: source.trim() || t("quickEntry.defaultSource"),
          channel,
          note: null,
        }),
      );
      await invalidate();
      if (result.shareSuggestion === null) {
        onClose();
      } else {
        setOutcome(result);
      }
    } catch (caught) {
      setError(errorKey(caught instanceof CommandError ? caught.code : "INTERNAL"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="quick-entry-title"
        className="flex w-full max-w-md flex-col gap-5 rounded-xl border border-border bg-surface p-6 shadow-lg"
      >
        {outcome === null ? (
          <form className="flex flex-col gap-5" onSubmit={(event) => void save(event)}>
            <h2 id="quick-entry-title" className="text-lg font-semibold text-text">
              {t("quickEntry.title")}
            </h2>
            <Field
              id="income-amount"
              label={t("quickEntry.amount")}
              value={amount}
              onChange={(event) => {
                setAmount(event.target.value);
              }}
              inputMode="decimal"
              autoComplete="off"
              autoFocus
            />
            {sources.length > 0 ? (
              <div className="flex flex-col gap-2">
                <span className="text-sm text-muted">{t("quickEntry.recentSources")}</span>
                <div className="flex flex-wrap gap-2">
                  {sources.map((name) => (
                    <button
                      key={name}
                      type="button"
                      aria-pressed={source === name}
                      onClick={() => {
                        setSource(name);
                      }}
                      className={`h-8 rounded-full border px-3 text-sm transition-colors ${
                        source === name
                          ? "border-accent text-text"
                          : "border-border text-muted hover:text-text"
                      }`}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <Field
              id="income-source"
              label={t("quickEntry.source")}
              value={source}
              placeholder={t("quickEntry.defaultSource")}
              onChange={(event) => {
                setSource(event.target.value);
              }}
              autoComplete="off"
            />
            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted">{t("quickEntry.channel")}</span>
              <div className="flex gap-2">
                <ChannelButton
                  active={channel === "CASH"}
                  onSelect={() => {
                    setChannel("CASH");
                  }}
                >
                  {t("quickEntry.cash")}
                </ChannelButton>
                <ChannelButton
                  active={channel === "CARD"}
                  onSelect={() => {
                    setChannel("CARD");
                  }}
                >
                  {t("quickEntry.card")}
                </ChannelButton>
              </div>
            </div>
            {error !== null ? <Alert>{t(error)}</Alert> : null}
            <div className="flex justify-end gap-2">
              <SecondaryButton onClick={onClose}>{t("common.cancel")}</SecondaryButton>
              <PrimaryButton type="submit" disabled={busy || amount.trim() === ""}>
                {t("quickEntry.save")}
              </PrimaryButton>
            </div>
          </form>
        ) : (
          <ShareStep
            outcome={outcome}
            onAccept={async (text) => {
              await acceptShare(outcome, text);
            }}
            onClose={onClose}
          />
        )}
      </div>
    </div>
  );

  async function acceptShare(current: IncomeOutcomeDto, text: string) {
    setError(null);
    try {
      unwrap(await commands.acceptShare(current.income.id, text));
      await invalidate();
      onClose();
    } catch (caught) {
      setError(errorKey(caught instanceof CommandError ? caught.code : "INTERNAL"));
    }
  }
}

function ChannelButton({
  active,
  onSelect,
  children,
}: {
  active: boolean;
  onSelect: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onSelect}
      className={`h-10 flex-1 rounded-lg border text-sm transition-colors ${
        active ? "border-accent text-text" : "border-border text-muted hover:text-text"
      }`}
    >
      {children}
    </button>
  );
}

/** Ulush taklifi: «Shundan X so'm — kelajagingiz uchun». Birinchi tugma fokusda — Enter bilan tasdiqlanadi. */
function ShareStep({
  outcome,
  onAccept,
  onClose,
}: {
  outcome: IncomeOutcomeDto;
  onAccept: (text: string) => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [customOpen, setCustomOpen] = useState(false);
  const [custom, setCustom] = useState("");
  const suggestion = outcome.shareSuggestion;

  if (suggestion === null) {
    return null;
  }

  return (
    <div className="flex flex-col gap-5">
      <h2 id="quick-entry-title" className="text-lg font-semibold text-text">
        {t("quickEntry.shareTitle")}
      </h2>
      <p className="text-base text-muted">
        {t("quickEntry.shareText", { amount: suggestion.formatted })}
      </p>
      <PrimaryButton
        autoFocus
        onClick={() => {
          void onAccept(suggestion.formatted);
        }}
      >
        {t("quickEntry.shareAccept")}
      </PrimaryButton>
      {customOpen ? (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void onAccept(custom);
          }}
        >
          <Field
            id="custom-share"
            label={t("quickEntry.customAmount")}
            value={custom}
            inputMode="decimal"
            autoComplete="off"
            autoFocus
            onChange={(event) => {
              setCustom(event.target.value);
            }}
          />
          <PrimaryButton type="submit" disabled={custom.trim() === ""}>
            {t("quickEntry.shareSave")}
          </PrimaryButton>
        </form>
      ) : (
        <SecondaryButton
          onClick={() => {
            setCustomOpen(true);
          }}
        >
          {t("quickEntry.shareCustom")}
        </SecondaryButton>
      )}
      <SecondaryButton onClick={onClose}>{t("quickEntry.shareSkip")}</SecondaryButton>
    </div>
  );
}
