import { useState } from "react";
import { AlertTriangle, FileArchive, FolderOpen, PackageCheck } from "lucide-react";
import { call, dateTime, usePoll, type SessionSummary } from "../api";
import { ErrorBanner } from "../components";

interface ExportResult {
  ok: boolean;
  path: string;
  records: number;
  checkpoints: number;
  payloads: number;
  shredded: number;
  verified: boolean;
  sha256: string;
}

interface ExportsList {
  ok: boolean;
  dir: string;
  items: { path: string; name: string; size: number; ts: string }[];
}

function kb(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
}

/** Auditor uchun dalil to'plami: jurnal + checkpoint'lar + kalit + mustaqil Python verifikatori (+ payload'lar). */
export function ReportsScreen() {
  const { data: sessions } = usePoll(() => call<{ items: SessionSummary[] }>("sessions"), 5000);
  const { data: exports, refresh } = usePoll(() => call<ExportsList>("list_exports"), 5000);
  const [picked, setPicked] = useState<string[]>([]);
  const [payloads, setPayloads] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = (s: string) => setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));
  const items = sessions?.items ?? [];
  const totals = items.reduce((a, s) => ({ tools: a.tools + s.tools, deny: a.deny + s.deny, ask: a.ask + s.ask }), { tools: 0, deny: 0, ask: 0 });

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await call<ExportResult>("export_bundle", { sessions: picked, includePayloads: payloads }));
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const reveal = (path: string) => void call("reveal", { path });

  return (
    <div className="page reports">
      <div className="kpis">
        <div><b>{items.length}</b>sessiya</div>
        <div><b>{totals.tools}</b>tool so'rovi</div>
        <div><b className="deny-text">{totals.deny}</b>bloklangan</div>
        <div><b className="ask-text">{totals.ask}</b>ask</div>
      </div>

      <section className="card export-card">
        <header>
          <PackageCheck size={18} />
          <b>Dalil to'plami</b>
        </header>
        <p className="dim">
          ZIP ichida: to'liq jurnal, imzolangan checkpoint'lar, ochiq kalit, HTML xulosa va <b>mustaqil Python verifikatori</b> — auditor TAMGA'ga
          ishonmasdan, faqat Python bilan tekshiradi.
        </p>

        <span className="label">Payload'lar qaysi sessiyalardan (tanlanmasa — hammasidan)</span>
        <div className="session-picks">
          {items.map((s) => (
            <label key={s.session} className={`pick ${picked.includes(s.session) ? "on" : ""}`}>
              <input type="checkbox" checked={picked.includes(s.session)} onChange={() => toggle(s.session)} aria-label={`sessiya ${s.session}`} />
              <span className="mono">{s.session.slice(0, 13)}…</span>
              <span className="dim">{dateTime(s.first)}</span>
              <span className="dim">{s.tools} tool</span>
              {s.deny > 0 && <span className="pill deny">{s.deny} deny</span>}
            </label>
          ))}
        </div>

        <label className="toggle">
          <input type="checkbox" checked={payloads} onChange={(e) => setPayloads(e.target.checked)} aria-label="Payload'larni qo'shish" />
          Payload'larni qo'shish (buyruqlar, fayl mazmuni, natijalar)
        </label>
        {payloads && (
          <div className="banner danger" style={{ margin: "8px 0 0" }}>
            <AlertTriangle size={16} />
            Payload'lar ochiq matnda qo'shiladi — ichidagi maxfiy qiymatlar ham. Auditor jurnaldagi tuzlangan digest bilan solishtira olishi uchun ular
            yashirilmaydi. To'plamni faqat ishonchli auditorga bering.
          </div>
        )}

        <div className="actions-row" style={{ marginTop: 16 }}>
          <button className="btn primary" disabled={busy} onClick={() => void run()}>
            <FileArchive size={15} /> {busy ? "Yaratilmoqda…" : "Dalil to'plamini yaratish"}
          </button>
        </div>
        {error && <ErrorBanner text={error} />}
        {result && (
          <div className={`verdict-card ${result.verified ? "good" : "bad"}`} style={{ marginTop: 16, marginBottom: 0 }}>
            <PackageCheck size={28} />
            <div style={{ minWidth: 0 }}>
              <h2>{result.verified ? "To'plam tayyor — jurnal butun" : "To'plam tayyor — jurnalda BUZILISH bor (MANIFEST.json)"}</h2>
              <p>
                {result.records} yozuv · {result.checkpoints} checkpoint · {result.payloads} payload
                {result.shredded ? ` · ${result.shredded} unutilgan` : ""}
              </p>
              <p className="mono wrap" style={{ fontSize: 12 }}>
                {result.sha256}
              </p>
            </div>
            <button className="btn" style={{ marginLeft: "auto" }} onClick={() => reveal(result.path)}>
              <FolderOpen size={15} /> Papkada ko'rsatish
            </button>
          </div>
        )}
      </section>

      <section>
        <span className="label">Avvalgi to'plamlar</span>
        <table className="table">
          <thead>
            <tr>
              <th>Fayl</th>
              <th>Vaqt</th>
              <th>Hajm</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(exports?.items ?? []).map((e) => (
              <tr key={e.path}>
                <td className="mono">{e.name}</td>
                <td className="mono">{dateTime(e.ts)}</td>
                <td>{kb(e.size)}</td>
                <td>
                  <button className="btn" onClick={() => reveal(e.path)} aria-label={`${e.name} papkada ko'rsatish`}>
                    <FolderOpen size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {exports && exports.items.length === 0 && (
              <tr>
                <td colSpan={4} className="dim">
                  Hali to'plam yaratilmagan.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
