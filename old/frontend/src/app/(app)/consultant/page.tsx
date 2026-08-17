"use client";

import { useState } from "react";
import { Loader2, Copy, Check } from "lucide-react";
import { api } from "@/lib/api-client";
import { Markdown } from "@/components/shared/Markdown";

const FRAMEWORKS: { value: string; label: string; group: string }[] = [
  { value: "business_plan", label: "Biznes-reja", group: "Strategiya" },
  { value: "swot", label: "SWOT tahlil", group: "Strategiya" },
  { value: "pestel", label: "PESTEL tahlil", group: "Strategiya" },
  { value: "bmc", label: "Business Model Canvas", group: "Strategiya" },
  { value: "lean_canvas", label: "Lean Canvas", group: "Strategiya" },
  { value: "roadmap", label: "Roadmap (12 oy)", group: "Strategiya" },
  { value: "marketing_plan", label: "Marketing reja", group: "Marketing va savdo" },
  { value: "go_to_market", label: "Go-to-Market", group: "Marketing va savdo" },
  { value: "sales_strategy", label: "Savdo strategiyasi", group: "Marketing va savdo" },
  { value: "pricing", label: "Narxlash", group: "Marketing va savdo" },
  { value: "competitor_analysis", label: "Raqobatchilar tahlili", group: "Marketing va savdo" },
  { value: "financial_forecast", label: "Moliyaviy prognoz", group: "Moliya va nazorat" },
  { value: "risk_analysis", label: "Risklar tahlili", group: "Moliya va nazorat" },
  { value: "kpi", label: "KPI tizimi", group: "Moliya va nazorat" },
  { value: "okr", label: "OKR", group: "Moliya va nazorat" },
  { value: "investment_pitch", label: "Investor pitch", group: "Investitsiya va hujjatlar" },
  { value: "investor_deck", label: "Investor deck", group: "Investitsiya va hujjatlar" },
  { value: "grant_application", label: "Grant arizasi", group: "Investitsiya va hujjatlar" },
  { value: "tender_document", label: "Tender taklifi", group: "Investitsiya va hujjatlar" },
];

const GROUPS = [...new Set(FRAMEWORKS.map((f) => f.group))];

export default function ConsultantPage() {
  const [framework, setFramework] = useState("swot");
  const [description, setDescription] = useState("");
  const [extra, setExtra] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api<{ content: string }>("/consultant/generate", {
        method: "POST",
        body: JSON.stringify({
          framework,
          business_description: description,
          extra_context: extra || undefined,
        }),
      });
      setResult(data.content);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Biznes Konsultant</h1>
        <p className="text-sm text-muted-foreground">
          Professional biznes hujjatlari va tahlillarni bir necha daqiqada yarating
        </p>
      </div>

      <form onSubmit={generate} className="space-y-4 rounded-2xl border p-5">
        <label className="block text-sm">
          Framework
          <select
            value={framework}
            onChange={(e) => setFramework(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          >
            {GROUPS.map((group) => (
              <optgroup key={group} label={group}>
                {FRAMEWORKS.filter((f) => f.group === group).map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          Biznes tavsifi <span className="text-muted-foreground">(kamida 20 belgi)</span>
          <textarea
            required
            minLength={20}
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Masalan: Toshkentda milliy taomlar yetkazib berish xizmati. Auditoriya — ofis xodimlari. Hozircha 2 oshpaz, kunlik ~40 buyurtma..."
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          />
        </label>

        <label className="block text-sm">
          Qo'shimcha kontekst <span className="text-muted-foreground">(ixtiyoriy)</span>
          <textarea
            rows={2}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="Byudjet, muddat, maxsus talablar..."
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
        >
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? "Yaratilmoqda… (~30-60 soniya)" : "Yaratish"}
        </button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </form>

      {result && (
        <section className="rounded-2xl border p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">
              {FRAMEWORKS.find((f) => f.value === framework)?.label}
            </h2>
            <button
              onClick={copy}
              className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Nusxalandi" : "Nusxalash"}
            </button>
          </div>
          <Markdown>{result}</Markdown>
        </section>
      )}
    </div>
  );
}
