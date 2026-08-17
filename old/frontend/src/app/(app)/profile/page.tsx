"use client";

import { useEffect, useState } from "react";
import { Loader2, Check, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuthStore, type User } from "@/stores/auth";

const BUSINESS_TYPES = [
  { value: "ytt", label: "YTT (yakka tartibdagi tadbirkor)" },
  { value: "mchj", label: "MChJ" },
  { value: "microfirm", label: "Mikrofirma" },
  { value: "freelancer", label: "Frilanser" },
  { value: "startup", label: "Startap" },
  { value: "other", label: "Boshqa" },
];

interface ProfileForm {
  industry: string;
  business_type: string;
  experience_years: string;
  goals: string;
  location: string;
  employees: string;
  annual_revenue_uzs: string;
}

export default function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const [form, setForm] = useState<ProfileForm>({
    industry: "", business_type: "", experience_years: "", goals: "",
    location: "", employees: "", annual_revenue_uzs: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 2FA
  const [twoFa, setTwoFa] = useState<{ secret: string; provisioning_uri: string } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [twoFaDone, setTwoFaDone] = useState(false);

  useEffect(() => {
    api<User & { profile: Record<string, unknown> }>("/auth/me").then((me) => {
      setUser(me);
      const p = me.profile as Record<string, unknown>;
      setForm({
        industry: (p.industry as string) ?? "",
        business_type: (p.business_type as string) ?? "",
        experience_years: p.experience_years != null ? String(p.experience_years) : "",
        goals: Array.isArray(p.goals) ? (p.goals as string[]).join(", ") : "",
        location: (p.location as string) ?? "",
        employees: p.employees != null ? String(p.employees) : "",
        annual_revenue_uzs: p.annual_revenue_uzs != null ? String(p.annual_revenue_uzs) : "",
      });
    }).catch((e) => setError((e as Error).message));
  }, [setUser]);

  const set = (key: keyof ProfileForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api<User>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          profile: {
            industry: form.industry || null,
            business_type: form.business_type || null,
            experience_years: form.experience_years ? Number(form.experience_years) : null,
            goals: form.goals ? form.goals.split(",").map((g) => g.trim()).filter(Boolean) : [],
            location: form.location || null,
            employees: form.employees ? Number(form.employees) : null,
            annual_revenue_uzs: form.annual_revenue_uzs ? Number(form.annual_revenue_uzs) : null,
          },
        }),
      });
      setUser(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const setup2fa = async () => {
    setError(null);
    try {
      setTwoFa(await api<{ secret: string; provisioning_uri: string }>("/auth/2fa/setup", { method: "POST" }));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const confirm2fa = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api("/auth/2fa/confirm", {
        method: "POST",
        body: JSON.stringify({ totp_code: totpCode }),
      });
      setTwoFaDone(true);
      setTwoFa(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const input = "mt-1 w-full rounded-lg border bg-background px-3 py-2";

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Profil</h1>
        <p className="text-sm text-muted-foreground">
          Biznes profilingiz to'liq bo'lsa, AI maslahatlar sizga moslashadi
        </p>
      </div>

      {error && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

      <form onSubmit={save} className="space-y-4 rounded-2xl border p-5">
        <h2 className="font-semibold">Biznes profili</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            Soha
            <input value={form.industry} onChange={set("industry")} className={input}
              placeholder="Masalan: oziq-ovqat yetkazib berish" />
          </label>
          <label className="text-sm">
            Biznes turi
            <select value={form.business_type} onChange={set("business_type")} className={input}>
              <option value="">Tanlang…</option>
              {BUSINESS_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Tajriba (yil)
            <input type="number" min={0} max={80} value={form.experience_years}
              onChange={set("experience_years")} className={input} />
          </label>
          <label className="text-sm">
            Hudud
            <input value={form.location} onChange={set("location")} className={input}
              placeholder="Toshkent" />
          </label>
          <label className="text-sm">
            Xodimlar soni
            <input type="number" min={0} value={form.employees}
              onChange={set("employees")} className={input} />
          </label>
          <label className="text-sm">
            Yillik aylanma (so'm)
            <input type="number" min={0} value={form.annual_revenue_uzs}
              onChange={set("annual_revenue_uzs")} className={input} />
          </label>
        </div>
        <label className="block text-sm">
          Maqsadlar <span className="text-muted-foreground">(vergul bilan)</span>
          <input value={form.goals} onChange={set("goals")} className={input}
            placeholder="eksportga chiqish, filial ochish, investor topish" />
        </label>
        <button type="submit" disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50">
          {saving ? <Loader2 size={16} className="animate-spin" /> : saved ? <Check size={16} /> : null}
          {saved ? "Saqlandi" : "Saqlash"}
        </button>
      </form>

      <section className="space-y-3 rounded-2xl border p-5">
        <h2 className="flex items-center gap-2 font-semibold">
          <ShieldCheck size={18} /> Ikki bosqichli himoya (2FA)
        </h2>
        {user?.two_fa_enabled || twoFaDone ? (
          <p className="text-sm text-emerald-600">2FA yoqilgan ✓</p>
        ) : twoFa ? (
          <form onSubmit={confirm2fa} className="space-y-3 text-sm">
            <p>
              Authenticator ilovangizga (Google Authenticator, Authy) quyidagi kalitni kiriting:
            </p>
            <code className="block rounded-lg bg-muted p-3 font-mono text-xs break-all">
              {twoFa.secret}
            </code>
            <label className="block">
              Ilovadagi 6 raqamli kod
              <input inputMode="numeric" pattern="\d{6}" maxLength={6} required
                value={totpCode} onChange={(e) => setTotpCode(e.target.value)}
                className="mt-1 w-40 rounded-lg border bg-background px-3 py-2" />
            </label>
            <button type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-primary-foreground">
              Tasdiqlash
            </button>
          </form>
        ) : (
          <button onClick={setup2fa}
            className="rounded-lg border px-4 py-2 text-sm hover:bg-muted">
            2FA ni yoqish
          </button>
        )}
      </section>
    </div>
  );
}
