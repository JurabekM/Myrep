"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth";

type Tab = "analytics" | "users" | "prompts" | "flags" | "kb" | "moderation";

const TABS: { value: Tab; label: string }[] = [
  { value: "analytics", label: "Statistika" },
  { value: "users", label: "Foydalanuvchilar" },
  { value: "prompts", label: "Promptlar" },
  { value: "flags", label: "Feature flags" },
  { value: "kb", label: "Bilimlar bazasi" },
  { value: "moderation", label: "Moderatsiya" },
];

const fmt = (n: number) => new Intl.NumberFormat("uz-UZ").format(n);

export default function AdminPage() {
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<Tab>("analytics");

  if (user && user.role !== "admin" && user.role !== "moderator") {
    return <p className="p-6 text-muted-foreground">Bu sahifa uchun ruxsat yo'q.</p>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Admin Panel</h1>
      <div className="flex flex-wrap gap-2 border-b">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`border-b-2 px-4 py-2 text-sm ${
              tab === t.value
                ? "border-primary font-medium"
                : "border-transparent text-muted-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "analytics" && <AnalyticsTab />}
      {tab === "users" && <UsersTab />}
      {tab === "prompts" && <PromptsTab />}
      {tab === "flags" && <FlagsTab />}
      {tab === "kb" && <KBTab />}
      {tab === "moderation" && <ModerationTab />}
    </div>
  );
}

// ---------------------------------------------------------------- analytics

function AnalyticsTab() {
  const [data, setData] = useState<{
    total_users: number;
    new_users_30d: number;
    by_plan: { plan: string; count: number }[];
    ai_usage: { module: string; tokens: number; cost_usd: number }[];
  } | null>(null);

  useEffect(() => {
    api<NonNullable<typeof data>>("/admin/analytics").then(setData).catch(() => undefined);
  }, []);

  if (!data) return <Loading />;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Jami foydalanuvchi" value={fmt(data.total_users)} />
        <Stat label="Yangi (30 kun)" value={fmt(data.new_users_30d)} />
        {data.by_plan.map((p) => (
          <Stat key={p.plan} label={`Tarif: ${p.plan}`} value={fmt(p.count)} />
        ))}
      </div>
      <div className="rounded-2xl border">
        <h2 className="border-b p-4 text-sm font-semibold">AI xarajatlari (modul bo'yicha)</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="p-3">Modul</th>
              <th className="p-3 text-right">Tokenlar</th>
              <th className="p-3 text-right">Xarajat (USD)</th>
            </tr>
          </thead>
          <tbody>
            {data.ai_usage.map((row) => (
              <tr key={row.module} className="border-t">
                <td className="p-3">{row.module}</td>
                <td className="p-3 text-right">{fmt(row.tokens)}</td>
                <td className="p-3 text-right">${row.cost_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------- users

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  plan: string;
  is_active: boolean;
}

function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);

  const load = useCallback(() => {
    api<{ total: number; items: AdminUser[] }>("/admin/users?limit=100")
      .then((d) => {
        setUsers(d.items);
        setTotal(d.total);
      })
      .catch(() => undefined);
  }, []);

  useEffect(load, [load]);

  const patch = async (id: string, fields: Partial<AdminUser>) => {
    await api(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(fields) });
    load();
  };

  return (
    <div className="rounded-2xl border">
      <h2 className="border-b p-4 text-sm font-semibold">Jami: {fmt(total)}</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="p-3">Email</th>
              <th className="p-3">Ism</th>
              <th className="p-3">Rol</th>
              <th className="p-3">Tarif</th>
              <th className="p-3">Holat</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="p-3">{u.email}</td>
                <td className="p-3">{u.full_name}</td>
                <td className="p-3">
                  <select
                    value={u.role}
                    onChange={(e) => void patch(u.id, { role: e.target.value })}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {["user", "moderator", "admin"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </td>
                <td className="p-3">
                  <select
                    value={u.plan}
                    onChange={(e) => void patch(u.id, { plan: e.target.value })}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {["free", "pro", "business", "enterprise"].map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </td>
                <td className="p-3">
                  <button
                    onClick={() => void patch(u.id, { is_active: !u.is_active })}
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      u.is_active
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                        : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                    }`}
                  >
                    {u.is_active ? "Faol" : "Bloklangan"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ prompts

interface Prompt {
  key: string;
  version: number;
  locale: string;
  active: boolean;
  content: string;
}

function PromptsTab() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [editing, setEditing] = useState<Prompt | null>(null);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<{ items: Prompt[] }>("/admin/prompts")
      .then((d) => setPrompts(d.items.filter((p) => p.active)))
      .catch(() => undefined);
  }, []);

  useEffect(load, [load]);

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      await api("/admin/prompts", {
        method: "POST",
        body: JSON.stringify({ key: editing.key, locale: editing.locale, content }),
      });
      setEditing(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ul className="divide-y rounded-2xl border">
        {prompts.map((p) => (
          <li key={`${p.key}-${p.locale}`}>
            <button
              onClick={() => {
                setEditing(p);
                setContent(p.content);
              }}
              className={`w-full p-3 text-left text-sm hover:bg-muted ${
                editing?.key === p.key ? "bg-muted" : ""
              }`}
            >
              <span className="font-mono">{p.key}</span>
              <span className="ml-2 text-xs text-muted-foreground">
                v{p.version} · {p.locale}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="rounded-2xl border p-4">
        {editing ? (
          <div className="space-y-3">
            <p className="font-mono text-sm">{editing.key}</p>
            <textarea
              rows={14}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full rounded-lg border bg-background p-3 font-mono text-xs"
            />
            <button
              onClick={save}
              disabled={saving}
              className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {saving ? "Saqlanmoqda…" : "Yangi versiya sifatida saqlash"}
            </button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Tahrirlash uchun prompt tanlang</p>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------- flags

interface Flag {
  key: string;
  enabled: boolean;
  rollout_pct: number;
  plans: string[];
}

function FlagsTab() {
  const [flags, setFlags] = useState<Flag[]>([]);

  const load = useCallback(() => {
    api<{ items: Flag[] }>("/admin/feature-flags")
      .then((d) => setFlags(d.items))
      .catch(() => undefined);
  }, []);

  useEffect(load, [load]);

  const toggle = async (flag: Flag) => {
    await api(`/admin/feature-flags/${flag.key}`, {
      method: "PUT",
      body: JSON.stringify({ ...flag, enabled: !flag.enabled }),
    });
    load();
  };

  return (
    <ul className="divide-y rounded-2xl border">
      {flags.map((f) => (
        <li key={f.key} className="flex items-center justify-between p-3 text-sm">
          <div>
            <p className="font-mono">{f.key}</p>
            <p className="text-xs text-muted-foreground">
              rollout {f.rollout_pct}%{f.plans.length ? ` · ${f.plans.join(", ")}` : ""}
            </p>
          </div>
          <button
            onClick={() => void toggle(f)}
            className={`rounded-full px-3 py-1 text-xs ${
              f.enabled
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {f.enabled ? "Yoqilgan" : "O'chirilgan"}
          </button>
        </li>
      ))}
    </ul>
  );
}

// ----------------------------------------------------------------------- kb

interface KBSource {
  id: string;
  type: string;
  title?: string;
  url?: string;
  chunks_count: number;
}

function KBTab() {
  const [sources, setSources] = useState<KBSource[]>([]);
  const [url, setUrl] = useState("");
  const [queued, setQueued] = useState(false);

  const load = useCallback(() => {
    api<{ items: KBSource[] }>("/admin/kb/sources")
      .then((d) => setSources(d.items))
      .catch(() => undefined);
  }, []);

  useEffect(load, [load]);

  const ingest = async (e: React.FormEvent) => {
    e.preventDefault();
    setQueued(false);
    await api("/admin/kb/ingest-lex", { method: "POST", body: JSON.stringify({ url }) });
    setQueued(true);
    setUrl("");
    setTimeout(load, 3000);
  };

  return (
    <div className="space-y-4">
      <form onSubmit={ingest} className="flex gap-2">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://lex.uz/docs/..."
          className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
        />
        <button className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground">
          Indekslash
        </button>
      </form>
      {queued && <p className="text-sm text-emerald-600">Navbatga qo'yildi ✓</p>}
      <ul className="divide-y rounded-2xl border">
        {sources.map((s) => (
          <li key={s.id} className="p-3 text-sm">
            <p className="font-medium">{s.title ?? s.url}</p>
            <p className="text-xs text-muted-foreground">
              {s.type} · {s.chunks_count} chunk
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --------------------------------------------------------------- moderation

interface FlaggedMessage {
  id: string;
  content: string;
  safety?: { confidence: number; category: string } | null;
  feedback?: number | null;
  created_at: string;
}

function ModerationTab() {
  const [items, setItems] = useState<FlaggedMessage[]>([]);

  useEffect(() => {
    api<{ items: FlaggedMessage[] }>("/admin/moderation/flagged")
      .then((d) => setItems(d.items))
      .catch(() => undefined);
  }, []);

  if (items.length === 0)
    return <p className="text-sm text-muted-foreground">Tekshirish uchun xabarlar yo'q 🎉</p>;

  return (
    <ul className="space-y-3">
      {items.map((m) => (
        <li key={m.id} className="rounded-2xl border p-4 text-sm">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            {m.safety && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                Ishonch: {Math.round(m.safety.confidence * 100)}% · {m.safety.category}
              </span>
            )}
            {m.feedback === -1 && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-red-800 dark:bg-red-900/40 dark:text-red-300">
                👎 Salbiy baho
              </span>
            )}
            <span className="text-muted-foreground">
              {new Date(m.created_at).toLocaleString("uz-UZ")}
            </span>
          </div>
          <p className="whitespace-pre-wrap text-muted-foreground">{m.content}</p>
        </li>
      ))}
    </ul>
  );
}

// ------------------------------------------------------------------ helpers

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}

function Loading() {
  return (
    <div className="flex items-center gap-2 p-6 text-muted-foreground">
      <Loader2 size={16} className="animate-spin" /> Yuklanmoqda…
    </div>
  );
}
