"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useTheme } from "next-themes";
import {
  MessageSquare, Briefcase, Scale, Calculator, Megaphone, FileText,
  Wallet, LayoutDashboard, UserCircle, Shield, LogOut, Moon, Sun, Menu, X,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuthStore, type User } from "@/stores/auth";

const NAV = [
  { href: "/chat", label: "AI Chat", icon: MessageSquare },
  { href: "/consultant", label: "Konsultant", icon: Briefcase },
  { href: "/legal", label: "Huquq", icon: Scale },
  { href: "/tax", label: "Soliq", icon: Calculator },
  { href: "/marketing", label: "Marketing", icon: Megaphone },
  { href: "/documents", label: "Hujjatlar", icon: FileText },
  { href: "/finance", label: "Moliya", icon: Wallet },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/profile", label: "Profil", icon: UserCircle },
];

/**
 * Authenticated shell: restores the session via the BFF refresh cookie on
 * first mount, then renders sidebar navigation. Unauthenticated users are
 * redirected to /login.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { accessToken, user, setAccessToken, setUser, logout } = useAuthStore();
  const [status, setStatus] = useState<"checking" | "ready">(
    accessToken ? "ready" : "checking",
  );
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (accessToken) return;
    void (async () => {
      const res = await fetch("/api/auth/refresh", { method: "POST" });
      if (!res.ok) {
        router.replace("/login");
        return;
      }
      const data = (await res.json()) as { access_token: string };
      setAccessToken(data.access_token);
      setStatus("ready");
    })();
  }, [accessToken, router, setAccessToken]);

  useEffect(() => {
    if (status !== "ready" || user) return;
    api<User>("/auth/me").then(setUser).catch(() => undefined);
  }, [status, user, setUser]);

  if (status === "checking") {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Yuklanmoqda…
      </div>
    );
  }

  const isAdmin = user?.role === "admin" || user?.role === "moderator";

  const nav = (
    <nav className="flex flex-col gap-1 p-3">
      {NAV.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          onClick={() => setMenuOpen(false)}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
            pathname.startsWith(href)
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Icon size={16} /> {label}
        </Link>
      ))}
      {isAdmin && (
        <Link
          href="/admin"
          onClick={() => setMenuOpen(false)}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
            pathname.startsWith("/admin")
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Shield size={16} /> Admin
        </Link>
      )}
    </nav>
  );

  return (
    <div className="flex h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r md:flex">
        <div className="border-b p-4">
          <p className="font-semibold">AI Business Advisor</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <div className="flex-1 overflow-y-auto">{nav}</div>
        <div className="flex items-center justify-between border-t p-3">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
            aria-label="Mavzuni almashtirish"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-2 rounded-lg p-2 text-sm text-muted-foreground hover:bg-muted"
          >
            <LogOut size={16} /> Chiqish
          </button>
        </div>
      </aside>

      {/* Mobile header + drawer */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-4 py-2 md:hidden">
          <p className="font-semibold">AI Advisor</p>
          <button onClick={() => setMenuOpen(!menuOpen)} aria-label="Menyu">
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </header>
        {menuOpen && <div className="border-b bg-background md:hidden">{nav}</div>}
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
