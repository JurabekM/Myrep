import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { PrimaryButton, SecondaryButton } from "../finance/ui";
import type { PageId } from "../navigation";
import { useUiStore } from "../store";

const STEPS = ["welcome", "income", "future", "expenses", "safety"] as const;
type Step = (typeof STEPS)[number];

function stepKeys(step: Step) {
  switch (step) {
    case "income":
      return {
        title: "onboarding.income.title",
        body: "onboarding.income.body",
        action: "onboarding.income.action",
        page: "income" as PageId,
      } as const;
    case "future":
      return {
        title: "onboarding.future.title",
        body: "onboarding.future.body",
        action: "onboarding.future.action",
        page: "future" as PageId,
      } as const;
    case "expenses":
      return {
        title: "onboarding.expenses.title",
        body: "onboarding.expenses.body",
        action: "onboarding.expenses.action",
        page: "expenses" as PageId,
      } as const;
    case "safety":
      return {
        title: "onboarding.safety.title",
        body: "onboarding.safety.body",
        action: null,
        page: null,
      } as const;
    default:
      return {
        title: "onboarding.welcome.title",
        body: "onboarding.welcome.body",
        action: null,
        page: null,
      } as const;
  }
}

/**
 * Birinchi ishga tushirish (D15): 5 qadam — xush kelibsiz, daromad, «Kelajagim», xarajat va havas, xavfsizlik.
 * Har qadamda tegishli bo'limga o'tish mumkin; «O'tkazib yuborish» doim bor. Holat — UI afzalligi
 * (`localStorage`, moliyaviy ma'lumot emas). Klaviatura: Esc — o'tkazib yuborish, fokus dialog ichida.
 */
export function Onboarding() {
  const { t } = useTranslation();
  const setPage = useUiStore((state) => state.setPage);
  const setOnboardingDone = useUiStore((state) => state.setOnboardingDone);
  const [index, setIndex] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const step = STEPS[index] ?? "welcome";
  const keys = stepKeys(step);
  const last = index === STEPS.length - 1;

  useEffect(() => {
    headingRef.current?.focus();
  }, [index]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOnboardingDone();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [setOnboardingDone]);

  function go(page: PageId) {
    setPage(page);
    setOnboardingDone();
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-app/90 p-6"
    >
      <div className="flex w-full max-w-xl flex-col gap-5 rounded-xl border border-border bg-surface p-8">
        <p className="text-xs text-subtle">
          {t("onboarding.progress", { step: index + 1, total: STEPS.length })}
        </p>
        <h1
          id="onboarding-title"
          ref={headingRef}
          tabIndex={-1}
          className="text-2xl font-semibold text-text outline-none"
        >
          {t(keys.title)}
        </h1>
        <p className="text-sm leading-relaxed text-muted">{t(keys.body)}</p>
        {step === "welcome" ? (
          <p className="text-xs text-subtle">{t("common.disclaimer")}</p>
        ) : null}
        <ol className="flex gap-1" aria-hidden="true">
          {STEPS.map((s, i) => (
            <li
              key={s}
              className={`h-1 flex-1 rounded ${i <= index ? "bg-accent" : "bg-raised"}`}
            />
          ))}
        </ol>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SecondaryButton
            onClick={() => {
              setOnboardingDone();
            }}
          >
            {t("onboarding.skip")}
          </SecondaryButton>
          <div className="flex flex-wrap gap-2">
            {index > 0 ? (
              <SecondaryButton
                onClick={() => {
                  setIndex((i) => Math.max(0, i - 1));
                }}
              >
                {t("common.back")}
              </SecondaryButton>
            ) : null}
            {keys.page !== null ? (
              <SecondaryButton
                onClick={() => {
                  go(keys.page);
                }}
              >
                {t(keys.action)}
              </SecondaryButton>
            ) : null}
            <PrimaryButton
              onClick={() => {
                if (last) {
                  setOnboardingDone();
                } else {
                  setIndex((i) => Math.min(STEPS.length - 1, i + 1));
                }
              }}
            >
              {last ? t("onboarding.finish") : t("common.next")}
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
}
