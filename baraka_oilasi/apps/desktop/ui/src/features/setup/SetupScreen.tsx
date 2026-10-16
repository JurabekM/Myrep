import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type PickedFile, type SetupResult } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { LOCALES, type LocaleTag } from "../../i18n";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";

const SPACES = ["UY", "KASBKOR", "MUSOFIR"] as const;

/** Birinchi ishga tushirish (≤ 5 qadam onboarding'ning desktop qismi). */
export function SetupScreen() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [household, setHousehold] = useState("");
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [pin2, setPin2] = useState("");
  const [spaces, setSpaces] = useState<string[]>(["UY"]);
  const [mismatch, setMismatch] = useState(false);
  const [result, setResult] = useState<SetupResult | null>(null);
  // «Mavjud xonadonga qo'shilish» (8.5) yoki zaxira nusxadan tiklash.
  const [joining, setJoining] = useState(false);
  const [file, setFile] = useState<PickedFile | null>(null);
  const [secret, setSecret] = useState("");
  const [deviceName, setDeviceName] = useState("Desktop");

  const setup = useMutation({
    mutationFn: () =>
      call(
        commands.setup(pin, {
          householdName: household,
          deviceName: "Desktop",
          platform: "desktop",
          locale: i18n.language,
          baseCurrency: "UZS",
          monthStartDay: 1,
          spaces,
          members: [{ displayName: name, role: "ADULT" }],
        }),
      ),
    onSuccess: setResult,
  });
  const pick = useMutation({ mutationFn: () => call(commands.pickBarakaFile()), onSuccess: (f) => f && setFile(f) });
  const join = useMutation({
    mutationFn: () => call(commands.joinHousehold(file?.path ?? "", pin, { secret, deviceName, platform: "desktop" })),
    onSuccess: setResult,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setMismatch(pin !== pin2);
    if (pin !== pin2) return;
    if (joining) join.mutate();
    else setup.mutate();
  };

  if (result) {
    return (
      <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center gap-6 p-8">
        <h1 className="text-2xl font-semibold">{t("setup.recoveryTitle")}</h1>
        <p className="leading-relaxed">{t("setup.recoveryHint")}</p>
        <p data-testid="recovery-code" className="card text-center font-mono text-xl tracking-widest select-all">
          {result.recoveryCode}
        </p>
        <button autoFocus className="btn-primary" onClick={() => void qc.invalidateQueries({ queryKey: keys.session })}>
          {t("setup.recoveryDone")}
        </button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">{t("setup.title")}</h1>
      <div className="flex gap-2">
        {LOCALES.map((l: LocaleTag) => (
          <button key={l} type="button" className={l === i18n.language ? "btn-primary" : "btn-ghost"} onClick={() => void i18n.changeLanguage(l)}>
            {l}
          </button>
        ))}
      </div>
      <div role="tablist" className="flex gap-1 border-b border-line">
        {([false, true] as const).map((j) => (
          <button
            key={String(j)}
            type="button"
            role="tab"
            aria-selected={joining === j}
            className={`-mb-px border-b-2 px-4 py-2 text-sm ${joining === j ? "border-accent text-ink" : "border-transparent text-ink-muted hover:text-ink"}`}
            onClick={() => setJoining(j)}
          >
            {t(j ? "setup.join" : "setup.create")}
          </button>
        ))}
      </div>
      <form className="flex flex-col gap-4" onSubmit={submit}>
        {joining ? (
          <>
            <p className="text-sm text-ink-muted">{t("setup.joinHint")}</p>
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" className="btn-ghost" onClick={() => pick.mutate()}>
                {t("sync.pickFile")}
              </button>
              <span className="text-sm text-ink-muted">{file ? file.name : t("sync.noFile")}</span>
            </div>
            <label>
              <span className="label">{t("setup.joinSecret")}</span>
              <input className="field font-mono" autoComplete="off" value={secret} onChange={(e) => setSecret(e.target.value)} required />
            </label>
            <label>
              <span className="label">{t("setup.deviceName")}</span>
              <input className="field" value={deviceName} onChange={(e) => setDeviceName(e.target.value)} required />
            </label>
          </>
        ) : (
          <>
        <label>
          <span className="label">{t("setup.household")}</span>
          <input className="field" value={household} onChange={(e) => setHousehold(e.target.value)} required />
        </label>
        <label>
          <span className="label">{t("setup.yourName")}</span>
          <input className="field" value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
          </>
        )}
        <div className="grid grid-cols-2 gap-3">
          <label>
            <span className="label">{t("setup.pin")}</span>
            <input className="field tracking-widest" type="password" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} required />
          </label>
          <label>
            <span className="label">{t("setup.pinRepeat")}</span>
            <input className="field tracking-widest" type="password" inputMode="numeric" maxLength={6} value={pin2} onChange={(e) => setPin2(e.target.value)} required />
          </label>
        </div>
        {!joining && (
        <fieldset>
          <legend className="label">{t("setup.spaces")}</legend>
          <div className="flex gap-4">
            {SPACES.map((s) => (
              <label key={s} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={spaces.includes(s)}
                  onChange={(e) => setSpaces((cur) => (e.target.checked ? [...cur, s] : cur.filter((x) => x !== s)))}
                />
                {t(`space.${s}`)}
              </label>
            ))}
          </div>
        </fieldset>
        )}
        {mismatch && <p role="alert" className="text-sm text-danger">{t("setup.pinMismatch")}</p>}
        <ErrorText error={joining ? (pick.error ?? join.error) : setup.error} />
        {joining ? (
          <button className="btn-primary" disabled={join.isPending || !file}>
            {t("setup.joinSubmit")}
          </button>
        ) : (
          <button className="btn-primary" disabled={setup.isPending || spaces.length === 0}>
            {t("setup.submit")}
          </button>
        )}
      </form>
      <p className="text-xs text-ink-muted">{t("app.disclaimer")}</p>
    </main>
  );
}
