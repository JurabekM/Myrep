import { useEffect, useMemo, useRef, useState } from "react";
import { Eye, Lock, Search } from "lucide-react";
import { call, time, type Rec } from "../api";
import { ErrorBanner, Facts, OsPill, osWhat, RecordDetail, recTitle, VerdictPill } from "../components";

interface RecordsResp {
  ok: boolean;
  error?: string;
  total: number;
  items: Rec[];
}

const FILTERS = [
  { id: "all", label: "Hammasi" },
  { id: "tools", label: "Tool'lar" },
  { id: "blocked", label: "Bloklangan" },
  { id: "ask", label: "Ask" },
  { id: "os", label: "Nomuvofiq" },
] as const;

/** Jonli oqim: har soniyada faqat yangi yozuvlar so'raladi. */
export function LiveScreen() {
  const [recs, setRecs] = useState<Rec[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Rec | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const last = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = () =>
      call<RecordsResp>("records", last.current === null ? { limit: 400 } : { after: last.current, limit: 400 })
        .then((r) => {
          if (!alive) return;
          if (!r.ok) return setError(r.error ?? "xato");
          setError(null);
          if (r.items.length) {
            last.current = r.items[r.items.length - 1]!.seq;
            setRecs((prev) => [...prev, ...r.items].slice(-1000));
          }
        })
        .catch((e: unknown) => alive && setError(String(e)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return recs
      .filter((r) => {
        if (filter === "tools" && r.event !== "tool.pre") return false;
        if (filter === "blocked" && r.verdict !== "deny") return false;
        if (filter === "ask" && r.verdict !== "ask" && r.event !== "decision.human") return false;
        if (filter === "os" && r.os?.severity !== "warn") return false;
        if (!q) return true;
        return `${r.tool ?? ""} ${r.event} ${r.policy ?? ""} ${r.session} ${(r.facts ?? []).join(" ")}`.toLowerCase().includes(q);
      })
      .reverse();
  }, [recs, query, filter]);

  return (
    <div className="live">
      <div className="live-list">
        {error && <ErrorBanner text={`Jurnal o'qilmadi: ${error}`} />}
        <div className="toolbar">
          <label className="field">
            <Search size={16} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Bash, no-secret-exfil, sessiya…" aria-label="Filtrlash" />
          </label>
          <div className="segmented" role="tablist">
            {FILTERS.map((f) => (
              <button key={f.id} role="tab" aria-selected={filter === f.id} onClick={() => setFilter(f.id)}>
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div role="listbox" aria-label="Agent harakatlari" className="scroll">
          {visible.map((r) => (
            <button key={r.seq} role="option" className="row" aria-selected={selected?.seq === r.seq} onClick={() => setSelected(r)}>
              <span className="mono time">{time(r.ts)}</span>
              <span className={r.event === "tool.pre" ? "" : "dim"}>{recTitle(r)}</span>
              <span className="cmd">
                <Facts facts={r.facts} max={2} />
                {r.os && <span className={`mono ${r.os.severity === "warn" ? "warn-text" : "dim"}`}>{osWhat(r.os)}</span>}
                {!r.facts?.length && !r.os && <span className="dim mono">{r.policy ?? (r.event === "tool.post" ? `#${r.ref ?? "?"} natijasi` : r.session.slice(0, 8))}</span>}
              </span>
              {r.os ? <OsPill o={r.os} /> : <VerdictPill verdict={r.verdict} by={r.by} />}
              {r.event === "os.observed" ? <Eye size={15} color="var(--warning)" /> : <Lock size={15} color="var(--success)" aria-label="Muhrlangan" />}
            </button>
          ))}
          {visible.length === 0 && !error && (
            <p className="empty-note">{recs.length ? "Filtrga mos yozuv yo'q." : "Hali yozuv yo'q. Claude Code'da ish boshlang: harakatlar shu yerda paydo bo'ladi."}</p>
          )}
        </div>
      </div>
      <aside className="detail" aria-label="Yozuv tafsiloti">
        <RecordDetail rec={selected} />
      </aside>
    </div>
  );
}
