import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { call } from "../../lib/api";

/** Qulf ekrani: summalar ko'rinmaydi. PIN yoki tiklash kodi bilan ochiladi. */
export function LockScreen({ lockedUntil }: { lockedUntil: string | null }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [pin, setPin] = useState("");
  const [recovery, setRecovery] = useState(false);
  const [code, setCode] = useState("");
  const [newPin, setNewPin] = useState("");
  const done = () => void qc.invalidateQueries();

  const unlock = useMutation({ mutationFn: () => call(commands.unlock(pin)), onSuccess: done, onSettled: () => setPin("") });
  const restore = useMutation({ mutationFn: () => call(commands.unlockWithRecovery(code, newPin)), onSuccess: done });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (recovery) restore.mutate();
    else unlock.mutate();
  };

  return (
    <main className="mx-auto flex min-h-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">{t("lock.title")}</h1>
      {lockedUntil && <p role="status" className="text-sm text-warn">{t("lock.lockedUntil", { time: new Date(lockedUntil).toLocaleTimeString() })}</p>}
      <form className="flex flex-col gap-4" onSubmit={submit}>
        {recovery ? (
          <>
            <label>
              <span className="label">{t("lock.recoveryCode")}</span>
              <input className="field font-mono" value={code} onChange={(e) => setCode(e.target.value)} required />
            </label>
            <label>
              <span className="label">{t("lock.newPin")}</span>
              <input className="field tracking-widest" type="password" inputMode="numeric" maxLength={6} value={newPin} onChange={(e) => setNewPin(e.target.value)} required />
            </label>
          </>
        ) : (
          <label>
            <span className="label">{t("lock.pin")}</span>
            <input autoFocus className="field text-center text-2xl tracking-[0.5em]" type="password" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} required />
          </label>
        )}
        <ErrorText error={recovery ? restore.error : unlock.error} />
        <button className="btn-primary" disabled={unlock.isPending || restore.isPending}>
          {t("lock.unlock")}
        </button>
        <button type="button" className="text-sm text-ink-muted underline" onClick={() => setRecovery((r) => !r)}>
          {recovery ? t("common.cancel") : t("lock.forgot")}
        </button>
      </form>
    </main>
  );
}
