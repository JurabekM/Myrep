import { vi } from "vitest";
import {
  type AuditDto,
  type HomeDto,
  type VaultDto,
  type WhoseMoneyDto,
  commands,
} from "../bindings/bindings";

/** Testlar uchun pul qiymati (DTO shakli). `formatted` — backend formatlagan matn. */
export function money(minor: number, formatted: string) {
  return { minor: String(minor), currency: "UZS", formatted };
}

export const HOME: HomeDto = {
  paidToSelf: money(0, "0 soʻm"),
  vaultBalance: money(0, "0 soʻm"),
  income: money(0, "0 soʻm"),
  monthResult: money(0, "0 soʻm"),
  habit: { currentStreakWeeks: 0, totalWeeks: 0, thisWeekDone: false },
  audit: { done: false, periodStart: "2026-09-01", periodEnd: "2026-10-01" },
};

export const VAULT: VaultDto = {
  balance: money(0, "0 soʻm"),
  savedThisMonth: money(0, "0 soʻm"),
  hasInitial: true,
  rule: {
    mode: "PERCENT",
    basisPoints: 500,
    fixedAmount: null,
    progressive: false,
  },
  habit: { currentStreakWeeks: 0, totalWeeks: 0, thisWeekDone: false },
  progressionOfferBp: null,
  history: [],
};

export const AUDIT: AuditDto = {
  periodStart: "2026-09-01",
  periodEnd: "2026-10-01",
  done: false,
  income: money(0, "0 soʻm"),
  expenses: money(0, "0 soʻm"),
  obligationsTotal: money(0, "0 soʻm"),
  obligationsUnrecorded: money(0, "0 soʻm"),
  netSavings: money(0, "0 soʻm"),
  unexplained: money(0, "0 soʻm"),
  lines: [],
  spent: [],
  categories: [
    { id: "0192a000-0000-7000-8000-0000000000c1", name: "Ijara", systemKey: "RENT" },
    {
      id: "0192a000-0000-7000-8000-0000000000c2",
      name: "Mayda kundalik",
      systemKey: "DAILY_SMALL",
    },
  ],
};

export const WHOSE: WhoseMoneyDto = {
  periodStart: "2026-10-01",
  periodEnd: "2026-11-01",
  total: money(0, "0 soʻm"),
  parts: [],
};

/** Moliya buyruqlari uchun bo'sh (xavfsiz) javoblar. Testlar kerak bo'lsa, ularni o'zgartiradi. */
export function resetFinanceMocks(): void {
  vi.mocked(commands.getHome).mockResolvedValue({ status: "ok", data: HOME });
  vi.mocked(commands.listIncomesThisMonth).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.listRecentIncomes).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getVault).mockResolvedValue({ status: "ok", data: VAULT });
  vi.mocked(commands.getAudit).mockResolvedValue({ status: "ok", data: AUDIT });
  vi.mocked(commands.getWhoseMoney).mockResolvedValue({ status: "ok", data: WHOSE });
  vi.mocked(commands.listCategories).mockResolvedValue({ status: "ok", data: AUDIT.categories });
  vi.mocked(commands.listObligations).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.listDebts).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.listChapters).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getWeeklyTasks).mockResolvedValue({ status: "ok", data: null });
}
