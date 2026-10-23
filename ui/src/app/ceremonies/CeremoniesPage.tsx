import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, type SyntheticEvent, useCallback, useState } from "react";
import { CeremonyCouncilPage } from "./CeremonyCouncilPage";
import { useTranslation } from "react-i18next";
import {
  type CeremoniesDto,
  type CeremonyDto,
  type ScenarioDto,
  commands,
} from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { financeKeys } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";

const SELECT_CLASS =
  "h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent";
const KINDS = ["TOY", "BESHIK", "SUNNAT", "MARAKA", "OTHER"] as const;
const FUNDINGS = ["SAVINGS", "FAMILY", "EXPECTED_GIFTS", "DEBT"] as const;
type Kind = (typeof KINDS)[number];
type Funding = (typeof FUNDINGS)[number];

function kindKey(value: string) {
  switch (value) {
    case "TOY":
      return "ceremonies.kind.TOY" as const;
    case "BESHIK":
      return "ceremonies.kind.BESHIK" as const;
    case "SUNNAT":
      return "ceremonies.kind.SUNNAT" as const;
    case "MARAKA":
      return "ceremonies.kind.MARAKA" as const;
    default:
      return "ceremonies.kind.OTHER" as const;
  }
}

function fundingKey(value: string) {
  switch (value) {
    case "SAVINGS":
      return "ceremonies.funding.SAVINGS" as const;
    case "FAMILY":
      return "ceremonies.funding.FAMILY" as const;
    case "EXPECTED_GIFTS":
      return "ceremonies.funding.EXPECTED_GIFTS" as const;
    default:
      return "ceremonies.funding.DEBT" as const;
  }
}

/** Mutatsiya natijasini keshga yozadi; xatoni matnga aylantiradi. */
function useCeremonyAction() {
  const queryClient = useQueryClient();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(
    async (action: () => Promise<CeremoniesDto>): Promise<boolean> => {
      setError(null);
      try {
        queryClient.setQueryData(financeKeys.ceremonies, await action());
        return true;
      } catch (caught) {
        setError(message(caught));
        return false;
      }
    },
    [queryClient, message],
  );
  return { run, error };
}

/**
 * «Marosimlar» (SPEC 2D.8, D11): byudjet qatorlari manba bilan, 2–3 stsenariyni yonma-yon taqqoslash,
 * qarz manbasi bo'lsa «Buni qarzsiz qanday o'tkazamiz?» muhokamasi, to'yona o'rniga jamg'arma maqsadi, smeta PDF.
 * Barcha summalar backend'dan tayyor keladi.
 */
export function CeremoniesPage() {
  const { t } = useTranslation();
  const ceremonies = useQuery({
    queryKey: financeKeys.ceremonies,
    queryFn: () => commands.getCeremonies().then(unwrap),
  });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("nav.ceremonies")} subtitle={t("ceremonies.subtitle")} />
      <p className="rounded-lg border border-border bg-raised px-4 py-3 text-sm text-muted">
        {t("ceremonies.quote")}
      </p>
      {ceremonies.isError ? <Alert>{t("errors.generic")}</Alert> : null}
      {ceremonies.isSuccess ? (
        <>
          {ceremonies.data.items.length === 0 ? (
            <p className="text-sm text-muted">{t("ceremonies.empty")}</p>
          ) : null}
          {ceremonies.data.items.map((ceremony) => (
            <CeremonyCard key={ceremony.id} ceremony={ceremony} />
          ))}
          <CreateCeremonyCard />
        </>
      ) : null}
    </div>
  );
}

