import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PageHeader, PrimaryButton, SecondaryButton } from "../finance/ui";
import { AgreementWizard } from "./AgreementWizard";
import { PartnershipsCard } from "./PartnershipsCard";
import { kindKey, statusKey } from "./labels";
import { agreementFetchers, agreementKeys, useApplyAgreement } from "./queries";

const KINDS = ["PARTNERSHIP", "LOAN", "FAMILY", "OTHER"] as const;
const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

/** Kelishuvlar: ro'yxat, yangi qoralama, usta. (D13A da jadval, filtr va ko'riklar qo'shiladi.) */
export function AgreementsPage() {
  const { t } = useTranslation();
  const apply = useApplyAgreement();
  const message = useErrorMessage();
  const list = useQuery({ queryKey: agreementKeys.list, queryFn: agreementFetchers.list });
  const [open, setOpen] = useState<string | null>(null);
  const [kind, setKind] = useState<(typeof KINDS)[number]>("PARTNERSHIP");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function create(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const created = unwrap(await commands.createAgreement({ kind, title }));
      await apply(created);
      setTitle("");
      setOpen(created.id);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("agreements.title")} subtitle={t("agreements.subtitle")} />

      <PartnershipsCard
        onOpen={(agreementId) => {
          setOpen(agreementId);
        }}
      />

      <Card title={t("agreements.listTitle")}>
        {list.isSuccess && list.data.length === 0 ? (
          <p className="text-sm text-muted">{t("agreements.empty")}</p>
        ) : null}
        {list.isSuccess && list.data.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {list.data.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-app px-4 py-3"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-sm text-text">{item.title}</span>
                  <span className="text-xs text-subtle">
                    {t(kindKey(item.kind))} · {t(statusKey(item.status))} ·{" "}
                    {t("agreements.answeredShort", { done: item.answered })}
                    {item.reviewDate !== null
                      ? ` · ${t("agreements.reviewOn", { date: item.reviewDate })}`
                      : ""}
                  </span>
                </span>
                <SecondaryButton
                  onClick={() => {
                    setOpen(item.id);
                  }}
                >
                  {t("agreements.open")}
                </SecondaryButton>
              </li>
            ))}
          </ul>
        ) : null}
        {list.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      </Card>

      <Card title={t("agreements.newTitle")}>
        <form className="flex flex-col gap-4" onSubmit={(event) => void create(event)}>
          <div className="flex flex-col gap-2">
            <label htmlFor="agreement-kind" className="text-sm text-muted">
              {t("agreements.kindLabel")}
            </label>
            <select
              id="agreement-kind"
              className={SELECT_CLASS}
              value={kind}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setKind(KINDS.find((k) => k === value) ?? "PARTNERSHIP");
              }}
            >
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(kindKey(k))}
                </option>
              ))}
            </select>
          </div>
          <Field
            id="agreement-title-input"
            label={t("agreements.titleLabel")}
            value={title}
            onChange={(event) => {
              setTitle(event.currentTarget.value);
            }}
          />
          <div>
            <PrimaryButton type="submit" disabled={title.trim() === ""}>
              {t("agreements.create")}
            </PrimaryButton>
          </div>
        </form>
        {error !== null ? <Alert>{error}</Alert> : null}
      </Card>

      {open !== null ? (
        <AgreementWizard
          id={open}
          onClose={() => {
            setOpen(null);
          }}
        />
      ) : null}
    </div>
  );
}
