import { useQueryClient } from "@tanstack/react-query";
import { type SyntheticEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { commands } from "../../bindings/bindings";
import { isValidPin } from "./pin";
import { PinField, SecurityCard } from "./SecurityCard";
import { SECURITY_STATUS_KEY } from "./security-status";

/** Qulflash ekrani: baza qulflangan, davom etish uchun PIN kiritiladi. */
export function LockScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);

  const clearLockout = useCallback(() => {
    setLockedUntil(null);
  }, []);

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValidPin(pin) || busy || lockedUntil !== null) {
      return;
    }

    setBusy(true);
    setError(null);
    const result = await commands.unlock(pin);
    setBusy(false);
    setPin("");

    if (result.status === "ok") {
      await queryClient.invalidateQueries({ queryKey: SECURITY_STATUS_KEY });
      return;
    }

    switch (result.error.code) {
      case "WRONG_PIN":
        setError(t("security.wrongPin"));
        break;
      case "LOCKED_OUT":
        setLockedUntil(Date.now() + result.error.retryAfterSeconds * 1000);
        break;
      case "KEY_UNAVAILABLE":
        setError(t("security.keyUnavailable"));
        break;
      default:
        setError(t("security.internal"));
    }
  }

  return (
    <SecurityCard title={t("security.lockedTitle")} text={t("security.lockedText")}>
      <form
        className="flex flex-col gap-5"
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <PinField
          id="unlock-pin"
          label={t("security.pinLabel")}
          value={pin}
          onChange={setPin}
          autoFocus
          disabled={lockedUntil !== null}
        />

        {lockedUntil !== null ? (
          <LockoutNotice until={lockedUntil} onExpire={clearLockout} />
        ) : null}
        {error !== null ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={!isValidPin(pin) || busy || lockedUntil !== null}
          className="h-11 rounded-lg bg-accent font-medium text-app transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {t("security.unlock")}
        </button>
      </form>
    </SecurityCard>
  );
}

interface LockoutNoticeProps {
  /** Kutish tugaydigan vaqt (epoch millisekundlarda). */
  until: number;
  onExpire: () => void;
}

/** Juda ko'p noto'g'ri urinishdan keyingi sanoq. Vaqt tugagach `onExpire` chaqiriladi. */
function LockoutNotice({ until, onExpire }: LockoutNoticeProps) {
  const { t } = useTranslation();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      const current = Date.now();
      setNow(current);
      if (current >= until) {
        window.clearInterval(timer);
        onExpire();
      }
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [until, onExpire]);

  const seconds = Math.max(0, Math.ceil((until - now) / 1000));
  return (
    <p role="alert" className="text-sm text-danger">
      {t("security.lockedOut", { seconds })}
    </p>
  );
}
