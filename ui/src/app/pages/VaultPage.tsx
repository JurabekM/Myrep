import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { type ShareRuleDto, commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { LumpSumCard } from "../finance/LumpSumCard";
import { ReserveCard } from "../finance/ReserveCard";
import { useErrorMessage } from "../finance/errors";
import { fetchers, financeKeys, useInvalidateFinance } from "../finance/queries";
import {
  Alert,
  Card,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Stat,
} from "../finance/ui";
import { isValidPin, sanitizePin } from "../security/pin";

/** Pul olishdan oldin kutiladigan vaqt (soniyalarda): «o'ylash pauzasi» (SPEC 2.2). */
const WITHDRAW_PAUSE_SECONDS = 5;

/** «Kelajagim» ekrani: balans, odat, progressiv taklif, ulush qoidasi, ro'molcha, pul olish va tarix. */
export function VaultPage() {
  const { t } = useTranslation();
  const vault = useQuery({ queryKey: financeKeys.vault, queryFn: fetchers.vault });

  if (vault.isPending) {
    return <p className="text-sm text-muted">{t("common.loading")}</p>;
  }
  if (vault.isError) {
    return <Alert>{t("errors.generic")}</Alert>;
  }
  const data = vault.data;
  const kindLabel = (kind: string) => {
    switch (kind) {
      case "INITIAL":
        return t("vault.history.initial");
      case "INCOME_SHARE":
        return t("vault.history.share");
      case "RESCUE_DEPOSIT":
        return t("vault.history.rescue");
      default:
        return t("vault.history.withdrawal");
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={t("vault.title")} subtitle={t("vault.subtitle")} />

      <Card title={t("vault.balanceTitle")}>
        <div className="grid gap-6 sm:grid-cols-2">
          <Stat label={t("vault.balance")} value={data.balance.formatted} />
          <Stat label={t("vault.savedThisMonth")} value={data.savedThisMonth.formatted} />
        </div>
        <p className="text-sm text-muted">
          {data.habit.currentStreakWeeks > 0
            ? t("home.habit.streak", { weeks: data.habit.currentStreakWeeks })
            : t("home.habit.noStreak")}
          {" · "}
          {t("vault.totalWeeks", { weeks: data.habit.totalWeeks })}
        </p>
      </Card>

      <ReserveCard />

      <LumpSumCard />

      {data.progressionOfferBp !== null ? <ProgressionCard bp={data.progressionOfferBp} /> : null}
      <RuleCard rule={data.rule} />
      {!data.hasInitial ? <InitialCard /> : null}
      <WithdrawCard />

      <Card title={t("vault.history.title")}>
        {data.history.length === 0 ? (
          <p className="text-sm text-muted">{t("vault.history.empty")}</p>
        ) : null}
        <ul className="flex flex-col divide-y divide-border">
          {data.history.map((entry) => (
            <li key={entry.id} className="flex items-center justify-between gap-4 py-3">
              <span className="flex min-w-0 flex-col">
                <span className="text-base text-text">{kindLabel(entry.kind)}</span>
                <span className="text-xs text-subtle">
                  {entry.occurredOn}
                  {entry.reason !== null ? ` · ${entry.reason}` : ""}
                </span>
              </span>
              <span className="shrink-0 text-base font-medium text-text">
                {entry.amount.formatted}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/** Progressiv taklif: 4 hafta ketma-ket ajratilgan — ulushni +1 % oshirish. */
function ProgressionCard({ bp }: { bp: number }) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const [error, setError] = useState<string | null>(null);

  async function respond(accept: boolean) {
    setError(null);
    try {
      unwrap(await commands.respondProgression(accept));
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("vault.progression.title")}>
      <p className="text-base text-text">{t("vault.progression.text", { percent: bp / 100 })}</p>
      {error !== null ? <Alert>{error}</Alert> : null}
      <div className="flex gap-2">
        <PrimaryButton
          onClick={() => {
            void respond(true);
          }}
        >
          {t("vault.progression.accept")}
        </PrimaryButton>
        <SecondaryButton
          onClick={() => {
            void respond(false);
          }}
        >
          {t("vault.progression.later")}
        </SecondaryButton>
      </div>
    </Card>
  );
}

/** Ulush qoidasi: 5 % / 10 % yoki oylik qat'iy summa; progressiv rejim faqat foiz bilan. */
function RuleCard({ rule }: { rule: ShareRuleDto }) {
  const { t } = useTranslation();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const [choice, setChoice] = useState<"500" | "1000" | "FIXED">(
    rule.mode === "FIXED" ? "FIXED" : rule.basisPoints === 1000 ? "1000" : "500",
  );
  const [fixed, setFixed] = useState("");
  const [progressive, setProgressive] = useState(rule.progressive);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    try {
      const isFixed = choice === "FIXED";
      unwrap(
        await commands.setShareRule({
          mode: isFixed ? "FIXED" : "PERCENT",
          basisPoints: isFixed ? null : Number(choice),
          fixedAmount: isFixed ? fixed : null,
          progressive: isFixed ? false : progressive,
        }),
      );
      await invalidate();
      setSaved(true);
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("vault.rule.title")}>
      <p className="text-sm text-muted">
        {rule.mode === "FIXED" && rule.fixedAmount !== null
          ? t("vault.rule.currentFixed", { amount: rule.fixedAmount.formatted })
          : t("vault.rule.currentPercent", { percent: (rule.basisPoints ?? 0) / 100 })}
      </p>
      <form className="flex flex-col gap-4" onSubmit={(event) => void save(event)}>
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm text-muted">{t("vault.rule.choose")}</legend>
          <RadioOption
            name="share-rule"
            value="500"
            checked={choice === "500"}
            onSelect={setChoice}
          >
            {t("vault.rule.percent5")}
          </RadioOption>
          <RadioOption
            name="share-rule"
            value="1000"
            checked={choice === "1000"}
            onSelect={setChoice}
          >
            {t("vault.rule.percent10")}
          </RadioOption>
          <RadioOption
            name="share-rule"
            value="FIXED"
            checked={choice === "FIXED"}
            onSelect={setChoice}
          >
            {t("vault.rule.fixed")}
          </RadioOption>
        </fieldset>
        {choice === "FIXED" ? (
          <Field
            id="fixed-amount"
            label={t("vault.rule.fixedAmount")}
            value={fixed}
            inputMode="decimal"
            autoComplete="off"
            onChange={(event) => {
              setFixed(event.target.value);
            }}
          />
        ) : (
          <label className="flex items-center gap-2 text-sm text-text">
            <input
              type="checkbox"
              checked={progressive}
              onChange={(event) => {
                setProgressive(event.target.checked);
              }}
            />
            {t("vault.rule.progressive")}
          </label>
        )}
        {error !== null ? <Alert>{error}</Alert> : null}
        {saved ? <p className="text-sm text-muted">{t("vault.rule.saved")}</p> : null}
        <div>
          <PrimaryButton type="submit" disabled={choice === "FIXED" && fixed.trim() === ""}>
            {t("common.save")}
          </PrimaryButton>
        </div>
      </form>
    </Card>
  );
}

function RadioOption({
  name,
  value,
  checked,
  onSelect,
  children,
}: {
  name: string;
  value: "500" | "1000" | "FIXED";
  checked: boolean;
  onSelect: (value: "500" | "1000" | "FIXED") => void;
  children: string;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-text">
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => {
          onSelect(value);
        }}
      />
      {children}
    </label>
  );
}

/** Boshlang'ich balans (ro'molcha): ilovadan oldin yig'ilgan jamg'arma. Bir marta. */
function InitialCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      unwrap(await commands.setInitialBalance(amount));
      setAmount("");
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <Card title={t("vault.initial.title")}>
      <p className="text-sm text-muted">{t("vault.initial.text")}</p>
      <form className="flex flex-col gap-4" onSubmit={(event) => void save(event)}>
        <Field
          id="initial-amount"
          label={t("vault.initial.amount")}
          value={amount}
          inputMode="decimal"
          autoComplete="off"
          onChange={(event) => {
            setAmount(event.target.value);
          }}
        />
        {error !== null ? <Alert>{error}</Alert> : null}
        <div>
          <PrimaryButton type="submit" disabled={amount.trim() === ""}>
            {t("common.save")}
          </PrimaryButton>
        </div>
      </form>
    </Card>
  );
}

/**
 * Pul olish (friction, SPEC 2.2): sabab majburiy, 5 soniyalik o'ylash pauzasi, PIN qayta kiritiladi.
 * Noto'g'ri PIN — hisoblanadi (kutish qo'yilishi mumkin).
 */
function WithdrawCard() {
  const { t } = useTranslation();
  const invalidate = useInvalidateFinance();
  const message = useErrorMessage();
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [pin, setPin] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(WITHDRAW_PAUSE_SECONDS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (secondsLeft <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setSecondsLeft((current) => Math.max(0, current - 1));
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [secondsLeft]);

  const ready =
    secondsLeft === 0 && amount.trim() !== "" && reason.trim() !== "" && isValidPin(pin) && !busy;

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) {
      return;
    }
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      unwrap(await commands.withdraw(pin, { amount, reason }));
      setAmount("");
      setReason("");
      setDone(true);
      await invalidate();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setPin("");
      setBusy(false);
    }
  }

  return (
    <Card title={t("vault.withdraw.title")}>
      <p className="text-sm text-muted">{t("vault.withdraw.hint")}</p>
      {secondsLeft > 0 ? (
        <p className="text-sm text-accent" aria-live="polite">
          {t("vault.withdraw.pause", { seconds: secondsLeft })}
        </p>
      ) : null}
      <form className="flex flex-col gap-4" onSubmit={(event) => void submit(event)}>
        <Field
          id="withdraw-amount"
          label={t("vault.withdraw.amount")}
          value={amount}
          inputMode="decimal"
          autoComplete="off"
          onChange={(event) => {
            setAmount(event.target.value);
          }}
        />
        <Field
          id="withdraw-reason"
          label={t("vault.withdraw.reason")}
          value={reason}
          autoComplete="off"
          onChange={(event) => {
            setReason(event.target.value);
          }}
        />
        <Field
          id="withdraw-pin"
          label={t("vault.withdraw.pin")}
          type="password"
          inputMode="numeric"
          autoComplete="off"
          value={pin}
          maxLength={6}
          onChange={(event) => {
            setPin(sanitizePin(event.target.value));
          }}
        />
        {error !== null ? <Alert>{error}</Alert> : null}
        {done ? <p className="text-sm text-muted">{t("vault.withdraw.done")}</p> : null}
        <div>
          <PrimaryButton type="submit" disabled={!ready}>
            {t("vault.withdraw.submit")}
          </PrimaryButton>
        </div>
      </form>
    </Card>
  );
}
