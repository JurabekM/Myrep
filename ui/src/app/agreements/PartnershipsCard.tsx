import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { type PartnershipDto, type PartnershipsDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { errorKey, useErrorMessage } from "../finance/errors";
import { Alert, Card, Field, PrimaryButton, SecondaryButton, Stat } from "../finance/ui";
import { agreementKeys } from "./queries";
import { VentureCard } from "./VentureCard";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const KINDS = ["MUDARABA", "MUSHARAKA"] as const;
const ROLES = ["WORKER", "CAPITAL_PROVIDER"] as const;

function kindKey(value: string) {
  return value === "MUSHARAKA"
    ? ("partnerships.kind.MUSHARAKA" as const)
    : ("partnerships.kind.MUDARABA" as const);
}

function roleKey(value: string) {
  return value === "CAPITAL_PROVIDER"
    ? ("partnerships.role.CAPITAL_PROVIDER" as const)
    : ("partnerships.role.WORKER" as const);
}

/** bp → «66,7 %». */
export function shareText(bp: number): string {
  return `${String(Math.floor(bp / 100))},${String(Math.floor((bp % 100) / 10))} %`;
}

function usePartnershipAction() {
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(
    async (action: () => Promise<PartnershipsDto>): Promise<PartnershipsDto | null> => {
      setError(null);
      try {
        const next = await action();
        queryClient.setQueryData(agreementKeys.partnerships, next);
        await queryClient.invalidateQueries({ queryKey: agreementKeys.list });
        return next;
      } catch (caught) {
        setError(message(caught));
        return null;
      }
    },
    [queryClient, message],
  );
  return { run, error };
}

/**
 * Sheriklik (SPEC 2E.1, 2E.2, 2E.6, D12): `PARTNERSHIP` kelishuvi ustiga tur, rol, tayyorgarlik darvozasi
 * (faqat kapital kirituvchiga), kapital qabul qilishda oilaviy rozilik, kamayib boruvchi sheriklik (buyout).
 * Hisob va qoidalar Rustda; bu yerda faqat ko'rsatish.
 */
export function PartnershipsCard({ onOpen }: { onOpen: (agreementId: string) => void }) {
  const { t } = useTranslation();
  const partnerships = useQuery({
    queryKey: agreementKeys.partnerships,
    queryFn: () => commands.getPartnerships().then(unwrap),
  });

  return (
    <Card title={t("partnerships.title")}>
      <p className="text-sm text-muted">{t("partnerships.intro")}</p>
      {partnerships.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {partnerships.isSuccess ? (
        <>
          <p className="text-xs text-subtle">
            {partnerships.data.gate === "OPEN"
              ? t("partnerships.gateOpen")
              : t("partnerships.gateLocked")}
          </p>
          {partnerships.data.items.length === 0 ? (
            <p className="text-sm text-muted">{t("partnerships.empty")}</p>
          ) : null}
          {partnerships.data.items.map((item) => (
            <PartnershipBlock key={item.id} item={item} onOpen={onOpen} />
          ))}
          <CreateForm onCreated={onOpen} />
        </>
      ) : null}
    </Card>
  );
}

function PartnershipBlock({
  item,
  onOpen,
}: {
  item: PartnershipDto;
  onOpen: (agreementId: string) => void;
}) {
  const { t } = useTranslation();
  const { run, error } = usePartnershipAction();
  const [member, setMember] = useState("");
  const [total, setTotal] = useState("");
  const [months, setMonths] = useState("12");
  const [start, setStart] = useState("");
  const [payment, setPayment] = useState("");

  return (
    <section
      aria-label={item.title}
      className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-text">{item.title}</h3>
        <span className="text-sm text-muted">
          {t(kindKey(item.kind))} · {t(roleKey(item.myRole))} · {item.status} ·{" "}
          {t("agreements.version", { version: item.version })}
        </span>
      </div>
      {item.parties.length > 0 ? (
        <ul className="flex flex-col gap-1 text-sm text-text">
          {item.parties.map((party) => (
            <li key={party.partyId}>
              {party.name} · {party.role} · {party.capital.formatted} · {shareText(party.shareBp)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{t("partnerships.noParties")}</p>
      )}
      {item.issues.length > 0 ? (
        <ul className="flex flex-col gap-1 text-xs text-warning">
          {item.issues.map((code) => (
            <li key={code}>{t(errorKey(code))}</li>
          ))}
        </ul>
      ) : null}

      {item.myRole === "WORKER" ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-subtle">{t("partnerships.consentHint")}</p>
          {item.consentMember !== null ? (
            <p className="text-sm text-success">
              {t("partnerships.consentLine", {
                name: item.consentMember,
                date: item.consentAt ?? "",
              })}
            </p>
          ) : (
            <form
              className="flex flex-wrap items-end gap-2"
              onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
                event.preventDefault();
                void run(() =>
                  commands.consentPartnership({ id: item.id, memberName: member }).then(unwrap),
                );
              }}
            >
              <div className="w-56">
                <Field
                  id={`consent-${item.id}`}
                  label={t("partnerships.consentMember")}
                  value={member}
                  onChange={(event) => {
                    setMember(event.currentTarget.value);
                  }}
                />
              </div>
              <PrimaryButton type="submit" disabled={member.trim() === ""}>
                {t("partnerships.consent")}
              </PrimaryButton>
            </form>
          )}
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <h4 className="text-sm font-medium text-text">{t("partnerships.buyoutTitle")}</h4>
        <p className="text-xs text-subtle">{t("partnerships.buyoutHint")}</p>
        {item.buyout === null ? (
          <form
            className="grid gap-3 sm:grid-cols-4"
            onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
              event.preventDefault();
              void run(() =>
                commands
                  .setBuyout({ id: item.id, total, months: Number(months), startOn: start })
                  .then(unwrap),
              );
            }}
          >
            <Field
              id={`buyout-total-${item.id}`}
              label={t("partnerships.buyoutTotal")}
              inputMode="numeric"
              value={total}
              onChange={(event) => {
                setTotal(event.currentTarget.value);
              }}
            />
            <Field
              id={`buyout-months-${item.id}`}
              label={t("partnerships.buyoutMonths")}
              type="number"
              min={1}
              max={240}
              value={months}
              onChange={(event) => {
                setMonths(event.currentTarget.value);
              }}
            />
            <Field
              id={`buyout-start-${item.id}`}
              label={t("partnerships.buyoutStart")}
              type="date"
              value={start}
              onChange={(event) => {
                setStart(event.currentTarget.value);
              }}
            />
            <div className="flex items-end">
              <PrimaryButton
                type="submit"
                disabled={total.trim() === "" || start === "" || Number(months) <= 0}
              >
                {t("partnerships.buyoutSave")}
              </PrimaryButton>
            </div>
          </form>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label={t("partnerships.buyoutTotal")} value={item.buyout.total.formatted} />
              <Stat label={t("partnerships.buyoutPaid")} value={item.buyout.paid.formatted} />
              <Stat
                label={t("partnerships.remainingShare")}
                value={shareText(item.buyout.remainingShareBp)}
                hint={t("partnerships.remainingHint", { amount: item.buyout.remaining.formatted })}
              />
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded bg-raised"
              role="progressbar"
              aria-label={t("partnerships.remainingShare")}
              aria-valuemin={0}
              aria-valuemax={10000}
              aria-valuenow={10000 - item.buyout.remainingShareBp}
            >
              <div
                className="h-full bg-accent"
                style={{ width: `${String((10000 - item.buyout.remainingShareBp) / 100)}%` }}
              />
            </div>
            <div className="max-h-56 overflow-auto rounded-lg border border-border">
              <table className="w-full text-sm" aria-label={t("partnerships.buyoutTitle")}>
                <thead className="sticky top-0 bg-raised text-left text-xs text-subtle">
                  <tr>
                    <th className="px-3 py-2">№</th>
                    <th className="px-3 py-2">{t("partnerships.colDate")}</th>
                    <th className="px-3 py-2">{t("partnerships.colAmount")}</th>
                    <th className="px-3 py-2">{t("partnerships.colRemaining")}</th>
                    <th className="px-3 py-2">{t("partnerships.colPaid")}</th>
                  </tr>
                </thead>
                <tbody>
                  {item.buyout.rows.map((row) => (
                    <tr key={row.seq} className="border-t border-border text-text">
                      <td className="px-3 py-2">{row.seq}</td>
                      <td className="px-3 py-2">{row.dueOn}</td>
                      <td className="px-3 py-2">{row.amount.formatted}</td>
                      <td className="px-3 py-2">{shareText(row.remainingShareBp)}</td>
                      <td className="px-3 py-2">{row.paid ? "✓" : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {item.buyout.remainingShareBp > 0 ? (
              <form
                className="flex flex-wrap items-end gap-2"
                onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
                  event.preventDefault();
                  void run(() =>
                    commands.payBuyout({ id: item.id, amount: payment, paidOn: null }).then(unwrap),
                  ).then((next) => {
                    if (next !== null) {
                      setPayment("");
                    }
                  });
                }}
              >
                <div className="w-44">
                  <Field
                    id={`buyout-pay-${item.id}`}
                    label={t("partnerships.payAmount")}
                    inputMode="numeric"
                    value={payment}
                    onChange={(event) => {
                      setPayment(event.currentTarget.value);
                    }}
                  />
                </div>
                <PrimaryButton type="submit" disabled={payment.trim() === ""}>
                  {t("partnerships.pay")}
                </PrimaryButton>
              </form>
            ) : (
              <p className="text-sm text-success">{t("partnerships.buyoutDone")}</p>
            )}
          </>
        )}
      </div>

      {item.status === "SIGNED" ? <VentureCard partnership={item} /> : null}

      <div>
        <SecondaryButton
          onClick={() => {
            onOpen(item.agreementId);
          }}
        >
          {t("partnerships.openContract")}
        </SecondaryButton>
      </div>
      {error !== null ? <Alert>{error}</Alert> : null}
    </section>
  );
}

function CreateForm({ onCreated }: { onCreated: (agreementId: string) => void }) {
  const { t } = useTranslation();
  const { run, error } = usePartnershipAction();
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<(typeof KINDS)[number]>("MUDARABA");
  const [role, setRole] = useState<(typeof ROLES)[number]>("WORKER");

  async function create(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = await run(() =>
      commands.createPartnership({ title, kind, myRole: role }).then(unwrap),
    );
    if (next !== null) {
      setTitle("");
      const created = next.items[next.items.length - 1];
      if (created !== undefined) {
        onCreated(created.agreementId);
      }
    }
  }

  return (
    <form
      className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3"
      onSubmit={(event) => void create(event)}
    >
      <h3 className="text-sm font-medium text-text">{t("partnerships.newTitle")}</h3>
      <div className="grid gap-3 sm:grid-cols-4">
        <Field
          id="partnership-title"
          label={t("partnerships.titleLabel")}
          value={title}
          onChange={(event) => {
            setTitle(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="partnership-kind" className="text-sm text-muted">
            {t("partnerships.kindLabel")}
          </label>
          <select
            id="partnership-kind"
            className={SELECT_CLASS}
            value={kind}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setKind(KINDS.find((k) => k === value) ?? "MUDARABA");
            }}
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t(kindKey(k))}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="partnership-role" className="text-sm text-muted">
            {t("partnerships.roleLabel")}
          </label>
          <select
            id="partnership-role"
            className={SELECT_CLASS}
            value={role}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setRole(ROLES.find((r) => r === value) ?? "WORKER");
            }}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(roleKey(r))}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={title.trim() === ""}>
            {t("partnerships.create")}
          </PrimaryButton>
        </div>
      </div>
      <p className="text-xs text-subtle">
        {role === "CAPITAL_PROVIDER"
          ? t("partnerships.roleCapitalHint")
          : t("partnerships.roleWorkerHint")}
      </p>
      {error !== null ? <Alert>{error}</Alert> : null}
    </form>
  );
}
