import { useState } from "react";
import { RefreshCw, ShieldAlert, ShieldCheck, Stamp } from "lucide-react";
import { call, dateTime, usePoll, type Integrity } from "../api";

/** Yaxlitlik: zanjir + checkpoint'lar + gibrid imzolar tekshiruvi (tamga-verify bilan bir xil algoritm). */
export function IntegrityScreen() {
  const { data, error, refresh } = usePoll(() => call<Integrity>("verify"), 10000);
  const [busy, setBusy] = useState(false);
  const [checked, setChecked] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      refresh();
      setChecked(new Date().toLocaleTimeString("uz-UZ", { hour12: false }));
    } finally {
      setBusy(false);
    }
  };

  const d = data;
  const unsealed = d?.ok && d.records !== undefined && d.sealed !== undefined ? d.records - d.sealed : 0;
  return (
    <div className="page">
      <div className="actions-row" style={{ marginBottom: 16 }}>
        <button className="btn primary" disabled={busy} onClick={() => void run(async () => {})}>
          <RefreshCw size={15} /> Hozir tekshirish
        </button>
        <button className="btn" disabled={busy} onClick={() => void run(() => call("checkpoint_now"))}>
          <Stamp size={15} /> Checkpoint imzolash
        </button>
        {checked && <span className="dim">oxirgi tekshiruv {checked}</span>}
      </div>

      {error && <div className="verdict-card bad">{error}</div>}
      {d && d.ok && (
        <div className="verdict-card good">
          <ShieldCheck size={34} />
          <div>
            <h2>Jurnal butun</h2>
            <p>
              {d.records} yozuv, zanjir uzilmagan. {d.checkpoints?.length ?? 0} ta checkpoint Ed25519 + ML-DSA-65 bilan tasdiqlandi.
              {unsealed > 0 ? ` Oxirgi ${unsealed} yozuv hali checkpoint bilan muhrlanmagan.` : " Barcha yozuvlar muhrlangan."}
            </p>
          </div>
        </div>
      )}
      {d && !d.ok && (
        <div className="verdict-card bad">
          <ShieldAlert size={34} />
          <div>
            <h2>Buzilish aniqlandi: {d.error?.code}</h2>
            <p>
              Indeks {d.error?.index}: {d.error?.detail}
            </p>
          </div>
        </div>
      )}

      {d && (
        <div className="grid2">
          <div className="kv">
            <span className="label">Jurnal</span>
            <span className="mono">{d.log}</span>
            <span className="label">{(d.keys?.length ?? 0) > 1 ? "Kalitlar zanjiri" : "Imzo kaliti"}</span>
            <span className="mono wrap">{(d.keys?.length ?? 0) > 1 ? d.keys!.join(" → ") : d.key}</span>
            <span className="label">Algoritm</span>
            <span>SHA-256 zanjir · RFC 9162 Merkle · Ed25519 + ML-DSA-65 (ikkalasi shart)</span>
            {d.warnings?.length || d.key_warnings?.length ? (
              <>
                <span className="label">Ogohlantirishlar</span>
                {[...(d.warnings ?? []), ...(d.key_warnings ?? [])].map((w) => (
                  <span key={w} className="dim">
                    {w}
                  </span>
                ))}
              </>
            ) : null}
          </div>
          <div>
            <span className="label">Checkpoint'lar</span>
            <table className="table">
              <thead>
                <tr>
                  <th>O'lcham</th>
                  <th>Vaqt</th>
                  <th>Merkle ildizi</th>
                </tr>
              </thead>
              <tbody>
                {(d.checkpoints ?? [])
                  .slice()
                  .reverse()
                  .map((c) => (
                    <tr key={`${c.size}-${c.ts}`}>
                      <td className="mono">{c.size}</td>
                      <td className="mono">{dateTime(c.ts)}</td>
                      <td className="mono" title={c.root}>
                        {c.root.slice(7, 23)}…
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
