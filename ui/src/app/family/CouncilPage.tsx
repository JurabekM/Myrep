import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AdultConsentDto, CategoryDto, HavasLimitDto } from "../../bindings/bindings";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { fetchers, financeKeys } from "../finance/queries";
import { useErrorMessage } from "../finance/errors";
import {
  Alert,
  Card,
  Field,
  PrimaryButton,
  PageHeader,
  SecondaryButton,
  Stat,
} from "../finance/ui";
import { necessityKey, NECESSITY_CODES } from "./necessity";
import { familyFetchers, familyKeys, sanitizePin, useInvalidateFamily } from "./queries";

type Step = "review" | "categories" | "limit" | "summary";

const STEPS: readonly Step[] = ["review", "categories", "limit", "summary"];

const STEP_KEYS = {
  review: "family.steps.review",
  categories: "family.steps.categories",
  limit: "family.steps.limit",
  summary: "family.steps.summary",
} as const;

/**
 * Oila kengashi rejimi (DESKTOP_PROMPT 7): to'liq ekran, yirik shrift, qadamlar.
 * Oyni ko'rib chiqish → toifalarni kelishish → havas chegarasi (har bir katta o'z PIN'i bilan) → yakun.
 * Hisob-kitob backend'da; bu yerda faqat ko'rsatiladi va buyruqlar yuboriladi.
 */
export function CouncilPage({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>("review");
  const index = STEPS.indexOf(step);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("family.council")}
      className="fixed inset-0 z-50 overflow-y-auto bg-app p-8"
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <PageHeader title={t("family.council")} subtitle={t("family.councilSubtitle")} />
          <SecondaryButton onClick={onClose}>{t("family.close")}</SecondaryButton>
        </header>

        <ol className="flex flex-wrap gap-2 text-sm">
          {STEPS.map((key, position) => (
            <li
              key={key}
              aria-current={key === step ? "step" : undefined}
              className={
                key === step
                  ? "rounded-md border border-accent px-3 py-1 text-text"
                  : "rounded-md border border-border px-3 py-1 text-muted"
              }
            >
              {position + 1}. {t(STEP_KEYS[key])}
            </li>
          ))}
        </ol>

        {step === "review" ? <ReviewStep /> : null}
        {step === "categories" ? <CategoriesStep /> : null}
        {step === "limit" ? <LimitStep /> : null}
        {step === "summary" ? <SummaryStep onFinish={onClose} /> : null}

        <footer className="flex flex-wrap gap-2">
          {index > 0 ? (
            <SecondaryButton
              onClick={() => {
                setStep(STEPS[index - 1] ?? "review");
              }}
            >
              {t("family.back")}
            </SecondaryButton>
          ) : null}
          {index < STEPS.length - 1 ? (
            <PrimaryButton
              onClick={() => {
                setStep(STEPS[index + 1] ?? "summary");
              }}
            >
              {t("family.next")}
            </PrimaryButton>
          ) : null}
        </footer>
      </div>
    </div>
  );
}

function ReviewStep() {
  const { t } = useTranslation();
  const summary = useQuery({ queryKey: familyKeys.summary, queryFn: familyFetchers.summary });
  if (summary.isPending) {
    return <p className="text-sm text-muted">{t("common.loading")}</p>;
  }
  if (summary.isError) {
    return <Alert>{t("errors.generic")}</Alert>;
  }
  const data = summary.data;
  return (
    <Card title={t("family.summary")}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat label={t("family.zarur")} value={data.zarur.formatted} />
        <Stat label={t("family.kerak")} value={data.kerak.formatted} />
        <Stat label={t("family.havas")} value={data.havas.formatted} hint={t("family.havasHint")} />
        <Stat
          label={t("family.sadaqa")}
          value={data.sadaqa.formatted}
          hint={t("family.sadaqaHint")}
        />
        <Stat
          label={t("family.flagGift")}
          value={data.gifts.formatted}
          hint={t("family.giftsHint")}
        />
        <Stat label={t("family.flagOstentation")} value={data.ostentation.formatted} />
      </div>
    </Card>
  );
}

