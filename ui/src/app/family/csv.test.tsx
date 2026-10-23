import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// CSV ustasi: matn → moslash → ko'rib chiqish (IPC soxta) → import. Tahlil Rustda, bu yerda oqim sinaladi.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
    lock: vi.fn(),
    getHome: vi.fn(),
    listIncomesThisMonth: vi.fn(),
    listRecentIncomes: vi.fn(),
    getVault: vi.fn(),
    getAudit: vi.fn(),
    getWhoseMoney: vi.fn(),
    listCategories: vi.fn(),
    listObligations: vi.fn(),
    listDebts: vi.fn(),
    listChapters: vi.fn(),
    getWeeklyTasks: vi.fn(),
    getMonthSummary: vi.fn(),
    listMonthExpenses: vi.fn(),
    getHavasLimit: vi.fn(),
    listMembers: vi.fn(),
    listTreats: vi.fn(),
    listHabits: vi.fn(),
    previewCsvImport: vi.fn(),
    importCsvExpenses: vi.fn(),
  },
}));

const SUMMARY = {
  periodStart: "2026-10-01",
  periodEnd: "2026-11-01",
  weekStart: "2026-10-09",
  today: "2026-10-15",
  zarur: money(0, "0 soʻm"),
  kerak: money(0, "0 soʻm"),
  havas: money(0, "0 soʻm"),
  sadaqa: money(0, "0 soʻm"),
  gifts: money(0, "0 soʻm"),
  ostentation: money(0, "0 soʻm"),
  fundedByDebt: money(0, "0 soʻm"),
};

const TEXT = "Sana;Summa;Izoh\n10.10.2026;-15 000;Non\n11.10.2026;250 000;Maosh";

describe("CSV import ustasi", () => {
  beforeEach(() => {
    vi.mocked(commands.getAppInfo).mockResolvedValue({
      name: "Baraka Dastur",
      version: "0.1.0",
      platform: "windows",
      arch: "x86_64",
      buildProfile: "release",
    });
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: true },
    });
    resetFinanceMocks();
    vi.mocked(commands.getMonthSummary).mockResolvedValue({ status: "ok", data: SUMMARY });
    vi.mocked(commands.listMonthExpenses).mockResolvedValue({ status: "ok", data: [] });
    vi.mocked(commands.getHavasLimit).mockResolvedValue({
      status: "ok",
      data: {
        limit: money(0, "0 soʻm"),
        spent: money(0, "0 soʻm"),
        level: "OK",
        active: false,
        adults: [],
      },
    });
    vi.mocked(commands.listMembers).mockResolvedValue({ status: "ok", data: [] });
    vi.mocked(commands.listTreats).mockResolvedValue({ status: "ok", data: [] });
    vi.mocked(commands.listHabits).mockResolvedValue({ status: "ok", data: [] });
    vi.mocked(commands.previewCsvImport).mockResolvedValue({
      status: "ok",
      data: {
        rows: [
          {
            line: 2,
            date: "2026-10-10",
            amount: money(1_500_000, "15 000 soʻm"),
            note: "Non",
            error: null,
            skipped: false,
          },
          {
            line: 3,
            date: "2026-10-11",
            amount: money(25_000_000, "250 000 soʻm"),
            note: "Maosh",
            error: null,
            skipped: true,
          },
        ],
        importable: 1,
        skipped: 1,
        failed: 0,
      },
    });
    vi.mocked(commands.importCsvExpenses).mockResolvedValue({ status: "ok", data: 1 });
    useUiStore.setState({ page: "expenses", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("matn → moslash → ko'rib chiqish → import", async () => {
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "CSV import" }));
    const dialog = screen.getByRole("dialog", { name: "CSV import" });

    await user.type(within(dialog).getByLabelText("Matn (CSV)"), TEXT);
    await user.click(within(dialog).getByRole("button", { name: "Davom etish" }));

    // Sarlavha ustunlari ro'yxatda ko'rinadi; standart moslash: 1 — sana, 2 — summa.
    expect(within(dialog).getByLabelText("Sana ustuni")).toHaveValue("0");
    expect(within(dialog).getByLabelText("Summa ustuni")).toHaveValue("1");
    await user.selectOptions(within(dialog).getByLabelText("Izoh ustuni"), "2");
    await user.click(within(dialog).getByRole("button", { name: "Koʻrib chiqish" }));

    expect(await within(dialog).findByText("15 000 soʻm")).toBeInTheDocument();
    expect(within(dialog).getByText("tashlanadi (kirim)")).toBeInTheDocument();
    expect(commands.previewCsvImport).toHaveBeenCalledWith({
      text: TEXT,
      mapping: {
        delimiter: null,
        hasHeader: true,
        dateColumn: 0,
        amountColumn: 1,
        noteColumn: 2,
        categoryId: null,
        skipPositive: true,
      },
    });

    await user.click(within(dialog).getByRole("button", { name: "Import qilish (1)" }));
    expect(await within(dialog).findByText("1 ta xarajat yozildi.")).toBeInTheDocument();
    expect(commands.importCsvExpenses).toHaveBeenCalledTimes(1);
  });

  it("xatoli satrlar bo'lsa import tugmasi o'chiq", async () => {
    vi.mocked(commands.previewCsvImport).mockResolvedValue({
      status: "ok",
      data: {
        rows: [
          {
            line: 2,
            date: "xato",
            amount: null,
            note: null,
            error: "CSV_BAD_DATE",
            skipped: false,
          },
        ],
        importable: 0,
        skipped: 0,
        failed: 1,
      },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "CSV import" }));
    const dialog = screen.getByRole("dialog", { name: "CSV import" });
    await user.type(within(dialog).getByLabelText("Matn (CSV)"), "xato;-5");
    await user.click(within(dialog).getByRole("button", { name: "Davom etish" }));
    await user.click(within(dialog).getByRole("button", { name: "Koʻrib chiqish" }));

    expect(await within(dialog).findByText("sana oʻqilmadi")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Import qilish (0)" })).toBeDisabled();
    expect(commands.importCsvExpenses).not.toHaveBeenCalled();
  });
});
