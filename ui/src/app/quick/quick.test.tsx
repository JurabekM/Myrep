import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { createQueryClient } from "../query-client";
import { QuickWindow } from "./QuickWindow";

// Mini oyna: IPC soxtalashtiriladi. Qulf holatida summa va ro'yxat yo'qligi — asosiy talab.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
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
    addExpense: vi.fn(),
    showMainWindow: vi.fn(),
    hideQuickWindow: vi.fn(),
  },
}));

function renderQuick() {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <QuickWindow />
    </QueryClientProvider>,
  );
}

describe("tez xarajat mini oynasi", () => {
  beforeEach(() => {
    resetFinanceMocks();
    vi.mocked(commands.showMainWindow).mockResolvedValue({ status: "ok", data: null });
    vi.mocked(commands.hideQuickWindow).mockResolvedValue({ status: "ok", data: null });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("qulf holatida summa ko'rsatmaydi va asosiy oynani ochadi", async () => {
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: false },
    });
    renderQuick();
    expect(await screen.findByText("Daftar qulflangan")).toBeInTheDocument();
    expect(screen.queryByLabelText("Summa")).not.toBeInTheDocument();
    expect(screen.queryByText(/soʻm/)).not.toBeInTheDocument();
    expect(commands.listCategories).not.toHaveBeenCalled();

    await userEvent.setup().click(screen.getByRole("button", { name: "Asosiy oynani ochish" }));
    expect(commands.showMainWindow).toHaveBeenCalledTimes(1);
  });

  it("ochiq holatda xarajatni saqlaydi va formani tozalaydi", async () => {
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: true },
    });
    vi.mocked(commands.addExpense).mockResolvedValue({
      status: "ok",
      data: {
        id: "0192e000-0000-7000-8000-0000000000e1",
        occurredOn: "2026-10-15",
        amount: money(1_500_000, "15 000 soʻm"),
        categoryName: null,
        necessity: "KERAK",
        note: "Non",
        isGift: false,
        isOstentation: false,
        fundedByDebt: false,
      },
    });
    renderQuick();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Summa"), "15 000");
    await user.type(screen.getByLabelText("Izoh (ixtiyoriy)"), "Non");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));

    expect(await screen.findByText("Saqlandi")).toBeInTheDocument();
    expect(commands.addExpense).toHaveBeenCalledWith({
      amount: "15 000",
      categoryId: null,
      note: "Non",
      isGift: false,
      isOstentation: false,
      fundedByDebt: false,
      occurredOn: null,
    });
    expect(screen.getByLabelText("Summa")).toHaveValue("");
  });

  it("Escape mini oynani yashiradi", async () => {
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: true },
    });
    renderQuick();
    await screen.findByLabelText("Summa");
    await userEvent.setup().keyboard("{Escape}");
    expect(commands.hideQuickWindow).toHaveBeenCalledTimes(1);
  });
});
