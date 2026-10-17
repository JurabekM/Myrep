import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, History } from "lucide-react";
import { call, dateTime, EVENT_LABEL, time, usePoll, type Rec, type SessionSummary } from "../api";
import { ErrorBanner, Facts, RecordDetail, VerdictPill } from "../components";

/** Sessiyalar ro'yxati va Claude Code transkriptiga o'xshash qayta o'ynatish. */
export function SessionsScreen() {
  const { data, error } = usePoll(() => call<{ ok: boolean; error?: string; items: SessionSummary[] }>("sessions"), 3000);
  const [active, setActive] = useState<string | null>(null);
  const items = data?.items ?? [];
  const current = active ?? items[0]?.session ?? null;

  if (error) return <ErrorBanner text={error} />;
  return (
    <div className="split">
      <div className="session-list scroll">
        {items.length === 0 && <p className="empty-note">Hali sessiya yo'q.</p>}
        {items.map((s) => (
          <button key={s.session} className="session-item" aria-selected={s.session === current} onClick={() => setActive(s.session)}>
            <span className="mono">{s.session.slice(0, 13)}…</span>
            <span className="dim">{dateTime(s.first)}</span>
            <span className="session-stats">
              <span>{s.tools} tool</span>
              {s.deny > 0 && <span className="pill deny">{s.deny} deny</span>}
              {s.ask > 0 && <span className="pill ask">{s.ask} ask</span>}
              {!s.ended && <span className="pill allow">faol</span>}
            </span>
          </button>
        ))}
      </div>
      {current ? <Timeline session={current} /> : <section className="empty"><History size={40} strokeWidth={1.25} /><h2>Sessiya tanlang</h2></section>}
    </div>
  );
}

function Timeline({ session }: { session: string }) {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => call<{ items: Rec[] }>("session_records", { session }).then((r) => alive && setRecs(r.items));
    void load();
    const id = window.setInterval(() => void load(), 2000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [session]);

  // tool.post va decision.human o'z tool.pre bloki ichida ko'rsatiladi.
  const children = (seq: number) => recs.filter((r) => r.ref === seq);
  const top = recs.filter((r) => !(r.ref !== null && r.ref !== undefined && recs.some((p) => p.seq === r.ref)));

  return (
    <div className="timeline scroll">
      <div className="transcript">
        {top.map((r) => {
          if (r.event !== "tool.pre") {
            return (
              <div key={r.seq} className="t-event">
                <span className="dot-sm" />
                <span>{EVENT_LABEL[r.event] ?? r.event}</span>
                {r.model && <span className="dim mono">{r.model}</span>}
                <span className="dim mono" style={{ marginLeft: "auto" }}>
                  #{r.seq} · {time(r.ts)}
                </span>
              </div>
            );
          }
          const kids = children(r.seq);
          const isOpen = open === r.seq;
          const final = kids.find((k) => k.event === "decision.human");
          return (
            <div key={r.seq} className={`t-tool ${r.verdict ?? ""}`}>
              <button className="t-head" onClick={() => setOpen(isOpen ? null : r.seq)} aria-expanded={isOpen}>
                {isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                <b>{r.tool}</b>
                <Facts facts={r.facts} max={3} />
                <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                  <VerdictPill verdict={r.verdict} by={r.by} />
                  {final && <VerdictPill verdict={final.verdict} by={final.by} />}
                </span>
                <span className="dim mono">#{r.seq}</span>
              </button>
              {isOpen && (
                <div className="t-body detail-inline">
                  <RecordDetail rec={r} />
                  {kids.map((k) => (
                    <div key={k.seq} className="t-child">
                      <RecordDetail rec={k} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
