import { useEffect, useState } from "react";
import { AlertTriangle, CircleCheck, Lock, Trash2 } from "lucide-react";
import { call, dateTime, EVENT_LABEL, FACT_LABEL, type OsObs, type Payload, type Rec } from "./api";

export function VerdictPill({ verdict, by }: { verdict: string | null; by?: string | null }) {
  if (!verdict) return <span className="pill muted">—</span>;
  const label = verdict === "ask" ? "ask" : verdict;
  return (
    <span className={`pill ${verdict}`} title={by ? `qaror: ${by}` : undefined}>
      {label}
      {by === "human" ? " · inson" : ""}
    </span>
  );
}

export function Facts({ facts, max }: { facts: string[] | null; max?: number }) {
  if (!facts?.length) return null;
  const shown = max ? facts.slice(0, max) : facts;
  const rest = facts.length - shown.length;
  return (
    <div className="facts" title={facts.map((f) => FACT_LABEL[f] ?? f).join(", ")}>
      {shown.map((f) => (
        <span key={f} className={`fact ${f.includes("secret") || f.includes("destructive") ? "hot" : ""}`}>
          {FACT_LABEL[f] ?? f}
        </span>
      ))}
      {rest > 0 && <span className="fact">+{rest}</span>}
    </div>
  );
}

/** Yozuv nomi: tool nomi yoki hodisa turi. */
export function recTitle(r: Rec): string {
  if (r.tool) return r.tool;
  if (r.os) return r.os.image ?? (r.os.kind === "file" ? "fayl" : "OS");
  return EVENT_LABEL[r.event] ?? r.event;
}

const OS_KIND: Record<string, string> = { process: "jarayon", network: "tarmoq", file: "fayl" };

/** OS kuzatuvining qisqa tavsifi: nima qilingan. */
export function osWhat(o: OsObs): string {
  if (o.kind === "network") return `${o.image ?? ""} → ${o.remote ?? ""}`;
  if (o.kind === "file") return `${o.op ?? ""} ${o.path ?? ""}`;
  return `${o.image ?? ""}${o.pid ? ` (PID ${o.pid})` : ""}`;
}

/** "Aytdi va qildi" belgisi: aytilgan / aytilmagan / nomuvofiq. */
export function OsPill({ o }: { o: OsObs }) {
  const cls = o.severity === "warn" ? "deny" : o.declared ? "allow" : "muted";
  const label = o.severity === "warn" ? "nomuvofiq" : o.declared ? "aytilgan" : "aytilmagan";
  return (
    <span className={`pill ${cls}`} title={o.mismatch ?? undefined}>
      {OS_KIND[o.kind]} · {label}
    </span>
  );
}

/** Tool chaqiruvi ostida: agent aytgani va OS ko'rgani. */
export function SaidDid({ kids }: { kids: Rec[] }) {
  const obs = kids.filter((k) => k.os);
  if (!obs.length) return <p className="verdict-note">OS sensori bu chaqiruv paytida qo'shimcha jarayon, ulanish yoki fayl o'zgarishini ko'rmadi.</p>;
  return (
    <div className="said-did">
      {obs.map((k) => (
        <div key={k.seq} className={`did-row ${k.os!.severity === "warn" ? "warn" : ""}`}>
          <OsPill o={k.os!} />
          <span className="mono wrap">{osWhat(k.os!)}</span>
          {k.os!.mismatch && <span className="did-why">{k.os!.mismatch}</span>}
          <span className="dim mono" style={{ marginLeft: "auto" }}>
            #{k.seq}
          </span>
        </div>
      ))}
    </div>
  );
}

interface Detail {
  ok: boolean;
  error?: string;
  record?: Record<string, unknown>;
  payloads?: Payload[];
}

/** Tanlangan yozuv tafsiloti: qaror, faktlar, xesh va vault'dagi payload'lar (sirlar yashirilgan). */
export function RecordDetail({ rec }: { rec: Rec | null }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  useEffect(() => {
    setDetail(null);
    if (!rec) return;
    let alive = true;
    call<Detail>("record_detail", { seq: rec.seq })
      .then((d) => alive && setDetail(d))
      .catch((e: unknown) => alive && setDetail({ ok: false, error: String(e) }));
    return () => {
      alive = false;
    };
  }, [rec]);

  if (!rec) return <p className="verdict-note">Yozuvni tanlang.</p>;
  return (
    <>
      <h2>
        #{rec.seq} · {recTitle(rec)}
      </h2>
      <span className="verdict-note">{EVENT_LABEL[rec.event] ?? rec.event}</span>
      {rec.verdict && (
        <>
          <span className="label">Qaror</span>
          <span>
            <VerdictPill verdict={rec.verdict} by={rec.by} />
          </span>
          {rec.policy && (
            <span className="mono" style={{ color: "var(--ask)" }}>
              {rec.policy}
            </span>
          )}
          {rec.reason && <span className="verdict-note">{rec.reason}</span>}
        </>
      )}
      {rec.os && (
        <>
          <span className="label">OS kuzatuvi (qildi)</span>
          <span>
            <OsPill o={rec.os} />
          </span>
          <span className="mono wrap">{osWhat(rec.os)}</span>
          {rec.os.mismatch && <span className="verdict-note" style={{ color: rec.os.severity === "warn" ? "var(--danger)" : undefined }}>{rec.os.mismatch}</span>}
        </>
      )}
      {rec.facts?.length ? (
        <>
          <span className="label">Faktlar</span>
          <Facts facts={rec.facts} />
        </>
      ) : null}
      {rec.ref !== null && rec.ref !== undefined && (
        <>
          <span className="label">Bog'liq yozuv</span>
          <span className="mono">#{rec.ref}</span>
        </>
      )}
      {detail?.payloads?.map((p) => (
        <div key={p.name} style={{ display: "contents" }}>
          <span className="label">{p.name === "input" ? "Kirish (vault)" : "Natija (vault)"}</span>
          {p.status === "ok" ? (
            <div className="codeblock mono">{p.text || "(bo'sh)"}</div>
          ) : p.status === "shredded" ? (
            <span className="verdict-note">
              <Trash2 size={13} /> Unutilgan (shred): jurnal baribir tasdiqlanadi.
            </span>
          ) : (
            <span className="verdict-note" style={{ color: "var(--danger)" }}>
              {p.text}
            </span>
          )}
        </div>
      ))}
      {detail && !detail.ok && <span className="verdict-note">{detail.error}</span>}
      <span className="label">Vaqt</span>
      <span className="mono">{dateTime(rec.ts)}</span>
      <span className="label">Sessiya</span>
      <span className="mono wrap">{rec.session}</span>
      <span className="label">Xesh</span>
      <span className="mono wrap" title={rec.hash}>
        {rec.hash}
      </span>
      <span className="verdict-note" style={{ marginTop: 10 }}>
        <Lock size={13} /> Zanjirga muhrlangan, o'zgartirib bo'lmaydi.
      </span>
    </>
  );
}

export function ErrorBanner({ text }: { text: string }) {
  return (
    <div className="banner danger">
      <AlertTriangle size={16} />
      {text}
    </div>
  );
}

export function OkBanner({ text }: { text: string }) {
  return (
    <div className="banner ok">
      <CircleCheck size={16} />
      {text}
    </div>
  );
}
