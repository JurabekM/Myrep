import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { type BudgetDto, type SubscriptionDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, SecondaryButton } from "../finance/ui";
import { useApplyBudget } from "./queries";

/**
 * Obunalar: «ishlatdim» belgilash, bekor qilish va yangisini qo'shish.
 * Hech narsa avtomatik bekor qilinmaydi; «unutilgan» faqat eslatma.
 */
export function SubscriptionsCard({ subscriptions }: { subscriptions: SubscriptionDto[] }) {
  const { t } = useTranslation();
  const apply = useApplyBudget();
  const message = useErrorMessage();
  const [name, setName] = useState("");
  const [monthly, setMonthly] = useState("");
  const [yearly, setYearly] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<BudgetDto>, onDone?: () => void) {
    setError(null);
    try {
      await apply(await action());
      onDone?.();
    } catch (caught) {
      setError(message(caught));
    }
  }

  function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(
      () =>
        commands
          .addSubscription({
            name,
            monthly,
            yearly: yearly.trim() === "" ? null : yearly,
          })
          .then(unwrap),
      () => {
        setName("");
        setMonthly("");
        setYearly("");
      },
    );
  }

  return (
    <Card title={t("budget.subscriptionsTitle")}>
      {subscriptions.length === 0 ? (
        <p className="text-sm text-muted">{t("budget.subscriptionEmpty")}</p>
      ) : null}
      {subscriptions.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {subscriptions.map((sub) => {
            const cancelled = sub.cancelledOn !== null;
            return (
              <li
                key={sub.id}
                className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-sm text-text">{sub.name}</span>
                  <span className="text-xs text-subtle">
                    {cancelled
                      ? t("budget.cancelledOn", { date: sub.cancelledOn ?? "" })
                      : t("budget.active")}
                    {sub.lastUsedOn !== null
                      ? ` · ${t("budget.lastUsed", { date: sub.lastUsedOn })}`
                      : null}
                  </span>
                  {sub.forgotten ? (
                    <span className="text-xs text-accent">{t("budget.forgotten")}</span>
                  ) : null}
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-text">{sub.monthly.formatted}</span>
                  {cancelled ? null : (
                    <>
                      <SecondaryButton
                        onClick={() => {
                          void run(() => commands.markSubscriptionUsed(sub.id).then(unwrap));
                        }}
                      >
                        {t("budget.markUsed")}
                      </SecondaryButton>
                      <SecondaryButton
                        onClick={() => {
                          void run(() => commands.cancelSubscription(sub.id).then(unwrap));
                        }}
                      >
                        {t("budget.cancel")}
                      </SecondaryButton>
                    </>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}

      <form className="flex flex-col gap-4" onSubmit={add}>
        <Field
          id="sub-name"
          label={t("budget.name")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id="sub-monthly"
          label={t("budget.monthly")}
          inputMode="numeric"
          value={monthly}
          onChange={(event) => {
            setMonthly(event.currentTarget.value);
          }}
        />
        <Field
          id="sub-yearly"
          label={t("budget.yearly")}
          inputMode="numeric"
          value={yearly}
          onChange={(event) => {
            setYearly(event.currentTarget.value);
          }}
        />
        <div>
          <PrimaryButton type="submit" disabled={name.trim() === "" || monthly.trim() === ""}>
            {t("budget.addSubscription")}
          </PrimaryButton>
        </div>
      </form>

      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
