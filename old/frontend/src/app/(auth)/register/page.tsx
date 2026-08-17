"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: form.full_name,
          email: form.email,
          password: form.password,
          phone: form.phone || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.message ?? "Ro'yxatdan o'tish amalga oshmadi");
        return;
      }
      router.push("/login?registered=1");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-2xl border p-6">
        <h1 className="text-xl font-semibold">Ro'yxatdan o'tish</h1>
        <p className="text-sm text-muted-foreground">
          AI biznes-maslahatchingizni bepul sinab ko'ring
        </p>

        <label className="block text-sm">
          To'liq ism
          <input
            required
            minLength={2}
            value={form.full_name}
            onChange={set("full_name")}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="name"
          />
        </label>
        <label className="block text-sm">
          Email
          <input
            type="email"
            required
            value={form.email}
            onChange={set("email")}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="email"
          />
        </label>
        <label className="block text-sm">
          Telefon <span className="text-muted-foreground">(ixtiyoriy, +998…)</span>
          <input
            type="tel"
            pattern="\+998\d{9}"
            value={form.phone}
            onChange={set("phone")}
            placeholder="+998901234567"
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="tel"
          />
        </label>
        <label className="block text-sm">
          Parol <span className="text-muted-foreground">(kamida 8 belgi, harf + raqam)</span>
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={set("password")}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="new-password"
          />
        </label>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary py-2 text-primary-foreground disabled:opacity-50"
        >
          {loading ? "Yaratilmoqda…" : "Hisob yaratish"}
        </button>
        <p className="text-center text-sm text-muted-foreground">
          Hisobingiz bormi?{" "}
          <a href="/login" className="text-primary underline">Kirish</a>
        </p>
      </form>
    </main>
  );
}
