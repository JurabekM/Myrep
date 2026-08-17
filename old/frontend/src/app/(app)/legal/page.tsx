"use client";

import { useState } from "react";
import { Loader2, ExternalLink, ShieldCheck, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api-client";
import { Markdown } from "@/components/shared/Markdown";

interface Source {
  title: string;
  url?: string | null;
  article?: string | null;
  snippet?: string | null;
}

interface AskResponse {
  answer: string;
  sources: Source[];
  safety: { confidence: number; category: string };
  disclaimer: string;
}

type Tab = "ask" | "contract";

export default function LegalPage() {
  const [tab, setTab] = useState<Tab>("ask");
  const [question, setQuestion] = useState("");
  const [contract, setContract] = useState("");
  const [focus, setFocus] = useState("");
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [contractResult, setContractResult] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAskResult(null);
    try {
      const data = await api<AskResponse>("/legal/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
      });
      setAskResult(data);
      setDisclaimer(data.disclaimer);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const analyzeContract = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setContractResult(null);
    try {
      const data = await api<{ analysis: string; disclaimer: string }>(
        "/legal/analyze-contract",
        {
          method: "POST",
          body: JSON.stringify({ contract_text: contract, focus: focus || undefined }),
        },
      );
      setContractResult(data.analysis);
      setDisclaimer(data.disclaimer);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Huquqiy Yordamchi</h1>
        <p className="text-sm text-muted-foreground">
          O'zbekiston qonunchiligi bo'yicha ma'lumot — lex.uz manbalariga tayangan holda
        </p>
      </div>

      <div className="flex gap-2 border-b">
        {(
          [
            ["ask", "Savol berish"],
            ["contract", "Shartnoma tahlili"],
          ] as [Tab, string][]
        ).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`border-b-2 px-4 py-2 text-sm ${
              tab === value
                ? "border-primary font-medium text-foreground"
                : "border-transparent text-muted-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "ask" ? (
        <form onSubmit={ask} className="space-y-3">
          <textarea
            required
            minLength={5}
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Masalan: MChJ ta'sischisi o'z ulushini qanday sotishi mumkin?"
            className="w-full rounded-xl border bg-background px-4 py-3"
          />
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            So'rash
          </button>
        </form>
      ) : (
        <form onSubmit={analyzeContract} className="space-y-3">
          <textarea
            required
            minLength={100}
            rows={10}
            value={contract}
            onChange={(e) => setContract(e.target.value)}
            placeholder="Shartnoma matnini shu yerga joylashtiring (kamida 100 belgi)…"
            className="w-full rounded-xl border bg-background px-4 py-3 font-mono text-xs"
          />
          <input
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            placeholder="Alohida e'tibor (ixtiyoriy): masalan, jarima bandlari"
            className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Tahlil qilish
          </button>
        </form>
      )}

      {error && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

      {tab === "ask" && askResult && (
        <section className="space-y-4">
          <div className="rounded-2xl border p-5">
            <div className="mb-2">
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                  askResult.safety.confidence >= 0.6
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                    : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                }`}
              >
                {askResult.safety.confidence >= 0.6 ? (
                  <ShieldCheck size={12} />
                ) : (
                  <AlertTriangle size={12} />
                )}
                Ishonch: {Math.round(askResult.safety.confidence * 100)}%
              </span>
            </div>
            <Markdown>{askResult.answer}</Markdown>
          </div>

          {askResult.sources.length > 0 && (
            <div className="rounded-2xl border p-5">
              <h2 className="mb-3 text-sm font-semibold">Manbalar</h2>
              <ol className="space-y-2 text-sm">
                {askResult.sources.map((s, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-muted-foreground">[{i + 1}]</span>
                    <div>
                      <p className="font-medium">
                        {s.title}
                        {s.article ? `, ${s.article}` : ""}
                      </p>
                      {s.url && (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          lex.uz da ochish <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      )}

      {tab === "contract" && contractResult && (
        <section className="rounded-2xl border p-5">
          <Markdown>{contractResult}</Markdown>
        </section>
      )}

      {disclaimer && (
        <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
          {disclaimer}
        </p>
      )}
    </div>
  );
}
