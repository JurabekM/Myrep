import { useMutation, useQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import { commands, type SettingsDto } from "../../bindings";
import { ErrorText } from "../../components/ErrorText";
import { LOCALES } from "../../i18n";
import { call } from "../../lib/api";
import { FONT_SCALES, loadPrefs, savePrefs, type Theme } from "../../lib/prefs";
import { keys } from "../../lib/queryClient";
import { RHYTHMS } from "../setup/SetupScreen";

/** Sozlamalar: til (shu qurilma), ko'rinish (shrift, mavzu), daromad ritmi, qarz eslatmasi. */
export function SettingsScreen() {
  const { t, i18n } = useTranslation();
  const settings = useQuery({ queryKey: keys.settings, queryFn: () => call(commands.settings()) });
  const [display, setDisplay] = useState(loadPrefs);
  const save = useMutation({
    mutationFn: (patch: Partial<SettingsDto>) => {
      const cur = settings.data;
      return call(
        commands.updateSettings({
          locale: patch.deviceLocale !== undefined ? patch.deviceLocale : (cur?.deviceLocale ?? null),
          incomeRhythm: patch.incomeRhythm !== undefined ? patch.incomeRhythm : (cur?.incomeRhythm ?? null),
          debtsDeclared: patch.debtsDeclared ?? cur?.debtsDeclared ?? false,
        }),
      );
    },
    onSuccess: (s) => {
      if (s.locale !== i18n.language) void i18n.changeLanguage(s.locale);
    },
  });
  const s = settings.data;

  return (
    <section className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("settings.title")}</h1>
      <ErrorText error={save.error} />

      <Card title={t("settings.language")} hint={t("settings.languageHint")}>
        <div role="radiogroup" aria-label={t("settings.language")} className="flex flex-wrap gap-2">
          {LOCALES.map((l) => (
            <Option key={l} name="locale" checked={(s?.locale ?? i18n.language) === l} onChange={() => save.mutate({ deviceLocale: l })}>
              {t(`locale.${l}`)}
            </Option>
          ))}
        </div>
      </Card>

      <Card title={t("settings.display")} hint={t("settings.displayHint")}>
        <div role="radiogroup" aria-label={t("settings.fontSize")} className="flex flex-wrap items-center gap-2">
          <span className="label w-full">{t("settings.fontSize")}</span>
          {FONT_SCALES.map((f) => (
            <Option key={f} name="font" checked={display.fontScale === f} onChange={() => setDisplay(savePrefs({ fontScale: f }))}>
              {f}%
            </Option>
          ))}
        </div>
        <div role="radiogroup" aria-label={t("settings.theme")} className="flex flex-wrap items-center gap-2">
          <span className="label w-full">{t("settings.theme")}</span>
          {(["dark", "light"] as Theme[]).map((th) => (
            <Option key={th} name="theme" checked={display.theme === th} onChange={() => setDisplay(savePrefs({ theme: th }))}>
              {t(`settings.theme.${th}`)}
            </Option>
          ))}
        </div>
        <p className="text-sm text-ink-muted">{t("settings.highContrast")}</p>
      </Card>

      <Card title={t("settings.rhythm")} hint={t("settings.rhythmHint")}>
        <div role="radiogroup" aria-label={t("settings.rhythm")} className="flex flex-col gap-2">
          {RHYTHMS.map((r) => (
            <Option key={r} name="rhythm" checked={s?.incomeRhythm === r} onChange={() => save.mutate({ incomeRhythm: r })}>
              {t(`rhythm.${r}`)} <span className="text-ink-muted">— {t(`rhythmHint.${r}`)}</span>
            </Option>
          ))}
          <Option name="rhythm" checked={s !== undefined && s.incomeRhythm === null} onChange={() => save.mutate({ incomeRhythm: null })}>
            {t("rhythm.NONE")}
          </Option>
        </div>
      </Card>

      <Card title={t("settings.debts")}>
        <label className="flex items-start gap-3">
          <input type="checkbox" className="mt-1" checked={s?.debtsDeclared ?? false} onChange={(e) => save.mutate({ debtsDeclared: e.target.checked })} />
          <span>{t("settings.debtsReminder")}</span>
        </label>
      </Card>

      <Card title={t("settings.keyboard")}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          {(["Ctrl+N", "Ctrl+L", "Tab", "Esc"] as const).map((k) => (
            <div key={k} className="contents">
              <dt>
                <kbd className="rounded border border-field-line px-1.5 py-0.5 font-mono text-xs">{k}</kbd>
              </dt>
              <dd className="text-ink-muted">{t(`settings.key.${k}`)}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </section>
  );
}

function Card({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="card flex flex-col gap-3" aria-label={title}>
      <h2 className="text-lg font-semibold">{title}</h2>
      {hint && <p className="text-sm text-ink-muted">{hint}</p>}
      {children}
    </section>
  );
}

function Option({ name, checked, onChange, children }: { name: string; checked: boolean; onChange: () => void; children: ReactNode }) {
  return (
    <label className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 ${checked ? "border-accent bg-paper" : "border-field-line"}`}>
      <input type="radio" name={name} checked={checked} onChange={onChange} />
      <span>{children}</span>
    </label>
  );
}
