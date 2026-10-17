import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  Activity,
  FileCode2,
  FileOutput,
  Hand,
  History,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import mark from "../src-tauri/icons/128x128.png";
import { LiveScreen } from "./screens/LiveScreen";
import { PlaceholderScreen } from "./screens/PlaceholderScreen";
import { WindowControls } from "./WindowControls";

type ScreenId = "live" | "approvals" | "sessions" | "integrity" | "policies" | "reports" | "settings";

interface ScreenDef {
  id: ScreenId;
  title: string;
  icon: LucideIcon;
  phase: string;
  summary: string;
}

const SCREENS: ScreenDef[] = [
  { id: "live", title: "Jonli", icon: Activity, phase: "F2", summary: "" },
  {
    id: "approvals",
    title: "Tasdiqlash",
    icon: Hand,
    phase: "F3",
    summary: "Siyosat «ask» degan harakatlar shu yerda navbatda turadi: ruxsat, rad yoki doimiy qoida.",
  },
  {
    id: "sessions",
    title: "Sessiyalar",
    icon: History,
    phase: "F4",
    summary: "Har bir agent sessiyasini Claude Code transkriptiga o'xshab qayta o'ynatish.",
  },
  {
    id: "integrity",
    title: "Yaxlitlik",
    icon: ShieldCheck,
    phase: "F1 · F6",
    summary: "Xesh-zanjir, Merkle checkpoint'lar va tashqi guvoh holati. Buzilgan joy aniq seq bilan ko'rsatiladi.",
  },
  {
    id: "policies",
    title: "Siyosatlar",
    icon: FileCode2,
    phase: "F3",
    summary: "Cedar siyosatlari muharriri va «shu harakat bo'lsa nima bo'ladi» sinovi.",
  },
  {
    id: "reports",
    title: "Hisobotlar",
    icon: FileOutput,
    phase: "F6",
    summary: "Auditor uchun dalil to'plami: yozuvlar, imzolangan checkpoint'lar va mustaqil verifikator yo'riqnomasi.",
  },
];

const SETTINGS: ScreenDef = {
  id: "settings",
  title: "Sozlamalar",
  icon: Settings,
  phase: "F2",
  summary: "Rejim (strict/dev), integratsiyalar, imzo kalitlari va guvoh manzili.",
};

interface AppInfo {
  version: string;
  aar_version: string;
}

export function App() {
  const [active, setActive] = useState<ScreenId>("live");
  const [info, setInfo] = useState<AppInfo | null>(null);

  useEffect(() => {
    invoke<AppInfo>("app_info")
      .then(setInfo)
      .catch(() => setInfo(null)); // brauzerda (Tauri'siz) ochilganda
  }, []);

  const current = [...SCREENS, SETTINGS].find((s) => s.id === active) ?? SCREENS[0]!;

  const navButton = (s: ScreenDef) => {
    const Icon = s.icon;
    return (
      <button
        key={s.id}
        className="nav-item"
        aria-current={s.id === active ? "page" : undefined}
        onClick={() => setActive(s.id)}
      >
        <Icon size={17} strokeWidth={1.75} />
        {s.title}
      </button>
    );
  };

  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Asosiy navigatsiya">
        <div className="brand" data-tauri-drag-region>
          <img src={mark} alt="" />
          TAMGA
        </div>
        {SCREENS.map(navButton)}
        <div className="nav-section">Agentlar</div>
        <div className="nav-item" style={{ cursor: "default" }}>
          <span className="dot" />
          Claude Code
          <span className="pill count" style={{ color: "var(--text-faint)" }}>
            F2
          </span>
        </div>
        <div className="nav-item" style={{ cursor: "default" }}>
          <span className="dot" />
          MCP proxy
          <span className="pill count" style={{ color: "var(--text-faint)" }}>
            F5
          </span>
        </div>
        <div className="sidebar-foot">
          {navButton(SETTINGS)}
          <div className="mono" style={{ color: "var(--text-faint)", padding: "8px 12px 0" }}>
            v{info?.version ?? "—"} · AAR {info?.aar_version ?? "0.1"}
          </div>
        </div>
      </nav>

      <main className="main">
        <header className="titlebar" data-tauri-drag-region>
          <h1 data-tauri-drag-region>{current.title}</h1>
          <div className="status" title="Daemon F2 bosqichida ulanadi" data-tauri-drag-region>
            <span className="dot" />
            tamgad ulanmagan
          </div>
          <WindowControls />
        </header>
        <div className="content">
          {active === "live" ? <LiveScreen /> : <PlaceholderScreen key={current.id} {...current} />}
        </div>
      </main>
    </div>
  );
}
