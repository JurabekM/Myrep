import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useRef, useState } from "react";

export type Verdict = "allow" | "deny" | "ask";

/** Jurnal yozuvining ixcham ko'rinishi (`data::compact`). */
export interface Rec {
  seq: number;
  ts: string;
  session: string;
  event: string;
  tool: string | null;
  verdict: Verdict | null;
  by: string | null;
  policy: string | null;
  reason: string | null;
  ref: number | null;
  hash: string;
  facts: string[] | null;
  spooled: boolean | null;
  model: string | null;
  agent: string | null;
  /** OS sensori kuzatuvi (`os.observed`): "qildi". */
  os: OsObs | null;
}

export interface OsObs {
  kind: "process" | "network" | "file";
  image?: string;
  pid?: number;
  remote?: string;
  path?: string;
  op?: string;
  declared: boolean;
  mismatch?: string;
  severity: "info" | "warn";
}

export interface PendingItem {
  seq: number;
  ts: string;
  session: string;
  tool: string;
  policy: string;
  reason: string;
  facts: string[];
  preview: string;
  age_secs: number;
  expires_in_secs: number;
}

export interface SessionSummary {
  session: string;
  first: string;
  last: string;
  agent: string;
  events: number;
  tools: number;
  deny: number;
  ask: number;
  ended: boolean;
}

export interface Payload {
  name: "input" | "result";
  status: "ok" | "shredded" | "error";
  text: string;
  digest: string;
  size: number;
}

export interface Integrity {
  ok: boolean;
  log?: string;
  key?: string;
  records?: number;
  sealed?: number;
  checkpoints?: { size: number; ts: string; root: string }[];
  warnings?: string[];
  error?: { code: string; index: number; detail: string };
}

export interface PolicyRow {
  id: string;
  source: string;
  effect: "permit" | "forbid";
  verdict: Verdict;
  reason: string;
  text: string;
}

export interface Status {
  ok: boolean;
  error?: string;
  log?: string;
  records?: number;
  checkpointed?: number;
  key?: string;
  home?: string;
  mode?: string;
  pending?: number;
  policy_count?: number;
  policy_error?: string | null;
  tainted_sessions?: number;
  config?: { ask_route: string; ask_timeout_secs: number; mode: string };
  sensor?: { roots: number[]; watched_dirs: string[]; poll_ms: number; blind_spots: string[] } | null;
}

/** Tauri tashqarisida (oddiy brauzer) — buyruqlar ishlamaydi, UI xato holatini ko'rsatadi. */
export async function call<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return invoke<T>(cmd, args);
}

/** Davriy so'rov: `ms` da bir marta, komponent yashirin bo'lsa ham. `refresh()` — darhol. */
export function usePoll<T>(fn: () => Promise<T>, ms: number): { data: T | null; error: string | null; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const tick = useCallback(() => {
    fnRef
      .current()
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);
  useEffect(() => {
    tick();
    const id = window.setInterval(tick, ms);
    return () => window.clearInterval(id);
  }, [tick, ms]);
  return { data, error, refresh: tick };
}

export function time(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString("uz-UZ", { hour12: false });
}

export function dateTime(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : `${d.toLocaleDateString("uz-UZ")} ${d.toLocaleTimeString("uz-UZ", { hour12: false })}`;
}

export const EVENT_LABEL: Record<string, string> = {
  "session.start": "sessiya boshlandi",
  "session.end": "sessiya tugadi",
  prompt: "prompt",
  "tool.pre": "tool so'rovi",
  "tool.post": "tool natijasi",
  "decision.human": "inson qarori",
  "os.observed": "OS kuzatuvi",
};

export const FACT_LABEL: Record<string, string> = {
  network_egress: "tarmoqqa chiqish",
  reads_secret_file: "maxfiy fayl",
  sends_tainted_secret: "o'qilgan sir yuborilmoqda",
  contains_secret_pattern: "token shakli",
  session_secret_read: "sessiya sir ko'rgan",
  pipes_to_shell: "skript → shell",
  destructive: "o'chirish",
  destructive_outside_workspace: "papkadan tashqarida o'chirish",
  force_push: "force push",
  writes_outside_workspace: "papkadan tashqariga yozish",
  system_change: "tizim o'zgarishi",
};