function CeremonyCard({ ceremony }: { ceremony: CeremonyDto }) {
  const { t } = useTranslation();
  const { run, error } = useCeremonyAction();
  const planned = ceremony.status === "PLANNED";
  const [councilOpen, setCouncilOpen] = useState(false);
  const [chosen, setChosen] = useState(ceremony.scenarios[0]?.id ?? "");
  const chosenId = ceremony.scenarios.some((s) => s.id === chosen)
    ? chosen
    : (ceremony.scenarios[0]?.id ?? "");

  const headline = [
    t(kindKey(ceremony.kind)),
    ceremony.eventOn ?? t("ceremonies.noDate"),
    planned ? t("ceremonies.status.PLANNED") : t("ceremonies.status.CONFIRMED"),
  ].join(" · ");

  return (
    <Card title={ceremony.title}>
      <p className="text-sm text-muted">{headline}</p>
      {ceremony.scenarios.length > 0 ? <ComparisonTable scenarios={ceremony.scenarios} /> : null}
      {ceremony.scenarios.map((scenario) => (
        <ScenarioBlock
          key={scenario.id}
          scenario={scenario}
          ceremonyId={ceremony.id}
          editable={planned}
          chosen={ceremony.chosenScenarioId === scenario.id}
        />
      ))}
      {planned ? <AddScenarioForm ceremonyId={ceremony.id} /> : null}

      {ceremony.hasDebt ? (
        <div className="flex flex-col gap-2 rounded-lg border border-warning/40 bg-app px-4 py-3">
          <p className="text-sm font-medium text-text">{t("ceremonies.debtQuestion")}</p>
          <p className="text-xs text-subtle">{t("ceremonies.debtHint")}</p>
          {ceremony.discussion !== null ? (
            <p className="text-sm text-text">
              {t("ceremonies.council.summaryLine", {
                scenario: ceremony.discussion.scenarioName,
                done: ceremony.discussion.adults.filter((a) => a.consented).length,
                total: ceremony.discussion.adults.length,
              })}{" "}
              <span className="text-muted">— {ceremony.discussion.note}</span>
            </p>
          ) : null}
          {ceremony.familyDiscussed ? (
            <p className="text-sm text-success">{t("ceremonies.discussed")}</p>
          ) : null}
          {planned ? (
            <div>
              <PrimaryButton
                onClick={() => {
                  setCouncilOpen(true);
                }}
              >
                {ceremony.discussion === null
                  ? t("ceremonies.council.open")
                  : t("ceremonies.council.continue")}
              </PrimaryButton>
            </div>
          ) : null}
        </div>
      ) : null}
      {councilOpen ? (
        <CeremonyCouncilPage
          ceremony={ceremony}
          onClose={() => {
            setCouncilOpen(false);
          }}
        />
      ) : null}

      {planned && ceremony.scenarios.length > 0 ? (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
            event.preventDefault();
            void run(() =>
              commands.confirmCeremony({ id: ceremony.id, scenarioId: chosenId }).then(unwrap),
            );
          }}
        >
          <div className="flex flex-col gap-2">
            <label htmlFor={`choose-${ceremony.id}`} className="text-sm text-muted">
              {t("ceremonies.chooseScenario")}
            </label>
            <select
              id={`choose-${ceremony.id}`}
              className={SELECT_CLASS}
              value={chosenId}
              onChange={(event) => {
                setChosen(event.currentTarget.value);
              }}
            >
              {ceremony.scenarios.map((scenario) => (
                <option key={scenario.id} value={scenario.id}>
                  {scenario.name}
                </option>
              ))}
            </select>
          </div>
          <PrimaryButton type="submit">{t("ceremonies.confirm")}</PrimaryButton>
        </form>
      ) : null}
      {!planned ? <p className="text-sm text-success">{t("ceremonies.confirmedNote")}</p> : null}

      <GoalForm ceremony={ceremony} />
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

