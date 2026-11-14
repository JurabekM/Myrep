import { useState } from "react";
import { Hand, Info } from "lucide-react";
import { call, time, usePoll, type PendingItem } from "../api";
import { ErrorBanner, Facts } from "../components";

interface PendingResp {
  ok: boolean;
  error?: string;
  route: "studio" | "agent";
  items: PendingItem[];
}

/** Tasdiqlash navbati: `ask` qarorlari inson javobini kutadi (ask_route = studio). */
export function ApprovalsScreen({ onRouteChange }: { onRouteChange: () => void }) {
  const { data, error, refresh } = usePoll(() => call<PendingResp>("pending"), 1000);
  const [busy, setBusy] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const decide = async (seq: number, verdict: "allow" | "deny", scope: "once" | "session") => {
    setBusy(seq);
    try {
      const r = await call<{ ok: boolean; error?: string; record?: number }>("decide", { seq, verdict, scope });
      setNotice(r.ok ? `#${seq}: qaror #${r.record} yozuvi bo'lib zanjirga muhrlandi.` : (r.error ?? "xato"));
    } catch (e) {
      setNotice(String(e));
    } finally {
      setBusy(null);
      refresh();
    }
  };

  const enableStudio = async () => {
    await call("config_set", { askRoute: "studio" });
    onRouteChange();
    refresh();
  };

  if (error) return <ErrorBanner text={`Daemon bilan aloqa yo'q: ${error}`} />;
  if (data && !data.ok) return <ErrorBanner text={`Daemon bilan aloqa yo'q: ${data.error}`} />;
  const items = data?.items ?? [];
  return (
    <div className="page">
      {data?.route === "agent" && (
        <div className="banner">
          <Info size={16} />
          <span>
            Hozir <b>ask</b> qarorlarini agentning o'zi (Claude Code oynasi) so'raydi. Headless agentlar (<span className="mono">claude -p</span>, CI)
            uchun qarorni shu yerga yo'naltiring.
          </span>
          <button className="btn" style={{ marginLeft: "auto" }} onClick={() => void enableStudio()}>
            Studio'ga yo'naltirish
          </button>
        </div>
      )}
      {notice && (
        <div className="banner ok" onClick={() => setNotice(null)}>
          {notice}
        </div>
      )}
      {items.length === 0 ? (
        <section className="empty">
          <Hand size={40} strokeWidth={1.25} />
          <h2>Navbat bo'sh</h2>
          <p>Siyosat «ask» degan harakat paydo bo'lsa, agent shu yerda sizning qaroringizni kutadi.</p>
        </section>
      ) : (
        <div className="cards">
          {items.map((p) => (
            <article key={p.seq} className="card">
              <header>
                <span className="pill ask">ask</span>
                <b>{p.tool}</b>
                <span className="mono dim">#{p.seq}</span>
                <span className="dim" style={{ marginLeft: "auto" }}>
                  {time(p.ts)} · {p.expires_in_secs} s qoldi
                </span>
              </header>
              <div className="timer">
                <div style={{ width: `${Math.max(0, Math.min(100, (p.expires_in_secs / (p.expires_in_secs + p.age_secs || 1)) * 100))}%` }} />
              </div>
              <div className="codeblock mono">{p.preview}</div>
              <span className="mono" style={{ color: "var(--ask)" }}>
                {p.policy}
              </span>
              <span className="verdict-note">{p.reason}</span>
              <Facts facts={p.facts} />
              <span className="dim mono">sessiya {p.session}</span>
              <div className="actions-row">
                <button className="btn primary" disabled={busy === p.seq} onClick={() => void decide(p.seq, "allow", "once")}>
                  Ruxsat
                </button>
                <button className="btn" disabled={busy === p.seq} onClick={() => void decide(p.seq, "allow", "session")}>
                  Shu sessiyada doim
                </button>
                <button className="btn danger" disabled={busy === p.seq} onClick={() => void decide(p.seq, "deny", "once")}>
                  Rad etish
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
