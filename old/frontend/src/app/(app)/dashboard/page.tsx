"use client";

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "@/lib/api-client";

interface UsagePoint {
  date: string;
  tokens: number;
  requests: number;
}

interface Health {
  score: number;
  profile_completeness: number;
  engagement: number;
  recommendations: string[];
}

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsagePoint[]>([]);
  const [topics, setTopics] = useState<{ module: string; count: number }[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api<{ series: UsagePoint[] }>("/dashboard/usage?days=30"),
      api<{ by_module: { module: string; count: number }[] }>("/dashboard/topics?days=30"),
      api<Health>("/dashboard/business-health"),
    ])
      .then(([u, t, h]) => {
        setUsage(u.series);
        setTopics(t.by_module);
        setHealth(h);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      {error && <p className="text-destructive">{error}</p>}

      <div className="grid gap-6 md:grid-cols-3">
        <section className="rounded-2xl border p-4">
          <h2 className="mb-1 text-sm text-muted-foreground">Biznes salomatligi</h2>
          <p className="text-4xl font-bold">{health?.score ?? "—"}<span className="text-lg">/100</span></p>
          <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
            {health?.recommendations.map((r) => <li key={r}>• {r}</li>)}
          </ul>
        </section>

        <section className="rounded-2xl border p-4 md:col-span-2">
          <h2 className="mb-3 text-sm text-muted-foreground">AI foydalanish (30 kun)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={usage}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="requests" stroke="hsl(221 83% 53%)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="rounded-2xl border p-4">
        <h2 className="mb-3 text-sm text-muted-foreground">Modullar bo'yicha savollar</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={topics}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="module" fontSize={11} />
            <YAxis fontSize={11} />
            <Tooltip />
            <Bar dataKey="count" fill="hsl(221 83% 53%)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>
    </main>
  );
}
