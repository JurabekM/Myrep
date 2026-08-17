"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Upload, FileText, RefreshCw } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth";
import { Markdown } from "@/components/shared/Markdown";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface Doc {
  id: string;
  filename: string;
  status: "processing" | "ready" | "failed";
  size: number;
  created_at: string;
}

const ANALYSIS_TASKS = [
  { value: "summarize", label: "Xulosa" },
  { value: "explain", label: "Tushuntirish" },
  { value: "risks", label: "Risklar" },
  { value: "suggestions", label: "Takliflar" },
  { value: "translate", label: "Tarjima" },
  { value: "extract", label: "Ma'lumot ajratish" },
  { value: "classify", label: "Turini aniqlash" },
];

const STATUS_LABEL: Record<Doc["status"], string> = {
  processing: "Qayta ishlanmoqda…",
  ready: "Tayyor",
  failed: "Xatolik",
};

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<Doc | null>(null);
  const [task, setTask] = useState("summarize");
  const [targetLang, setTargetLang] = useState("uz");
  const [result, setResult] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setDocs(await api<Doc[]>("/documents"));
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll while any document is still processing.
  useEffect(() => {
    if (!docs.some((d) => d.status === "processing")) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [docs, load]);

  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const token = useAuthStore.getState().accessToken;
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.message ?? "Yuklash amalga oshmadi");
        return;
      }
      await load();
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const analyze = async () => {
    if (!selected) return;
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const data = await api<{ result: string }>("/documents/analyze", {
        method: "POST",
        body: JSON.stringify({
          document_id: selected.id,
          task,
          target_lang: targetLang,
        }),
      });
      setResult(data.result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Hujjat Tahlili</h1>
          <p className="text-sm text-muted-foreground">
            PDF, Word, Excel, PowerPoint, rasm (OCR) — 25 MB gacha
          </p>
        </div>
        <button
          onClick={load}
          className="rounded-lg border p-2 text-muted-foreground hover:bg-muted"
          aria-label="Yangilash"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <label className="flex cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-8 text-sm text-muted-foreground hover:bg-muted/50">
        {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
        {uploading ? "Yuklanmoqda…" : "Fayl tanlang yoki shu yerga tashlang"}
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.xlsx,.pptx,.txt,.csv,.png,.jpg,.jpeg"
          onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])}
        />
      </label>

      {error && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border">
          <h2 className="border-b p-4 text-sm font-semibold">Hujjatlarim</h2>
          <ul className="max-h-96 divide-y overflow-y-auto">
            {docs.length === 0 && (
              <li className="p-4 text-sm text-muted-foreground">Hali hujjat yuklanmagan</li>
            )}
            {docs.map((doc) => (
              <li key={doc.id}>
                <button
                  onClick={() => {
                    setSelected(doc);
                    setResult(null);
                  }}
                  className={`flex w-full items-center gap-3 p-3 text-left text-sm hover:bg-muted ${
                    selected?.id === doc.id ? "bg-muted" : ""
                  }`}
                >
                  <FileText size={16} className="shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate">{doc.filename}</span>
                  <span className="text-xs text-muted-foreground">{formatSize(doc.size)}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      doc.status === "ready"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                        : doc.status === "failed"
                          ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                          : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                    }`}
                  >
                    {STATUS_LABEL[doc.status]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border p-4">
          <h2 className="mb-3 text-sm font-semibold">Tahlil</h2>
          {!selected ? (
            <p className="text-sm text-muted-foreground">Chapdan hujjat tanlang</p>
          ) : (
            <div className="space-y-3">
              <p className="truncate text-sm font-medium">{selected.filename}</p>
              <div className="flex flex-wrap gap-2">
                <select
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  className="rounded-lg border bg-background px-3 py-2 text-sm"
                >
                  {ANALYSIS_TASKS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                {task === "translate" && (
                  <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="rounded-lg border bg-background px-3 py-2 text-sm"
                  >
                    <option value="uz">O'zbekcha</option>
                    <option value="ru">Ruscha</option>
                    <option value="en">Inglizcha</option>
                  </select>
                )}
                <button
                  onClick={analyze}
                  disabled={analyzing || selected.status !== "ready"}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
                >
                  {analyzing && <Loader2 size={14} className="animate-spin" />}
                  Tahlil qilish
                </button>
              </div>
              {selected.status === "processing" && (
                <p className="text-xs text-muted-foreground">
                  Hujjat hali qayta ishlanmoqda — bir necha soniyadan so'ng tayyor bo'ladi.
                </p>
              )}
              {result && (
                <div className="max-h-[28rem] overflow-y-auto rounded-xl border p-4">
                  <Markdown>{result}</Markdown>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
