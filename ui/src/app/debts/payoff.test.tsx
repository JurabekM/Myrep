import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type PayoffDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// jsdom'da canvas yo'q: ECharts init soxtalashtiriladi; jadval va natijalar haqiqiy komponentlarda sinaladi.
vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })),
}));
vi.mock("echarts/charts", () => ({ LineChart: {} }));
vi.mock("echarts/components", () => ({
  GridComponent: {},
  LegendComponent: {},
  TooltipComponent: {},
}));
vi.mock("echarts/renderers", () => ({ CanvasRenderer: {} }));

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
    getLoans: vi.fn(),
    getRecovery: vi.fn(),
    setRecovery: vi.fn(),
    simulatePayoff: vi.fn(),
  },
}));

const RESULT: PayoffDto = {
  standard: {
    payment: money(32_214_768, "322 147,68 soʻm"),
    months: 14,
    totalInterest: money(61_006_757, "610 067,57 soʻm"),
    debtFreeDay: "2027-12-15",
    rows: [
      {
        month: 1,
        date: "2026-11-15",
        interest: money(7_800_000, "78 000 soʻm"),
        principal: money(24_414_768, "244 147,68 soʻm"),
        extra: money(0, "0 soʻm"),
        balance: money(365_585_232, "3 655 852,32 soʻm"),
      },
    ],
  },
  accelerated: {
    payment: money(32_214_768, "322 147,68 soʻm"),
    months: 9,
    totalInterest: money(39_701_867, "397 018,67 soʻm"),
    debtFreeDay: "2027-07-15",
    rows: [
      {
        month: 1,
        date: "2026-11-15",
        interest: money(7_800_000, "78 000 soʻm"),
        principal: money(24_414_768, "244 147,68 soʻm"),
        extra: money(16_000_000, "160 000 soʻm"),
        balance: money(349_585_232, "3 495 852,32 soʻm"),
      },
    ],
  },
  interestSaved: money(21_304_890, "213 048,90 soʻm"),
  monthsSaved: 5,
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue({
    name: "Baraka Daftari",
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
  vi.mocked(commands.getLoans).mockResolvedValue({
    status: "ok",
    data: {
      taken: [],
      given: [],
      totalOutstanding: money(0, "0 soʻm"),
      totalReceivable: money(0, "0 soʻm"),
      monthlyBurden: money(0, "0 soʻm"),
      monthlyIncome: money(300_000_000, "3 000 000 soʻm"),
      debtFreeDay: null,
    },
  });
  vi.mocked(commands.getRecovery).mockResolvedValue({
    status: "ok",
    data: {
      mode: "STANDARD",
      splitBp: [7000, 2000, 1000],
      income: money(300_000_000, "3 000 000 soʻm"),
      parts: [
        money(210_000_000, "2 100 000 soʻm"),
        money(60_000_000, "600 000 soʻm"),
        money(30_000_000, "300 000 soʻm"),
      ],
    },
  });
}

describe("payoff va 70/20/10", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "debts", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("simulyatsiya natijasi: qarzsiz kun, tejalgan ustama va jadval", async () => {
    vi.mocked(commands.simulatePayoff).mockResolvedValue({ status: "ok", data: RESULT });
    render(<App />);
    const card = (
      await screen.findByRole("heading", { name: "Payoff rejalashtiruvchisi" })
    ).closest("section");
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    const user = userEvent.setup();
    await user.type(within(card).getByLabelText("Qoldiq summa"), "3 900 000");
    await user.clear(within(card).getByLabelText("Muddat, oy"));
    await user.type(within(card).getByLabelText("Muddat, oy"), "14");
    await user.type(within(card).getByLabelText("Qo'shimcha oylik to'lov"), "160 000");
    await user.click(within(card).getByRole("button", { name: "Hisoblash" }));

    expect(await within(card).findByText("2027-07-15")).toBeInTheDocument();
    expect(within(card).getByText("213 048,90 soʻm")).toBeInTheDocument();
    expect(within(card).getByText("5 oy erta")).toBeInTheDocument();
    expect(within(card).getByRole("img", { name: /Qoldiq grafigi/ })).toBeInTheDocument();
    expect(within(card).getByText("3 495 852,32 soʻm")).toBeInTheDocument();
    expect(commands.simulatePayoff).toHaveBeenCalledWith({
      scheduleType: "ANNUITY",
      principal: "3 900 000",
      annualBp: 2400,
      markup: "",
      termMonths: 14,
      extraPerMonth: "160 000",
      startDate: null,
    });
  });

  it("70/20/10 qismlari ko'rsatiladi va jamg'arma 0 bo'lsa xato", async () => {
    vi.mocked(commands.setRecovery).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "SAVINGS_BELOW_MINIMUM" },
    });
    render(<App />);
    const card = (await screen.findByRole("heading", { name: /Qarz tiklash rejimi/ })).closest(
      "section",
    );
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    expect(await within(card).findByText("2 100 000 soʻm")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.clear(within(card).getByLabelText("Jamg'arma, %"));
    await user.type(within(card).getByLabelText("Jamg'arma, %"), "0");
    await user.clear(within(card).getByLabelText("Ehtiyoj, %"));
    await user.type(within(card).getByLabelText("Ehtiyoj, %"), "80");
    await user.click(within(card).getByRole("button", { name: "Saqlash" }));
    expect(
      await within(card).findByText("Jamg'arma ulushi kamida 1 % bo'lishi kerak"),
    ).toBeInTheDocument();
    expect(commands.setRecovery).toHaveBeenCalledWith({
      mode: "STANDARD",
      splitBp: [8000, 2000, 0],
    });
  });
});
