import { useState } from "react";
import { call, usePoll, type Status } from "../api";

interface ConfigResp {
  ok: boolean;
  home: string;
  config: { mode: string; ask_route: string; ask_timeout_secs: number; checkpoint_every: number; checkpoint_secs: number; witness_dir: string | null };
}

function Choice({ value, options, onChange }: { value: string; options: [string, string][]; onChange: (v: string) => void }) {
  return (
    <div className="segmented">
      {options.map(([v, label]) => (
        <button key={v} aria-selected={value === v} onClick={() => onChange(v)}>
          {label}
        </button>
      ))}
    </div>
  );
}

export function SettingsScreen({ status }: { status: Status | null }) {
  const { data, refresh } = usePoll(() => call<ConfigResp>("config_get"), 4000);
  const set = async (args: Record<string, string>) => {
    await call("config_set", args);
    refresh();
  };
  const c = data?.config;
  const { data: integ, refresh: refreshInteg } = usePoll(
    () => call<{ ok: boolean; settings: string; installed: boolean | null; error: string | null; hook: string | null }>("integration_status"),
    5000,
  );
  const [msg, setMsg] = useState<string | null>(null);
  const integrate = async (action: "install" | "uninstall") => {
    const r = await call<{ ok: boolean; error?: string; changed?: number }>("integrate", { action });
    setMsg(r.ok ? (action === "install" ? "Ulandi. Yangi Claude Code sessiyalari TAMGA orqali yoziladi." : `Ajratildi: ${r.changed} ta hook olib tashlandi.`) : (r.error ?? "xato"));
    refreshInteg();
  };
  return (
    <div className="page settings">
      <section>
        <h3>Claude Code integratsiyasi</h3>
        <p className="dim">
          TAMGA hook'lari foydalanuvchi sozlamalariga (<span className="mono">{integ?.settings ?? "~/.claude/settings.json"}</span>) qo'shiladi. Boshqa
          sozlamalaringiz saqlanadi, avval zaxira nusxa yoziladi. Faqat yangi ochilgan sessiyalarga ta'sir qiladi.
        </p>
        <div className="actions-row">
          <span className={`pill ${integ?.installed ? "allow" : "muted"}`}>{integ?.installed ? "ulangan" : "ulanmagan"}</span>
          {integ?.installed ? (
            <button className="btn" onClick={() => void integrate("uninstall")}>
              Ajratish
            </button>
          ) : (
            <button className="btn primary" disabled={!integ?.hook} onClick={() => void integrate("install")}>
              Claude Code'ga ulash
            </button>
          )}
          {!integ?.hook && <span className="dim">tamga-hook.exe topilmadi (o'rnatilgan nusxada bo'ladi)</span>}
        </div>
        {msg && <p className="verdict-note" style={{ marginTop: 8 }}>{msg}</p>}
      </section>
      <section>
        <h3>Daemon ishlamasa</h3>
        <p className="dim">Hook daemon'ga ulana olmasa: hodisa spool'ga yoziladi va keyin jurnalga tushadi.</p>
        <Choice
          value={c?.mode ?? "dev"}
          options={[
            ["dev", "Ruxsat berish (dev)"],
            ["strict", "Bloklash (strict)"],
          ]}
          onChange={(v) => void set({ mode: v })}
        />
      </section>
      <section>
        <h3>«ask» qarorlarini kim beradi</h3>
        <p className="dim">
          Agent — Claude Code o'z oynasida so'raydi. Studio — agent sizning shu ilovadagi javobingizni kutadi ({c?.ask_timeout_secs ?? 120} s, keyin rad).
        </p>
        <Choice
          value={c?.ask_route ?? "agent"}
          options={[
            ["agent", "Agent oynasi"],
            ["studio", "TAMGA Studio"],
          ]}
          onChange={(v) => void set({ askRoute: v })}
        />
      </section>
      <section>
        <h3>OS sensori ("aytdi va qildi")</h3>
        {status?.sensor ? (
          <>
            <p className="dim">
              Admin huquqisiz: jarayonlar va TCP ulanishlari har {status.sensor.poll_ms} ms da, fayl o'zgarishlari {status.sensor.watched_dirs.length} ta
              papkada. Kuzatilayotgan agentlar: {status.sensor.roots.length}.
            </p>
            <span className="label">Ko'r nuqtalar (halol chegaralar)</span>
            <ul className="blind">
              {status.sensor.blind_spots.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="dim">Sensor o'chiq yoki daemon ulanmagan.</p>
        )}
      </section>
      <section className="kv">
        <span className="label">TAMGA papkasi</span>
        <span className="mono wrap">{data?.home}</span>
        <span className="label">Jurnal</span>
        <span className="mono">{status?.log ?? "—"}</span>
        <span className="label">Imzo kaliti</span>
        <span className="mono">{status?.key ?? "—"}</span>
        <span className="label">Checkpoint</span>
        <span>
          har {c?.checkpoint_every ?? 32} yozuvda yoki {c?.checkpoint_secs ?? 30} s da
        </span>
        <span className="label">Guvoh papkasi</span>
        <span className="mono">{c?.witness_dir ?? "sozlanmagan"}</span>
      </section>
    </div>
  );
}
