import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, SecondaryButton } from "../finance/ui";
import { agreementKeys, useApplyAgreement } from "./queries";

/**
 * Oilaviy kelishuvlar (SPEC 2F.10, D13A): 4 shablon — yengil format, guvoh va hakam ixtiyoriy,
 * imzo o'rniga ADULT a'zolarning PIN tasdig'i. Ohang: odob va hurmat, nazoratsiz.
 */
export function FamilyTemplatesCard({ onCreated }: { onCreated: (id: string) => void }) {
  const { t } = useTranslation();
  const apply = useApplyAgreement();
  const message = useErrorMessage();
  const templates = useQuery({
    queryKey: agreementKeys.familyTemplates,
    queryFn: () => commands.listFamilyTemplates().then(unwrap),
  });
  const [error, setError] = useState<string | null>(null);

  async function create(templateId: string) {
    setError(null);
    try {
      const created = unwrap(await commands.createFamilyAgreement(templateId));
      await apply(created);
      onCreated(created.id);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("familyAgreements.title")}>
      <p className="text-sm text-muted">{t("familyAgreements.intro")}</p>
      {templates.isSuccess ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {templates.data.map((template) => (
            <li
              key={template.id}
              className="flex flex-col gap-2 rounded-lg border border-border bg-app px-4 py-3"
            >
              <span className="text-sm font-medium text-text">{template.title}</span>
              <span className="text-xs text-subtle">{template.description}</span>
              <div>
                <SecondaryButton
                  onClick={() => {
                    void create(template.id);
                  }}
                >
                  {t("familyAgreements.create")}
                </SecondaryButton>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