function CategoriesStep() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const categories = useQuery({ queryKey: financeKeys.categories, queryFn: fetchers.categories });
  const [error, setError] = useState<string | null>(null);

  async function change(category: CategoryDto, code: string) {
    setError(null);
    try {
      await commands.setCategoryNecessity(category.id, code).then(unwrap);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  if (categories.isPending) {
    return <p className="text-sm text-muted">{t("common.loading")}</p>;
  }
  if (categories.isError) {
    return <Alert>{t("errors.generic")}</Alert>;
  }
  return (
    <Card title={t("family.categoriesTitle")}>
      <ul className="flex flex-col gap-2">
        {categories.data.map((category) => (
          <li
            key={category.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-app px-4 py-3"
          >
            <span className="text-sm text-text">{category.name}</span>
            <label className="flex items-center gap-2 text-sm text-muted">
              <span className="sr-only">{t("family.necessityLabel")}</span>
              <select
                aria-label={`${category.name}: ${t("family.necessityLabel")}`}
                value={category.necessity}
                onChange={(event) => {
                  void change(category, event.currentTarget.value);
                }}
                className="h-9 rounded-lg border border-border bg-app px-2 text-text outline-none focus:border-accent"
              >
                {NECESSITY_CODES.map((code) => (
                  <option key={code} value={code}>
                    {t(necessityKey(code))}
                  </option>
                ))}
              </select>
            </label>
          </li>
        ))}
      </ul>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

function LimitStep() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const limit = useQuery({ queryKey: familyKeys.limit, queryFn: familyFetchers.limit });
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function saveLimit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.setHavasLimit(amount).then(unwrap);
      setAmount("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  if (limit.isPending) {
    return <p className="text-sm text-muted">{t("common.loading")}</p>;
  }
  if (limit.isError) {
    return <Alert>{t("errors.generic")}</Alert>;
  }
  const data: HavasLimitDto = limit.data;
  return (
    <div className="flex flex-col gap-6">
      <Card title={t("family.limitTitle")}>
        <p className="text-sm text-muted">
          <LimitStatusText data={data} />
        </p>
        {data.limit !== null ? (
          <p className="text-base text-text">
            {t("family.spent")}: {data.spent.formatted} / {data.limit.formatted}
          </p>
        ) : null}
        {data.active && data.level === "WARNING" ? (
          <p className="text-sm text-muted">{t("family.levelWarning")}</p>
        ) : null}
        {data.active && data.level === "REACHED" ? (
          <p className="text-sm text-muted">{t("family.levelReached")}</p>
        ) : null}
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            void saveLimit(event);
          }}
        >
          <Field
            id="limit-amount"
            label={t("family.limitAmount")}
            inputMode="numeric"
            value={amount}
            onChange={(event) => {
              setAmount(event.currentTarget.value);
            }}
          />
          <div>
            <PrimaryButton type="submit" disabled={amount.trim() === ""}>
              {t("family.limitSave")}
            </PrimaryButton>
          </div>
        </form>
        {error !== null ? <Alert>{error}</Alert> : null}
      </Card>

      <Card title={t("family.adultsTitle")}>
        <ul className="flex flex-col gap-3">
          {data.adults.map((adult) => (
            <AdultRow key={adult.memberId} adult={adult} />
          ))}
        </ul>
      </Card>

      <AddMemberCard />
    </div>
  );
}

/** Chegara holati matni: yo'q, faol yoki faol emas (rozilik to'liq emas). */
function LimitStatusText({ data }: { data: HavasLimitDto }) {
  const { t } = useTranslation();
  if (data.limit === null) {
    return <>{t("family.limitNone")}</>;
  }
  return <>{data.active ? t("family.limitActive") : t("family.limitInactive")}</>;
}

/** Bitta katta: roziligi yoki PIN o'rnatish. PIN faqat shu qatorda saqlanadi. */
function AdultRow({ adult }: { adult: AdultConsentDto }) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function consent(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.consentHavasLimit(adult.memberId, pin).then(unwrap);
      setPin("");
      await invalidate();
    } catch (caught) {
      // Noto'g'ri PIN maydondan tozalanadi: qayta kiritish uchun.
      setPin("");
      setError(message(caught));
    }
  }

  async function setPinFor(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.setMemberPin(adult.memberId, pin).then(unwrap);
      setPin("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-app px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-text">{adult.name}</span>
        <span className="text-xs text-muted">
          {adult.consented ? t("family.consented") : t("family.notConsented")}
        </span>
      </div>
      {adult.consented ? null : adult.hasPin ? (
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            void consent(event);
          }}
        >
          <PinInput id={`consent-${adult.memberId}`} value={pin} onChange={setPin} />
          <PrimaryButton type="submit" disabled={pin.length !== 6}>
            {t("family.consent")}
          </PrimaryButton>
        </form>
      ) : (
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            void setPinFor(event);
          }}
        >
          <span className="text-xs text-subtle">{t("family.noPin")}</span>
          <PinInput id={`setpin-${adult.memberId}`} value={pin} onChange={setPin} />
          <SecondaryButton type="submit" disabled={pin.length !== 6}>
            {t("family.pinSet")}
          </SecondaryButton>
        </form>
      )}
      {error !== null ? <Alert>{error}</Alert> : null}
    </li>
  );
}

