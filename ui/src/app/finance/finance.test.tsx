import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { AUDIT, HOME, VAULT, WHOSE, money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Moliya oqimlari: IPC soxtalashtiriladi, mantiq va ko'rinish haqiqiy komponentlarda sinaladi.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
    lock: vi.fn(),
    getHome: vi.fn(),
    listIncomesThisMonth: vi.fn(),
    listRecentIncomes: vi.fn(),
    createIncome: vi.fn(),
    acceptShare: vi.fn(),
    getVault: vi.fn(),
    respondProgression: vi.fn(),
    setShareRule: vi.fn(),
    setInitialBalance: vi.fn(),
    withdraw: vi.fn(),
    getAudit: vi.fn(),
    addAuditExpense: vi.fn(),
    markUnexplainedAsDaily: vi.fn(),
    finishAudit: vi.fn(),
    getWhoseMoney: vi.fn(),
    listCategories: vi.fn(),
    listObligations: vi.fn(),
    addObligation: vi.fn(),
    setObligationActive: vi.fn(),
    listDebts: vi.fn(),
    addDebt: vi.fn(),
    payDebt: vi.fn(),
    listChapters: vi.fn(),
    getChapter: vi.fn(),
    getWeeklyTasks: vi.fn(),
    setTaskDone: vi.fn(),
    saveDaftarPage: vi.fn(),
  },
}));

const APP_INFO = {
  name: "Baraka Daftari",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const INCOME = {
  id: "0192a000-0000-7000-8000-0000000000d1",
  source: "Kunlik ish",
  channel: "CASH" as const,
  amount: money(15_000_000, "150 000 soʻm"),
  occurredOn: "2026-10-14",
  note: null,
};

describe("moliya oqimlari", () => {
  beforeEach(() => {
    vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: true },
    });
    resetFinanceMocks();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("Ctrl+N: daromad kiritiladi, ulush taklifi Enter bilan ajratiladi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.createIncome).mockResolvedValue({
      status: "ok",
      data: { income: INCOME, shareSuggestion: money(800_000, "8 000 soʻm") },
    });
    vi.mocked(commands.acceptShare).mockResolvedValue({ status: "ok", data: VAULT });
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: "Assalomu alaykum!" });

    await user.keyboard("{Control>}n{/Control}");
    await user.type(await screen.findByLabelText("Summa"), "150000{Enter}");

    expect(commands.createIncome).toHaveBeenCalledWith({
      amount: "150000",
      source: "Kunlik ish",
      channel: "CASH",
      note: null,
    });
    // Ulush bosqichida birinchi tugma fokusda: Enter — ajratish, summa ulush taklifidan olinadi.
    await user.keyboard("{Enter}");
    expect(commands.acceptShare).toHaveBeenCalledWith(INCOME.id, "8 000 soʻm");
  });

  it("pul olish: 5 soniya o'ylash pauzasi, noto'g'ri PIN xabari", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.withdraw).mockResolvedValue({
      status: "error",
      error: { code: "WRONG_PIN" },
    });
    useUiStore.setState({ page: "future" });
    render(<App />);

    const submit = await screen.findByRole("button", { name: "Olish" });
    expect(submit).toBeDisabled();
    expect(screen.getByText("Bir oz oʻylab koʻring: 5 soniya.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Summa"), "30000");
    await user.type(screen.getByLabelText("Sabab"), "Dori");
    await user.type(screen.getByLabelText("PIN"), "123456");
    // Pauza tugagach tugma yoqiladi (real vaqt: ~5 s).
    await waitFor(() => expect(submit).toBeEnabled(), { timeout: 7000 });

    await user.click(submit);
    expect(commands.withdraw).toHaveBeenCalledWith("123456", { amount: "30000", reason: "Dori" });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "PIN notoʻgʻri. Qayta urinib koʻring.",
    );
  }, 15_000);

  it("audit: birinchi qadam Enter bilan, xarajat qadamida fokus summa maydonida", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.addAuditExpense).mockResolvedValue({
      status: "ok",
      data: {
        ...AUDIT,
        spent: [
          {
            categoryId: AUDIT.categories[0]?.id ?? null,
            name: "Ijara",
            systemKey: "RENT",
            amount: money(500_000, "5 000 soʻm"),
          },
        ],
      },
    });
    useUiStore.setState({ page: "audit" });
    render(<App />);

    expect(await screen.findByText("Qadam 1 / 4 · Daromad va majburiyatlar")).toBeInTheDocument();
    // Birinchi qadamda «Keyingi» fokusda: Enter bilan keyingi qadamga o'tiladi.
    await user.keyboard("{Enter}");
    const amount = await screen.findByLabelText("Summa");
    expect(amount).toHaveFocus();

    await user.type(amount, "5000{Enter}");
    expect(commands.addAuditExpense).toHaveBeenCalledWith("5000", AUDIT.categories[0]?.id, null);
  });

  it("kimning puli?: bo'laklar backend ulushi (bp) bo'yicha chiziladi", async () => {
    vi.mocked(commands.getWhoseMoney).mockResolvedValue({
      status: "ok",
      data: {
        ...WHOSE,
        total: money(1_000_000, "10 000 soʻm"),
        parts: [
          { owner: "LANDLORD", amount: money(600_000, "6 000 soʻm"), shareBp: 6000 },
          { owner: "SELF", amount: money(400_000, "4 000 soʻm"), shareBp: 4000 },
        ],
      },
    });
    useUiStore.setState({ page: "whose-money" });
    render(<App />);

    const meters = await screen.findAllByRole("meter");
    expect(meters[0]).toHaveAttribute("aria-valuenow", "60");
    expect(meters[1]).toHaveAttribute("aria-valuenow", "40");
    expect(screen.getByText("Uy egasi")).toBeInTheDocument();
  });

  it("bosh sahifa: «O'zingizga to'langan» va odat backend ko'rsatkichlaridan chiqadi", async () => {
    vi.mocked(commands.getHome).mockResolvedValue({
      status: "ok",
      data: {
        ...HOME,
        paidToSelf: money(800_000, "8 000 soʻm"),
        habit: { currentStreakWeeks: 3, totalWeeks: 5, thisWeekDone: true },
      },
    });
    render(<App />);

    expect(await screen.findByText("8 000 soʻm")).toBeInTheDocument();
    expect(screen.getByText("Ketma-ket 3 hafta")).toBeInTheDocument();
    expect(screen.getByText("Bu hafta ajratildi")).toBeInTheDocument();
  });
});
