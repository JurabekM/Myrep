"use client";

import { useState } from "react";
import { Loader2, Copy, Check } from "lucide-react";
import { api } from "@/lib/api-client";
import { Markdown } from "@/components/shared/Markdown";

const TASKS = [
  { value: "content_plan", label: "Kontent-plan (30 kun)" },
  { value: "ad_copy", label: "Reklama matnlari" },
  { value: "smm_strategy", label: "SMM strategiya" },
  { value: "target_audience", label: "Target auditoriya tahlili" },
  { value: "seo_audit_plan", label: "SEO reja" },
  { value: "landing_page", label: "Landing page matni" },
  { value: "email_campaign", label: "Email ketma-ketligi" },
  { value: "funnel", label: "Marketing funnel" },
  { value: "ab_test_plan", label: "A/B test rejasi" },
];

const CHANNELS = [
  { value: "instagram", label: "Instagram" },
  { value: "telegram", label: "Telegram" },
  { value: "facebook", label: "Facebook" },
  { value: "google_ads", label: "Google Ads" },
  { value: "email", label: "Email" },
  { value: "website", label: "Veb-sayt" },
];

export default function MarketingPage() {
  const [task, setTask] = useState("content_plan");
  const [description, setDescription] = useState("");
  const [channels, setChannels] = useState<string[]>(["telegram", "instagram"]);
  const [budget, setBudget] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const toggleChannel = (value: string) =>
    setChannels((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value],
    );

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api<{ content: string }>("/marketing/generate", {
        method: "POST",
        body: JSON.stringify({
          task,
          business_description: description,
          channels,
          budget_uzs: budget ? Number(budget) : undefined,
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
        <h1 className="text-2xl font-semibold">Marketing AI</h1>
        <p className="text-sm text-muted-foreground">
          O'zbekiston auditoriyasiga moslashgan marketing materiallari
        </p>
      </div>

      <form onSubmit={generate} className="space-y-4 rounded-2xl border p-5">
        <label className="block text-sm">
          Vazifa
          <select
            value={task}
            onChange={(e) => setTask(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          >
            {TASKS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          Biznes tavsifi
          <textarea
            required
            minLength={10}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Mahsulot/xizmat, auditoriya, hozirgi holat..."
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          />
        </label>

        <fieldset className="text-sm">
          <legend className="mb-2">Kanallar</legend>
          <div className="flex flex-wrap gap-2">
            {CHANNELS.map((c) => (
              <button
                key={c.value}
                type="button"
                onClick={() => toggleChannel(c.value)}
                className={`rounded-full border px-3 py-1 text-sm ${
                  channels.includes(c.value)
                    ? "border-primary bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="block text-sm sm:w-64">
          Oylik byudjet, so'm <span className="text-muted-foreground">(ixtiyoriy)</span>
          <input
            type="number"
            min={0}
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="5000000"
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
        >
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? "Yaratilmoqda…" : "Yaratish"}
        </button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </form>

      {result && (
        <section className="rounded-2xl border p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">{TASKS.find((t) => t.value === task)?.label}</h2>
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
