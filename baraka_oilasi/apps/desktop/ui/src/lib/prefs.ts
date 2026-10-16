// Shu qurilmaning ko'rinish sozlamalari: til (qulf ekranida ham kerak — baza hali ochilmagan),
// shrift o'lchami va mavzu. Maxfiy emas, shuning uchun localStorage'da; summalar bu yerga tushmaydi.
// Saqlab bo'lmasa (xususiy rejim) — standart qiymatlar bilan ishlaydi.

export const FONT_SCALES = [100, 115, 130, 150] as const;
export type FontScale = (typeof FONT_SCALES)[number];
export type Theme = "dark" | "light";

const KEY = "baraka.display";

export type DisplayPrefs = { locale: string | null; fontScale: FontScale; theme: Theme };

const DEFAULTS: DisplayPrefs = { locale: null, fontScale: 100, theme: "dark" };

export function loadPrefs(): DisplayPrefs {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULTS;
    const p = JSON.parse(raw) as Partial<DisplayPrefs>;
    return {
      locale: typeof p.locale === "string" ? p.locale : null,
      fontScale: FONT_SCALES.includes(p.fontScale as FontScale) ? (p.fontScale as FontScale) : 100,
      theme: p.theme === "light" ? "light" : "dark",
    };
  } catch {
    return DEFAULTS;
  }
}

export function savePrefs(patch: Partial<DisplayPrefs>): DisplayPrefs {
  const next = { ...loadPrefs(), ...patch };
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // saqlanmasa ham joriy oynada qo'llanadi
  }
  applyPrefs(next);
  return next;
}

/** `<html>`: shrift masshtabi (Tailwind o'lchamlari rem'da — hammasi birga kattalashadi) va mavzu. */
export function applyPrefs(p: DisplayPrefs = loadPrefs()) {
  const root = document.documentElement;
  root.style.fontSize = p.fontScale === 100 ? "" : `${p.fontScale}%`;
  if (p.theme === "light") root.dataset.theme = "light";
  else delete root.dataset.theme;
}
