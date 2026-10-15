import {
  Banknote,
  BookOpen,
  Briefcase,
  CalendarDays,
  House,
  Receipt,
  ScrollText,
  Settings,
  Sprout,
  Tags,
  Wallet,
  type LucideIcon,
} from "lucide-react";

/** Sahifa identifikatorlari. Tarjima kaliti ham shu nom bilan: `nav.<id>`. */
export type PageId =
  | "home"
  | "income"
  | "expenses"
  | "future"
  | "budget"
  | "debts"
  | "ceremonies"
  | "partnerships"
  | "prices"
  | "chapters"
  | "settings"
  | "audit"
  | "whose-money"
  | "obligations";

/** Yon paneldagi bo'limlar (sahifalar); qo'shimcha sahifalar — faqat boshqa ekrandan ochiladi. */
export type NavPageId = Exclude<PageId, "audit" | "whose-money" | "obligations">;

export interface NavItem {
  readonly id: NavPageId;
  readonly icon: LucideIcon;
  /** Faqat tayyor bo'limlar bosiladi; qolganlari keyingi vazifalarda yoqiladi. */
  readonly enabled: boolean;
}

/**
 * Yon panel tartibi DESKTOP_PROMPT.md 7-bo'limdan olingan.
 * Ikonkalar: odam, hayvon, cho'chqa (piggy bank), qimor, alkogol va bank binosi ishlatilmaydi
 * (ikonka siyosati — icon-policy.test.ts).
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { id: "home", icon: House, enabled: true },
  { id: "income", icon: Banknote, enabled: true },
  { id: "expenses", icon: Receipt, enabled: true },
  { id: "future", icon: Sprout, enabled: true },
  { id: "budget", icon: Wallet, enabled: true },
  { id: "debts", icon: ScrollText, enabled: false },
  { id: "ceremonies", icon: CalendarDays, enabled: false },
  { id: "partnerships", icon: Briefcase, enabled: true },
  { id: "prices", icon: Tags, enabled: true },
  { id: "chapters", icon: BookOpen, enabled: true },
  { id: "settings", icon: Settings, enabled: true },
];
