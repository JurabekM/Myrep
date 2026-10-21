import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type PickedFile, type SetupResult } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { LOCALES, type LocaleTag } from "../../i18n";
import { call } from "../../lib/api";
import { keys } from "../../lib/queryClient";
import { useUi } from "../../state/ui";

const SPACES = ["UY", "KASBKOR", "MUSOFIR"] as const;
export const RHYTHMS = ["DAILY", "ORDERS", "MONTHLY"] as const;
type Rhythm = (typeof RHYTHMS)[number];
type Member = { key: number; displayName: string; role: "ADULT" | "CHILD" };

/** Onboarding qadamlari (≤ 5): til va yo'l → oila → daromad → qarzlar → PIN; keyin tiklash kodi. */
const STEPS = ["language", "family", "income", "debts", "pin"] as const;
type Step = (typeof STEPS)[number];

export function SetupScreen() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const setScreen = useUi((s) => s.setScreen);
  const [step, setStep] = useState<Step>("language");
  const [joining, setJoining] = useState(false);
  const [household, setHousehold] = useState("");
  const [name, setName] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [spaces, setSpaces] = useState<string[]>(["UY"]);
  const [rhythm, setRhythm] = useState<Rhythm | null>(null);
  const [monthStartDay, setMonthStartDay] = useState(1);
  const [debts, setDebts] = useState<boolean | null>(null);
  const [pin, setPin] = useState("");
  const [pin2, setPin2] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [result, setResult] = useState<SetupResult | null>(null);
  // «Mavjud xonadonga qo'shilish» (8.5) yoki zaxira nusxadan tiklash.
  const [file, setFile] = useState<PickedFile | null>(null);
  const [secret, setSecret] = useState("");
  const [deviceName, setDeviceName] = useState("Desktop");
  const heading = useRef<HTMLHeadingElement>(null);

  // Qadam almashganda fokus sarlavhaga — ekran o'quvchi yangi qadamni o'qiydi.
  useEffect(() => heading.current?.focus(), [step, joining, result]);

  const setup = useMutation({
    mutationFn: () =>
      call(
        commands.setup(pin, {
          householdName: household,
          deviceName: "Desktop",
          platform: "desktop",
          locale: i18n.language,
          baseCurrency: "UZS",
          monthStartDay: rhythm === "MONTHLY" ? monthStartDay : 1,
          spaces,
          members: [{ displayName: name, role: "ADULT" }, ...members.map(({ displayName, role }) => ({ displayName, role }))],
          incomeRhythm: rhythm,
          debtsDeclared: debts === true,
        }),
      ),
    onSuccess: setResult,
  });
  const pick = useMutation({ mutationFn: () => call(commands.pickBarakaFile()), onSuccess: (f) => f && setFile(f) });
  const join = useMutation({
    mutationFn: () => call(commands.joinHousehold(file?.path ?? "", pin, { secret, deviceName, platform: "desktop" })),
    onSuccess: setResult,
  });

  const index = STEPS.indexOf(step);
  const canNext: Record<Step, boolean> = {
    language: true,
    family: household.trim() !== "" && name.trim() !== "" && spaces.length > 0 && members.every((m) => m.displayName.trim() !== ""),
    income: rhythm !== null,
    debts: debts !== null,
    pin: pin.length === 6 && pin2.length === 6,
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (step !== "pin" && !joining) {
      const next = STEPS[index + 1];
      if (canNext[step] && next) setStep(next);
      return;
    }
    setMismatch(pin !== pin2);
    if (pin !== pin2) return;
    if (joining) join.mutate();
    else setup.mutate();
  };

  const finish = () => {
    // «Qarzim bor» degan bo'lsa — birinchi ish: qarzlarni yozib chiqish (keyin 70/20/10 taklif qilinadi).
    if (!joining && debts) setScreen("inventory");
    void qc.invalidateQueries({ queryKey: keys.session });
  };

  if (result) {
    return (
      <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center gap-6 p-8">
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {t("setup.recoveryTitle")}
        </h1>
        <p className="leading-relaxed">{t("setup.recoveryHint")}</p>
        <p data-testid="recovery-code" className="card text-center font-mono text-xl tracking-widest select-all">
          {result.recoveryCode}
        </p>
        <p className="text-sm text-ink-muted">{t("setup.backupHint")}</p>
        <button className="btn-primary" onClick={finish}>
          {t("setup.recoveryDone")}
        </button>
      </main>
    );
  }

  const pinFields = (
    <div className="grid grid-cols-2 gap-3">
      <label>
        <span className="label">{t("setup.pin")}</span>
        <input className="field tracking-widest" type="password" inputMode="numeric" autoComplete="new-password" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} required />
      </label>
      <label>
        <span className="label">{t("setup.pinRepeat")}</span>
        <input className="field tracking-widest" type="password" inputMode="numeric" autoComplete="new-password" maxLength={6} value={pin2} onChange={(e) => setPin2(e.target.value)} required />
      </label>
    </div>
  );

  return (
    <main className="mx-auto flex min-h-full max-w-xl flex-col justify-center gap-6 p-8">
      <div className="flex flex-col gap-1">
        {!joining && (
          <p className="text-sm text-ink-muted" data-testid="setup-progress">
            {t("setup.stepOf", { n: index + 1, total: STEPS.length })}
          </p>
        )}
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {joining ? t("setup.join") : t(`setup.step.${step}`)}
        </h1>
        {!joining && (
          <div className="mt-2 flex gap-1" aria-hidden="true">
            {STEPS.map((s, i) => (
              <span key={s} className={`h-1 flex-1 rounded ${i <= index ? "bg-accent" : "bg-surface"}`} />
            ))}
          </div>
        )}
      </div>

      <form className="flex flex-col gap-5" onSubmit={submit} aria-label={t("setup.title")}>
        {step === "language" && !joining && (
          <>
            <p className="leading-relaxed">{t("setup.title")}</p>
            <Choice legend={t("setup.language")}>
              {LOCALES.map((l: LocaleTag) => (
                <Radio key={l} name="locale" checked={i18n.language === l} onChange={() => void i18n.changeLanguage(l)} label={t(`locale.${l}`)} />
              ))}
            </Choice>
            <Choice legend={t("setup.path")}>
              <Radio name="path" checked={!joining} onChange={() => setJoining(false)} label={t("setup.create")} hint={t("setup.createHint")} />
              <Radio name="path" checked={joining} onChange={() => setJoining(true)} label={t("setup.join")} hint={t("setup.joinHint")} />
            </Choice>
          </>
        )}

        {joining && (
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
            {pinFields}
          </>
        )}

        {step === "family" && !joining && (
          <>
            <label>
              <span className="label">{t("setup.household")}</span>
              <input className="field" value={household} onChange={(e) => setHousehold(e.target.value)} required />
            </label>
            <label>
              <span className="label">{t("setup.yourName")}</span>
              <input className="field" value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <fieldset className="flex flex-col gap-2">
              <legend className="label">{t("setup.members")}</legend>
              <p className="text-sm text-ink-muted">{t("setup.membersHint")}</p>
              {members.map((m, i) => (
                <div key={m.key} className="flex items-end gap-2">
                  <input
                    className="field flex-1"
                    aria-label={t("setup.memberName", { n: i + 2 })}
                    value={m.displayName}
                    onChange={(e) => setMembers((cur) => cur.map((x) => (x.key === m.key ? { ...x, displayName: e.target.value } : x)))}
                  />
                  <select
                    className="field w-auto"
                    aria-label={t("setup.memberRole", { n: i + 2 })}
                    value={m.role}
                    onChange={(e) => setMembers((cur) => cur.map((x) => (x.key === m.key ? { ...x, role: e.target.value as Member["role"] } : x)))}
                  >
                    <option value="ADULT">{t("role.ADULT")}</option>
                    <option value="CHILD">{t("role.CHILD")}</option>
                  </select>
                  <button
                    type="button"
                    className="btn-ghost px-3"
                    aria-label={t("setup.memberRemove", { name: m.displayName || i + 2 })}
                    onClick={() => setMembers((cur) => cur.filter((x) => x.key !== m.key))}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button type="button" className="btn-ghost self-start" onClick={() => setMembers((cur) => [...cur, { key: Date.now() + cur.length, displayName: "", role: "ADULT" }])}>
                + {t("setup.memberAdd")}
              </button>
            </fieldset>
            <fieldset>
              <legend className="label">{t("setup.spaces")}</legend>
              <div className="flex flex-wrap gap-4">
                {SPACES.map((s) => (
                  <label key={s} className="flex items-center gap-2">
                    <input type="checkbox" checked={spaces.includes(s)} onChange={(e) => setSpaces((cur) => (e.target.checked ? [...cur, s] : cur.filter((x) => x !== s)))} />
                    {t(`space.${s}`)}
                  </label>
                ))}
              </div>
            </fieldset>
          </>
        )}

        {step === "income" && !joining && (
          <>
            <Choice legend={t("setup.rhythm")}>
              {RHYTHMS.map((r) => (
                <Radio key={r} name="rhythm" checked={rhythm === r} onChange={() => setRhythm(r)} label={t(`rhythm.${r}`)} hint={t(`rhythmHint.${r}`)} />
              ))}
            </Choice>
            {rhythm === "MONTHLY" && (
              <label className="max-w-xs">
                <span className="label">{t("setup.payday")}</span>
                <select className="field" value={monthStartDay} onChange={(e) => setMonthStartDay(Number(e.target.value))}>
                  {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}

        {step === "debts" && !joining && (
          <>
            <Choice legend={t("setup.debtsQuestion")}>
              <Radio name="debts" checked={debts === true} onChange={() => setDebts(true)} label={t("setup.debtsYes")} hint={t("setup.debtsYesHint")} />
              <Radio name="debts" checked={debts === false} onChange={() => setDebts(false)} label={t("setup.debtsNo")} />
            </Choice>
            <p className="text-sm text-ink-muted">{t("setup.debtsPrivacy")}</p>
          </>
        )}

        {step === "pin" && !joining && (
          <>
            <p className="text-sm text-ink-muted">{t("setup.pinHint")}</p>
            {pinFields}
          </>
        )}

        {mismatch && (
          <p role="alert" className="text-sm text-danger">
            {t("setup.pinMismatch")}
          </p>
        )}
        <ErrorText error={joining ? (pick.error ?? join.error) : setup.error} />

        <div className="flex gap-2">
          {(index > 0 || joining) && (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                if (joining) setJoining(false);
                else setStep(STEPS[index - 1] ?? "language");
              }}
            >
              {t("setup.back")}
            </button>
          )}
          {joining ? (
            <button className="btn-primary flex-1" disabled={join.isPending || !file}>
              {t("setup.joinSubmit")}
            </button>
          ) : step === "pin" ? (
            <button className="btn-primary flex-1" disabled={setup.isPending || !canNext.pin}>
              {t("setup.submit")}
            </button>
          ) : (
            <button className="btn-primary flex-1" disabled={!canNext[step]}>
              {t("setup.next")}
            </button>
          )}
        </div>
      </form>
      <p className="text-xs text-ink-muted">{t("app.disclaimer")}</p>
    </main>
  );
}

function Choice({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="label mb-1">{legend}</legend>
      {children}
    </fieldset>
  );
}

function Radio({ name, checked, onChange, label, hint }: { name: string; checked: boolean; onChange: () => void; label: string; hint?: string }) {
  return (
    <label className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 ${checked ? "border-accent bg-surface" : "border-field-line"}`}>
      <input type="radio" className="mt-1" name={name} checked={checked} onChange={onChange} />
      <span>
        <span className="font-medium">{label}</span>
        {hint && <span className="block text-sm text-ink-muted">{hint}</span>}
      </span>
    </label>
  );
}
