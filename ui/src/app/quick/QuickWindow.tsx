import { useQuery } from "@tanstack/react-query";
import { type SyntheticEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";
import { useErrorMessage } from "../finance/errors";
import { fetchers, financeKeys } from "../finance/queries";
import { Alert, Field, PrimaryButton, SecondaryButton } from "../finance/ui";
import { SECURITY_STATUS_KEY, fetchSecurityStatus } from "../security/security-status";

/** Holat so'rovi oralig'i: qulflanganda darhol summasiz holatga o'tish uchun. */
const STATUS_POLL_MS = 5_000;

/**
 * «Tez xarajat» mini oynasi (Ctrl+Alt+B). Qulf holatida hech qanday summa yoki ro'yxat ko'rsatilmaydi —
 * faqat qulf xabari va asosiy oynani ochish tugmasi (DESKTOP_PROMPT 7-bo'lim).
 */
export function QuickWindow() {
  const { t } = useTranslation();
  const status = useQuery({
    queryKey: SECURITY_STATUS_KEY,
    queryFn: fetchSecurityStatus,
    refetchInterval: STATUS_POLL_MS,
  });

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        void commands.hideQuickWindow();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  if (status.isPending) {
    return <p className="p-6 text-sm text-muted">{t("common.loading")}</p>;
  }
  if (status.isError || !status.data.setUp || !status.data.unlocked) {
    return <LockedNotice />;
  }
  return <QuickExpenseForm />;
}

function LockedNotice() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <h1 className="text-lg font-semibold text-text">{t("quickWindow.lockedTitle")}</h1>
      <p className="text-sm text-muted">{t("quickWindow.lockedBody")}</p>
      <div>
        <PrimaryButton
          onClick={() => {
            void commands.showMainWindow();
          }}
        >
          {t("quickWindow.openMain")}
        </PrimaryButton>
      </div>
    </div>
  );
}

function QuickExpenseForm() {
  const { t } = useTranslation();
  const message = useErrorMessage();
  const categories = useQuery({ queryKey: financeKeys.categories, queryFn: fetchers.categories });
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || amount.trim() === "") {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      unwrap(
        await commands.addExpense({
          amount,
          categoryId: category === "" ? null : category,
          note: note.trim() === "" ? null : note.trim(),
          isGift: false,
          isOstentation: false,
          fundedByDebt: false,
          occurredOn: null,
        }),
      );
      setAmount("");
      setNote("");
      setSaved(true);
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="flex h-full flex-col gap-4 p-6" onSubmit={(event) => void save(event)}>
      <h1 className="text-lg font-semibold text-text">{t("quickWindow.title")}</h1>
      <Field
        id="quick-amount"
        label={t("quickWindow.amount")}
        inputMode="numeric"
        autoFocus
        value={amount}
        onChange={(event) => {
          setAmount(event.currentTarget.value);
          setSaved(false);
        }}
      />
      <div className="flex flex-col gap-2">
        <label htmlFor="quick-category" className="text-sm text-muted">
          {t("quickWindow.category")}
        </label>
        <select
          id="quick-category"
          value={category}
          onChange={(event) => {
            setCategory(event.currentTarget.value);
          }}
          className="h-10 rounded-lg border border-border bg-app px-3 text-text outline-none focus:border-accent"
        >
          <option value="">{t("family.noCategory")}</option>
          {(categories.isSuccess ? categories.data : []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>
      <Field
        id="quick-note"
        label={t("quickWindow.note")}
        value={note}
        onChange={(event) => {
          setNote(event.currentTarget.value);
        }}
      />
      <div className="flex flex-wrap items-center gap-2">
        <PrimaryButton type="submit" disabled={busy || amount.trim() === ""}>
          {t("quickWindow.save")}
        </PrimaryButton>
        <SecondaryButton
          onClick={() => {
            void commands.hideQuickWindow();
          }}
        >
          {t("quickWindow.close")}
        </SecondaryButton>
        {saved ? <span className="text-sm text-muted">{t("quickWindow.saved")}</span> : null}
      </div>
      {error !== null ? <Alert>{error}</Alert> : null}
    </form>
  );
}
