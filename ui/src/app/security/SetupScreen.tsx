import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { isValidPin } from "./pin";
import { PinField, SecurityCard } from "./SecurityCard";
import { SECURITY_STATUS_KEY } from "./security-status";

/** Birinchi ishga tushirish: PIN o'rnatiladi va ikki marta tasdiqlanadi. */
export function SetupScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pin, setPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    if (!isValidPin(pin)) {
      setError(t("security.invalidPin"));
      return;
    }
    if (pin !== confirmation) {
      setError(t("security.mismatch"));
      setConfirmation("");
      return;
    }

    setBusy(true);
    setError(null);
    const result = await commands.setupPin(pin);
    setBusy(false);

    if (result.status === "ok" || result.error.code === "ALREADY_SET_UP") {
      // Sozlangan bo'lsa (yoki allaqachon bo'lsa) holat qayta o'qiladi: keyingi ekran tanlanadi.
      await queryClient.invalidateQueries({ queryKey: SECURITY_STATUS_KEY });
      return;
    }

    if (result.error.code === "DATABASE_WITHOUT_KEY") {
      setError(t("security.databaseWithoutKey"));
    } else if (result.error.code === "KEY_UNAVAILABLE") {
      setError(t("security.keyUnavailable"));
    } else {
      setError(t("security.internal"));
    }
  }

  return (
    <SecurityCard title={t("security.setupTitle")} text={t("security.setupText")}>
      <form
        className="flex flex-col gap-5"
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <PinField
          id="setup-pin"
          label={t("security.pinLabel")}
          value={pin}
          onChange={setPin}
          autoFocus
        />
        <PinField
          id="setup-pin-confirm"
          label={t("security.confirmLabel")}
          value={confirmation}
          onChange={setConfirmation}
        />

        <p className="text-sm text-muted">{t("security.setupWarning")}</p>

        {error !== null ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={busy}
          className="h-11 rounded-lg bg-accent font-medium text-app transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {t("security.setupButton")}
        </button>
      </form>
    </SecurityCard>
  );
}
