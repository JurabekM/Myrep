"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

function getDeviceId(): string {
  const key = "aba_device_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export default function LoginPage() {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          device_id: getDeviceId(),
          totp_code: needTotp ? totp : undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.message?.includes("2FA")) setNeedTotp(true);
        setError(data.message ?? "Kirish amalga oshmadi");
        return;
      }
      setAccessToken(data.access_token);
      router.push("/chat");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-2xl border p-6">
        <h1 className="text-xl font-semibold">AI Business Advisor</h1>
        <p className="text-sm text-muted-foreground">Hisobingizga kiring</p>

        <label className="block text-sm">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="email"
          />
        </label>
        <label className="block text-sm">
          Parol
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
            autoComplete="current-password"
          />
        </label>
        {needTotp && (
          <label className="block text-sm">
            2FA kodi
            <input
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              required
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              className="mt-1 w-full rounded-lg border bg-background px-3 py-2"
              autoComplete="one-time-code"
            />
          </label>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary py-2 text-primary-foreground disabled:opacity-50"
        >
          {loading ? "Kirilmoqda…" : "Kirish"}
        </button>
        <p className="text-center text-sm text-muted-foreground">
          Hisobingiz yo'qmi?{" "}
          <a href="/register" className="text-primary underline">
            Ro'yxatdan o'ting
          </a>
        </p>
      </form>
    </main>
  );
}
