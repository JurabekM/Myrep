import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton } from "../finance/ui";
import { familyFetchers, familyKeys, useInvalidateFamily } from "./queries";

/** Hafta kunlari tarjima kalitlari: indeks 0 — dushanba (backend bilan bir xil). */
const WEEKDAY_KEYS = [
  "family.weekdays.mon",
  "family.weekdays.tue",
  "family.weekdays.wed",
  "family.weekdays.thu",
  "family.weekdays.fri",
  "family.weekdays.sat",
  "family.weekdays.sun",
] as const;

/** Juma shirinligi: rejalashtirilgan ritual ro'yxati va yangisini qo'shish. */
export function TreatsCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const treats = useQuery({ queryKey: familyKeys.treats, queryFn: familyFetchers.treats });
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [weekday, setWeekday] = useState(4);
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.addTreat({ name, amount, weekday }).then(unwrap);
      setName("");
      setAmount("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("family.treatsTitle")}>
      {treats.isSuccess && treats.data.length === 0 ? (
        <p className="text-sm text-muted">{t("family.treatEmpty")}</p>
      ) : null}
      {treats.isSuccess && treats.data.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {treats.data.map((treat) => (
            <li
              key={treat.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-border bg-app px-4 py-3"
            >
              <span className="flex flex-col gap-1">
                <span className="text-sm text-text">{treat.name}</span>
                <span className="text-xs text-subtle">
                  {t(WEEKDAY_KEYS[treat.weekday] ?? WEEKDAY_KEYS[4])}
                </span>
              </span>
              <span className="flex items-center gap-3">
                {treat.dueToday ? (
                  <span className="rounded-md border border-accent px-2 py-0.5 text-xs text-accent">
                    {t("family.treatDueToday")}
                  </span>
                ) : null}
                <span className="text-sm text-text">{treat.amount.formatted}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          void add(event);
        }}
      >
        <Field
          id="treat-name"
          label={t("family.treatName")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id="treat-amount"
          label={t("family.amount")}
          inputMode="numeric"
          value={amount}
          onChange={(event) => {
            setAmount(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="treat-weekday" className="text-sm text-muted">
            {t("family.treatWeekday")}
          </label>
          <select
            id="treat-weekday"
            value={weekday}
            onChange={(event) => {
              setWeekday(Number(event.currentTarget.value));
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            {WEEKDAY_KEYS.map((key, index) => (
              <option key={key} value={index}>
                {t(key)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <PrimaryButton type="submit" disabled={name.trim() === "" || amount.trim() === ""}>
            {t("family.treatAdd")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
