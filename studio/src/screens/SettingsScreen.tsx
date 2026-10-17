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
  return (
    <div className="page settings">
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