function PinInput({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm text-muted">
        {t("family.pinLabel")}
      </label>
      <input
        id={id}
        type="password"
        inputMode="numeric"
        autoComplete="off"
        maxLength={6}
        value={value}
        placeholder={t("family.pinHint")}
        onChange={(event) => {
          onChange(sanitizePin(event.currentTarget.value));
        }}
        className="h-10 w-40 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
      />
    </div>
  );
}

/** Yangi oila a'zosi. Kattaga PIN majburiy. */
function AddMemberCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFamily();
  const message = useErrorMessage();
  const [name, setName] = useState("");
  const [role, setRole] = useState<"ADULT" | "CHILD">("ADULT");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await commands.addMember({ name, role, pin: role === "ADULT" ? pin : null }).then(unwrap);
      setName("");
      setPin("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("family.membersTitle")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          void add(event);
        }}
      >
        <Field
          id="member-name"
          label={t("family.memberName")}
          value={name}
          onChange={(event) => {
            setName(event.currentTarget.value);
          }}
        />
        <div className="flex flex-col gap-2">
          <label htmlFor="member-role" className="text-sm text-muted">
            {t("family.memberRole")}
          </label>
          <select
            id="member-role"
            value={role}
            onChange={(event) => {
              setRole(event.currentTarget.value === "CHILD" ? "CHILD" : "ADULT");
            }}
            className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
          >
            <option value="ADULT">{t("family.roleAdult")}</option>
            <option value="CHILD">{t("family.roleChild")}</option>
          </select>
        </div>
        {role === "ADULT" ? <PinInput id="member-pin" value={pin} onChange={setPin} /> : null}
        <div>
          <PrimaryButton
            type="submit"
            disabled={name.trim() === "" || (role === "ADULT" && pin.length !== 6)}
          >
            {t("family.addMember")}
          </PrimaryButton>
        </div>
      </form>
      {error !== null ? <Alert>{error}</Alert> : null}
    </Card>
  );
}

function SummaryStep({ onFinish }: { onFinish: () => void }) {
  const { t } = useTranslation();
  const limit = useQuery({ queryKey: familyKeys.limit, queryFn: familyFetchers.limit });
  return (
    <Card title={t("family.steps.summary")}>
      {limit.isSuccess ? (
        <p className="text-base text-text">
          {t("family.summaryLimitStatus")}: <LimitStatusText data={limit.data} />
        </p>
      ) : null}
      <p className="text-sm text-muted">{t("family.summaryDone")}</p>
      <p className="text-sm text-subtle">{t("family.summaryPdfLater")}</p>
      <div>
        <PrimaryButton onClick={onFinish}>{t("family.finish")}</PrimaryButton>
      </div>
    </Card>
  );
}
