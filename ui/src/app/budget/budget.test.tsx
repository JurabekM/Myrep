import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type BudgetDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Byudjet oqimi: IPC soxtalashtiriladi, ko'rinish va o'zaro ta'sir haqiqiy komponentlarda sinaladi.
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
    getBudget: vi.fn(),
    addSubscription: vi.fn(),
    markSubscriptionUsed: vi.fn(),
    cancelSubscription: vi.fn(),
    addEnvelope: vi.fn(),
    closeEnvelopeWeek: vi.fn(),
    transferToVaultFromRescue: vi.fn(),
    setBaselinePeriod: vi.fn(),
  },
}));

const APP_INFO = {
  name: "Baraka Daftari",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const SUB_ID = "0192e000-0000-7000-8000-0000000000b1";
const ENV_ID = "0192e000-0000-7000-8000-0000000000c1";

const SUBSCRIPTION = {
  id: SUB_ID,
  name: "Telegram Premium",
  monthly: money(3_000_000, "30 000 soʻm"),
  yearly: null,
  lastUsedOn: null,
  cancelledOn: null,
  forgotten: false,
};

const ENVELOPE = {
  id: ENV_ID,
  name: "Bozor",
  weeklyLimit: money(50_000_000, "500 000 soʻm"),
  spentThisWeek: money(0, "0 soʻm"),
  leftoverThisWeek: money(50_000_000, "500 000 soʻm"),
  closedThisWeek: false,
  categoryId: null,
};

const RESCUE = {
  havas: money(0, "0 soʻm"),
  subscriptions: money(1_000_000, "10 000 soʻm"),
  envelopes: money(0, "0 soʻm"),
  total: money(1_000_000, "10 000 soʻm"),
  transferred: money(0, "0 soʻm"),
  available: money(1_000_000, "10 000 soʻm"),
  spentMore: false,
  hasBaseline: false,
  baselineStart: null,
  periodStart: "2026-10-01",
  periodEnd: "2026-11-01",
};

const BUDGET: BudgetDto = {
  rescue: RESCUE,
  subscriptions: [SUBSCRIPTION],
  envelopes: [ENVELOPE],
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
  vi.mocked(commands.getSecurityStatus).mockResolvedValue({
    status: "ok",
    data: { setUp: true, unlocked: true },
  });
  resetFinanceMocks();
  vi.mocked(commands.getBudget).mockResolvedValue({ status: "ok", data: BUDGET });
}

async function openBudget(): Promise<void> {
  useUiStore.setState({ page: "budget" });
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Byudjet" });
  // Kartalar so'rovdan keyin chiqadi: obuna qatori paydo bo'lguncha kutiladi.
  await screen.findByText("Telegram Premium");
}

describe("byudjet", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("qutqarilgan pul hisobini ko'rsatadi", async () => {
    await openBudget();
    expect(await screen.findAllByText("10 000 soʻm")).not.toHaveLength(0);
    expect(screen.getByText("Telegram Premium")).toBeInTheDocument();
    expect(screen.getByText("Bozor")).toBeInTheDocument();
  });

  it("ortiqcha o'tkazish rad etiladi va xabar chiqadi", async () => {
    vi.mocked(commands.transferToVaultFromRescue).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "RESCUE_EXCEEDS_AVAILABLE" },
    });
    await openBudget();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Summa"), "20 000");
    await user.click(screen.getByRole("button", { name: "O'tkazish" }));
    expect(await screen.findByText("O'tkazish qutqarilgan summadan katta")).toBeInTheDocument();
    expect(commands.transferToVaultFromRescue).toHaveBeenCalledWith({ amount: "20 000" });
  });

  it("yangi obuna qo'shiladi", async () => {
    const added = {
      ...SUBSCRIPTION,
      id: "0192e000-0000-7000-8000-0000000000b2",
      name: "Zoom",
      monthly: money(5_000_000, "50 000 soʻm"),
    };
    vi.mocked(commands.addSubscription).mockResolvedValue({
      status: "ok",
      data: { ...BUDGET, subscriptions: [SUBSCRIPTION, added] },
    });
    await openBudget();
    const user = userEvent.setup();
    const [nameField] = screen.getAllByLabelText("Nomi");
    if (nameField === undefined) {
      throw new Error("Nomi maydoni topilmadi");
    }
    await user.type(nameField, "Zoom");
    await user.type(screen.getByLabelText("Oylik narx"), "50 000");
    await user.click(screen.getByRole("button", { name: "Obuna qo'shish" }));
    expect(await screen.findByText("Zoom")).toBeInTheDocument();
    expect(commands.addSubscription).toHaveBeenCalledWith({
      name: "Zoom",
      monthly: "50 000",
      yearly: null,
    });
  });

  it("obuna bekor qilinadi va holat yangilanadi", async () => {
    const cancelled = { ...SUBSCRIPTION, cancelledOn: "2026-10-15" };
    vi.mocked(commands.cancelSubscription).mockResolvedValue({
      status: "ok",
      data: { ...BUDGET, subscriptions: [cancelled] },
    });
    await openBudget();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Bekor qilish" }));
    expect(await screen.findByText("Bekor qilingan: 2026-10-15")).toBeInTheDocument();
    expect(commands.cancelSubscription).toHaveBeenCalledWith(SUB_ID);
  });

  it("konvert hafta yakunida yopiladi", async () => {
    const closed = { ...ENVELOPE, closedThisWeek: true, leftoverThisWeek: money(0, "0 soʻm") };
    vi.mocked(commands.closeEnvelopeWeek).mockResolvedValue({
      status: "ok",
      data: { ...BUDGET, envelopes: [closed] },
    });
    await openBudget();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Hafta yakuni: qoldiqni qutqarish" }));
    expect(await screen.findByRole("button", { name: "Bu hafta yopilgan" })).toBeDisabled();
    expect(commands.closeEnvelopeWeek).toHaveBeenCalledWith(ENV_ID);
  });
});
