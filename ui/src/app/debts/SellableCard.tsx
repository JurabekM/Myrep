import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type LoansDto, type SellableDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import { Alert, Card, Field, PrimaryButton, SecondaryButton, Stat } from "../finance/ui";

/**
 * Sotiladigan buyumlar (SPEC 2D.6, D10 qoldig'i): qarzdan chiqish uchun zaxira manba — ro'yxat, taxminiy jami,
 * qarz qoldig'iga nisbatan. Hisob Rustda.
 */
export function SellableCard({
  sellable,
  outstanding,
}: {
  sellable: SellableDto;
  outstanding: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [name, setName] = useState("");
  const [estimate, setEstimate] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<LoansDto>): Promise<boolean> {
    setError(null);
    try {
      queryClient.setQueryData(financeKeys.loans, await action());
      return true;
    } catch (caught) {
      setError(message(caught));
      return false;
    }
  }

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await run(() =>
      commands
        .addSellableItem({ name, estimate, note: note.trim() === "" ? null : note })
        .then(unwrap),
    );
    if (ok) {
      setName("");
      setEstimate("");
      setNote("");
    }
  }

  return (
    <Card title={t("sellable.title")}>
      <p className="text-sm text-muted">{t("sellable.intro")}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat label={t("sellable.total")} value={sellable.totalEstimate.formatted} />
        <Stat label={t("debts.totalOutstanding")} value={outstanding} />
      </div>
      {sellable.items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {sellable.items.map((item) => (
            <li
              key={item.id}
              className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-app px-4 py-2 text-sm ${
                item.soldOn !== null ? "opacity-60" : ""
              }`}
            >
              <span className="text-text">
                {item.name} · {item.estimate.formatted}
                {item.note !== null ? ` · ${item.note}` : ""}
                {item.soldOn !== null ? ` · ${t("sellable.soldOn", { date: item.soldOn })}` : ""}
              </span>
              <span className="flex gap-2">
                {item.soldOn === null ? (
                  <SecondaryButton
                    className="h-8 px-2 text-xs"
                    onClick={() => {
                      void run(() => commands.markSellableSold(item.id).then(unwrap));
                    }}
                  >
                    {t("sellable.markSold")}
                  </SecondaryButton>
                ) : null}
                <SecondaryButton
                  className="h-8 px-2 text-xs"
                  aria-label={t("sellable.removeLabel", { name: item.name })}
                  onClick={() => {
                    void run(() => commands.removeSellableItem(item.id).then(unwrap));
                  }}
                >
                  {t("ceremonies.remove")}
                </SecondaryButton>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{t("sellable.empty")}</p>
      )}
      <form
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        onSubmit={(event) => void add(event)}
      >
        <Field
          id="sellable-name"
          label={t("sellable.name")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id="sellable-estimate"
          label={t("sellable.estimate")}
          inputMode="numeric"
          value={estimate}
          onChange={(event) => {
            setEstimate(event.currentTarget.value);
          }}
        />
        <Field
          id="sellable-note"
          label={t("sellable.note")}
          value={note}
          onChange={(event) => {
            setNote(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={name.trim() === "" || estimate.trim() === ""}>
            {t("sellable.add")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