/** Stsenariylar yonma-yon: qatorlar — ko'rsatkich, ustunlar — stsenariy. */
export function ComparisonTable({ scenarios }: { scenarios: ScenarioDto[] }) {
  const { t } = useTranslation();
  const rows: { label: string; cell: (s: ScenarioDto) => string }[] = [
    {
      label: t("ceremonies.cmp.size"),
      cell: (s) => t("ceremonies.sizeLine", { days: s.days, guests: s.guests }),
    },
    { label: t("ceremonies.cmp.total"), cell: (s) => s.total.formatted },
    { label: t("ceremonies.cmp.debt"), cell: (s) => s.debtPart.formatted },
    {
      label: t("ceremonies.cmp.payoff"),
      cell: (s) =>
        s.payoffMonths === null
          ? s.hasDebt
            ? t("ceremonies.noIncomeData")
            : "—"
          : t("ceremonies.monthsValue", { months: s.payoffMonths }),
    },
    {
      label: t("ceremonies.cmp.alternative"),
      cell: (s) =>
        s.monthsOfNeeds === null
          ? t("ceremonies.noNeedsData")
          : t("ceremonies.monthsOfNeeds", { months: s.monthsOfNeeds }),
    },
  ];
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm" aria-label={t("ceremonies.cmp.title")}>
        <thead className="bg-raised text-left text-xs text-subtle">
          <tr>
            <th className="px-3 py-2">{t("ceremonies.cmp.title")}</th>
            {scenarios.map((s) => (
              <th key={s.id} className="px-3 py-2 text-text">
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-t border-border">
              <th scope="row" className="px-3 py-2 text-left font-normal text-muted">
                {row.label}
              </th>
              {scenarios.map((s) => (
                <td key={s.id} className="px-3 py-2 text-text">
                  {row.cell(s)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScenarioBlock({
  scenario,
  ceremonyId,
  editable,
  chosen,
}: {
  scenario: ScenarioDto;
  ceremonyId: string;
  editable: boolean;
  chosen: boolean;
}) {
  const { t } = useTranslation();
  const { run, error } = useCeremonyAction();
  const message = useErrorMessage();
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState("");
  const [funding, setFunding] = useState<Funding>("SAVINGS");
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  async function addLine(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await run(() =>
      commands
        .addCeremonyLine({
          scenarioId: scenario.id,
          name,
          quantity: Number(quantity),
          unitPrice: price,
          funding,
        })
        .then(unwrap),
    );
    if (ok) {
      setName("");
      setQuantity("1");
      setPrice("");
    }
  }

  async function createPdf() {
    setPdfError(null);
    try {
      setPdfPath(unwrap(await commands.createCeremonyPdf(ceremonyId, scenario.id)));
    } catch (caught) {
      setPdfError(message(caught));
    }
  }

  return (
    <section
      aria-label={scenario.name}
      className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-text">
          {scenario.name}
          {chosen ? ` · ${t("ceremonies.chosen")}` : ""}
        </h3>
        <span className="text-sm text-muted">
          {t("ceremonies.sizeLine", { days: scenario.days, guests: scenario.guests })}
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat label={t("ceremonies.cmp.total")} value={scenario.total.formatted} />
        <Stat label={t("ceremonies.funding.SAVINGS")} value={scenario.savingsPart.formatted} />
        <Stat label={t("ceremonies.funding.DEBT")} value={scenario.debtPart.formatted} />
      </div>
      {scenario.lines.length === 0 ? (
        <p className="text-sm text-muted">{t("ceremonies.noLines")}</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {scenario.lines.map((line) => (
            <li
              key={line.id}
              className="flex flex-wrap items-center justify-between gap-2 text-sm text-text"
            >
              <span>
                {line.name} · {line.quantity} × {line.unitPrice.formatted} ·{" "}
                <span className={line.funding === "DEBT" ? "text-warning" : "text-muted"}>
                  {t(fundingKey(line.funding))}
                </span>
              </span>
              <span className="flex items-center gap-2">
                <span className="font-medium">{line.total.formatted}</span>
                {editable ? (
                  <SecondaryButton
                    className="h-8 px-2 text-xs"
                    aria-label={t("ceremonies.removeLine", { name: line.name })}
                    onClick={() => {
                      void run(() => commands.removeCeremonyLine(line.id).then(unwrap));
                    }}
                  >
                    {t("ceremonies.remove")}
                  </SecondaryButton>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
      {editable ? (
        <form
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
          onSubmit={(event) => void addLine(event)}
        >
          <Field
            id={`line-name-${scenario.id}`}
            label={t("ceremonies.lineName")}
            value={name}
            onChange={(event) => {
              setName(event.currentTarget.value);
            }}
          />
          <Field
            id={`line-qty-${scenario.id}`}
            label={t("ceremonies.lineQuantity")}
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => {
              setQuantity(event.currentTarget.value);
            }}
          />
          <Field
            id={`line-price-${scenario.id}`}
            label={t("ceremonies.linePrice")}
            inputMode="numeric"
            value={price}
            onChange={(event) => {
              setPrice(event.currentTarget.value);
            }}
          />
          <div className="flex flex-col gap-2">
            <label htmlFor={`line-funding-${scenario.id}`} className="text-sm text-muted">
              {t("ceremonies.lineFunding")}
            </label>
            <select
              id={`line-funding-${scenario.id}`}
              className={SELECT_CLASS}
              value={funding}
              onChange={(event) => {
                const value = event.currentTarget.value;
                setFunding(FUNDINGS.find((f) => f === value) ?? "SAVINGS");
              }}
            >
              {FUNDINGS.map((f) => (
                <option key={f} value={f}>
                  {t(fundingKey(f))}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <PrimaryButton
              type="submit"
              disabled={name.trim() === "" || price.trim() === "" || Number(quantity) <= 0}
            >
              {t("ceremonies.addLine")}
            </PrimaryButton>
          </div>
        </form>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <SecondaryButton
          disabled={scenario.lines.length === 0}
          onClick={() => {
            void createPdf();
          }}
        >
          {t("ceremonies.pdf")}
        </SecondaryButton>
        {pdfPath !== null ? (
          <span className="text-xs text-subtle">{t("ceremonies.pdfSaved", { path: pdfPath })}</span>
        ) : null}
      </div>
      {error !== null ? <Alert>{error}</Alert> : null}
      {pdfError !== null ? <Alert>{pdfError}</Alert> : null}
    </section>
  );
}

function AddScenarioForm({ ceremonyId }: { ceremonyId: string }) {
  const { t } = useTranslation();
  const { run, error } = useCeremonyAction();
  const [name, setName] = useState("");
  const [guests, setGuests] = useState("100");
  const [days, setDays] = useState("1");

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await run(() =>
      commands
        .addCeremonyScenario({
          ceremonyId,
          name,
          guests: Number(guests),
          days: Number(days),
        })
        .then(unwrap),
    );
    if (ok) {
      setName("");
    }
  }

  return (
    <FormRow title={t("ceremonies.newScenario")} error={error}>
      <form
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        onSubmit={(event) => void add(event)}
      >
        <Field
          id={`scenario-name-${ceremonyId}`}
          label={t("ceremonies.scenarioName")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id={`scenario-guests-${ceremonyId}`}
          label={t("ceremonies.guests")}
          type="number"
          min={0}
          value={guests}
          onChange={(event) => {
            setGuests(event.currentTarget.value);
          }}
        />
        <Field
          id={`scenario-days-${ceremonyId}`}
          label={t("ceremonies.days")}
          type="number"
          min={1}
          value={days}
          onChange={(event) => {
            setDays(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={name.trim() === "" || Number(days) <= 0}>
            {t("ceremonies.addScenario")}
          </PrimaryButton>
        </div>
      </form>
    </FormRow>
  );
}

function GoalForm({ ceremony }: { ceremony: CeremonyDto }) {
  const { t } = useTranslation();
  const { run, error } = useCeremonyAction();
  const [name, setName] = useState(ceremony.goalName ?? "");
  const [target, setTarget] = useState("");

  return (
    <FormRow title={t("ceremonies.goalTitle")} error={error}>
      <p className="text-xs text-subtle">{t("ceremonies.goalHint")}</p>
      {ceremony.goalName !== null && ceremony.goalTarget !== null ? (
        <p className="text-sm text-text">
          {t("ceremonies.goalLine", {
            name: ceremony.goalName,
            amount: ceremony.goalTarget.formatted,
          })}
        </p>
      ) : null}
      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
        onSubmit={(event: SyntheticEvent<HTMLFormElement>) => {
          event.preventDefault();
          void run(() =>
            commands.setCeremonyGoal({ id: ceremony.id, name, target }).then(unwrap),
          ).then((ok) => {
            if (ok) {
              setTarget("");
            }
          });
        }}
      >
        <Field
          id={`goal-name-${ceremony.id}`}
          label={t("ceremonies.goalName")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <Field
          id={`goal-target-${ceremony.id}`}
          label={t("ceremonies.goalTarget")}
          inputMode="numeric"
          value={target}
          onChange={(event) => {
            setTarget(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={name.trim() === "" || target.trim() === ""}>
            {t("ceremonies.saveGoal")}
          </PrimaryButton>
        </div>
      </form>
    </FormRow>
  );
}

function FormRow({
  title,
  error,
  children,
}: {
  title: string;
  error: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3">
      <h3 className="text-sm font-medium text-text">{title}</h3>
      {children}
      {error !== null ? <Alert>{error}</Alert> : null}
    </div>
  );
}

function CreateCeremonyCard() {
  const { t } = useTranslation();
  const { run, error } = useCeremonyAction();
  const [kind, setKind] = useState<Kind>("TOY");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");

  async function create(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const ok = await run(() =>
      commands
        .createCeremony({ kind, title, eventOn: date.trim() === "" ? null : date })
        .then(unwrap),
    );
    if (ok) {
      setTitle("");
      setDate("");
    }
  }

  return (
    <Card title={t("ceremonies.newTitle")}>
      <form
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        onSubmit={(event) => void create(event)}
      >
        <div className="flex flex-col gap-2">
          <label htmlFor="ceremony-kind" className="text-sm text-muted">
            {t("ceremonies.kindLabel")}
          </label>
          <select
            id="ceremony-kind"
            className={SELECT_CLASS}
            value={kind}
            onChange={(event) => {
              const value = event.currentTarget.value;
              setKind(KINDS.find((k) => k === value) ?? "TOY");
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
          id="ceremony-title"
          label={t("ceremonies.titleLabel")}
          value={title}
          onChange={(event) => {
            setTitle(event.currentTarget.value);
          }}
        />
        <Field
          id="ceremony-date"
          label={t("ceremonies.dateLabel")}
          type="date"
          value={date}
          onChange={(event) => {
            setDate(event.currentTarget.value);
          }}
        />
        <div className="flex items-end">
          <PrimaryButton type="submit" disabled={title.trim() === ""}>
            {t("ceremonies.create")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}
