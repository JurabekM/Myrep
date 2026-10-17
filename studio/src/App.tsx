import { useEffect, useState } from "react";
import { Activity, FileCode2, FileOutput, Hand, History, Settings, ShieldCheck, type LucideIcon } from "lucide-react";
import mark from "../src-tauri/icons/128x128.png";
import { call, usePoll, type Status } from "./api";
import { ApprovalsScreen } from "./screens/ApprovalsScreen";
import { IntegrityScreen } from "./screens/IntegrityScreen";
import { LiveScreen } from "./screens/LiveScreen";
import { PlaceholderScreen } from "./screens/PlaceholderScreen";
import { PoliciesScreen } from "./screens/PoliciesScreen";
import { SessionsScreen } from "./screens/SessionsScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { WindowControls } from "./WindowControls";

type ScreenId = "live" | "approvals" | "sessions" | "integrity" | "policies" | "reports" | "settings";

interface ScreenDef {
  id: ScreenId;
  title: string;
  icon: LucideIcon;
}

const SCREENS: ScreenDef[] = [
  { id: "live", title: "Jonli", icon: Activity },
  { id: "approvals", title: "Tasdiqlash", icon: Hand },
  { id: "sessions", title: "Sessiyalar", icon: History },
  { id: "integrity", title: "Yaxlitlik", icon: ShieldCheck },
  { id: "policies", title: "Siyosatlar", icon: FileCode2 },
  { id: "reports", title: "Hisobotlar", icon: FileOutput },
];

const SETTINGS: ScreenDef = { id: "settings", title: "Sozlamalar", icon: Settings };

interface AppInfo {
  version: string;
  format_version: string;
}

export function App() {
  const [active, setActive] = useState<ScreenId>("live");
  const [info, setInfo] = useState<AppInfo | null>(null);
  const { data: status, refresh: refreshStatus } = usePoll(
    () => call<Status>("status").catch((e: unknown) => ({ ok: false, error: String(e) }) as Status),
    2000,
  );

  useEffect(() => {
    call<AppInfo>("app_info")
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  const current = [...SCREENS, SETTINGS].find((s) => s.id === active) ?? SCREENS[0]!;
  const online = status?.ok === true;
  const pending = status?.pending ?? 0;

  const navButton = (s: ScreenDef) => {
    const Icon = s.icon;
    return (
      <button key={s.id} className="nav-item" aria-current={s.id === active ? "page" : undefined} onClick={() => setActive(s.id)}>
        <Icon size={17} strokeWidth={1.75} />
        {s.title}
        {s.id === "approvals" && pending > 0 && <span className="pill ask count">{pending}</span>}
      </button>
    );
  };

  const screen = (() => {
    switch (active) {
      case "live":
        return <LiveScreen />;
      case "approvals":
        return <ApprovalsScreen onRouteChange={refreshStatus} />;
      case "sessions":
        return <SessionsScreen />;
      case "integrity":
        return <IntegrityScreen />;
      case "policies":
        return <PoliciesScreen />;
      case "settings":
        return <SettingsScreen status={status} />;
      case "reports":
        return (
          <PlaceholderScreen
            title="Hisobotlar"
            icon={FileOutput}
            phase="F6"
            summary="Auditor uchun dalil to'plami: yozuvlar, imzolangan checkpoint'lar va mustaqil verifikator yo'riqnomasi."
          />
        );
    }
  })();

  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Asosiy navigatsiya">
        <div className="brand" data-tauri-drag-region>
          <img src={mark} alt="" />
          TAMGA
        </div>
        {SCREENS.map(navButton)}
        <div className="nav-section">Holat</div>
        <div className="nav-item static">
          <span className={`dot ${online ? "on" : ""}`} />
          {online ? `${status?.records ?? 0} yozuv` : "daemon ulanmagan"}
        </div>
        {online && (status?.tainted_sessions ?? 0) > 0 && (
          <div className="nav-item static" title="Bu sessiyalar maxfiy ma'lumotni o'qigan">
            <span className="dot warn" />
            {status?.tainted_sessions} sessiya sir ko'rgan
          </div>
        )}
        <div className="sidebar-foot">
          {navButton(SETTINGS)}
          <div className="mono" style={{ color: "var(--text-faint)", padding: "8px 12px 0" }}>
            v{info?.version ?? "—"} · TR {info?.format_version ?? "0.1"}
          </div>
        </div>
      </nav>

      <main className="main">
        <header className="titlebar" data-tauri-drag-region>
          <h1 data-tauri-drag-region>{current.title}</h1>
          <div className="status" data-tauri-drag-region title={online ? (status?.home ?? "") : (status?.error ?? "")}>
            <span className={`dot ${online ? "on" : ""}`} />
            {online ? `tamgad · ${status?.mode} · ${status?.config?.ask_route === "studio" ? "ask → Studio" : "ask → agent"}` : "tamgad ulanmagan"}
          </div>
          <WindowControls />
        </header>
        <div className="content">{screen}</div>
      </main>
    </div>
  );
}
