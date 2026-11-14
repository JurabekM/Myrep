import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PageHeader, PrimaryButton } from "../finance/ui";
import { AgreementWizard } from "./AgreementWizard";
import { CenterTable } from "./CenterTable";
import { FamilyTemplatesCard } from "./FamilyTemplatesCard";
import { HustleCard } from "./HustleCard";
import { OfferCheckCard } from "./OfferCheckCard";
import { PyramidCard } from "./PyramidCard";
import { PartnershipsCard } from "./PartnershipsCard";
import { kindKey } from "./labels";
import { agreementKeys, useApplyAgreement } from "./queries";

const KINDS = ["PARTNERSHIP", "LOAN", "FAMILY", "OTHER"] as const;
const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";

/** Kelishuvlar: ro'yxat, yangi qoralama, usta. (D13A da jadval, filtr va ko'riklar qo'shiladi.) */
export function AgreementsPage() {
  const { t } = useTranslation();
  const apply = useApplyAgreement();
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [open, setOpen] = useState<string | null>(null);
  const [kind, setKind] = useState<(typeof KINDS)[number]>("PARTNERSHIP");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  /** «Hunardan ishga» natijasidan sheriklik qoralamasi (mehnat egasi sifatida). */
  async function createPartnershipDraft(draftTitle: string) {
    setError(null);
    try {
      const next = unwrap(
        await commands.createPartnership({
          title: draftTitle,
          kind: "MUDARABA",
          myRole: "WORKER",
          gateOverride: null,
        }),
      );
      await queryClient.invalidateQueries({ queryKey: agreementKeys.partnerships });
      const created = next.items[next.items.length - 1];
      if (created !== undefined) {
        setOpen(created.agreementId);
      }
    } catch (caught) {
      setError(message(caught));
    }
  }

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

      <HustleCard
        onDraft={(draftTitle) => {
          void createPartnershipDraft(draftTitle);
        }}
      />

      <OfferCheckCard />

      <PyramidCard />

      <CenterTable
        onOpen={(id) => {
          setOpen(id);
        }}
      />

      <FamilyTemplatesCard
        onCreated={(id) => {
          setOpen(id);
        }}
      />

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
