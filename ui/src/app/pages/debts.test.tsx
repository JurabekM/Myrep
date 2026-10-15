import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type LoanDto, type LoansDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";
import { burdenText } from "./DebtsPage";

// Qarzlar: ro'yxat, «to'xta va o'yla» tekshiruvi, qarz qo'shish, to'lov. IPC soxta; hisob Rustda.
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
    checkBorrow: vi.fn(),
    addLoan: vi.fn(),
    payLoan: vi.fn(),
    createIou: vi.fn(),
  },
}));

const LOAN: LoanDto = {
  id: "0192e000-0000-7000-8000-0000000000d1",
  direction: "TAKEN",
  counterparty: "Dilshod",
  counterpartyType: "FRIEND",
  reason: "ta'mir",
  principal: money(120_000_000, "1 200 000 soʻm"),
  paid: money(0, "0 soʻm"),
  outstanding: money(120_000_000, "1 200 000 soʻm"),
  hasMarkup: false,
  incurredOn: "2026-10-15",
  nextDueOn: "2026-11-15",
  nextAmount: money(10_000_000, "100 000 soʻm"),
  lastDueOn: "2027-10-15",
  installments: 12,
  borrowVerdict: "CAUTION",
  agreementId: null,
  settled: false,
};

const EMPTY: LoansDto = {
  taken: [],
  given: [],
  totalOutstanding: money(0, "0 soʻm"),
  totalReceivable: money(0, "0 soʻm"),
  monthlyBurden: money(0, "0 soʻm"),
  monthlyIncome: money(300_000_000, "3 000 000 soʻm"),
  debtFreeDay: null,
};

const WITH_LOAN: LoansDto = {
  ...EMPTY,
  taken: [LOAN],
  totalOutstanding: LOAN.outstanding,
  monthlyBurden: money(10_000_000, "100 000 soʻm"),
  debtFreeDay: "2027-10-15",
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
  vi.mocked(commands.getLoans).mockResolvedValue({ status: "ok", data: EMPTY });
}

describe("qarzlar", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "debts", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("yuk foizi ko'rsatish yordamchisi", () => {
    expect(burdenText(3_333)).toBe("33,3 %");
    expect(burdenText(10_000)).toBe("100,0 %");
  });

  it("tekshiruv natijasi ko'rsatiladi va qarz reja bilan yoziladi", async () => {
    vi.mocked(commands.checkBorrow).mockResolvedValue({
      status: "ok",
      data: {
        verdict: "CAUTION",
        monthlyBurden: money(10_000_000, "100 000 soʻm"),
        monthlyIncome: money(300_000_000, "3 000 000 soʻm"),
        burdenBp: 3_333,
      },
    });
    vi.mocked(commands.addLoan).mockResolvedValue({ status: "ok", data: WITH_LOAN });
    render(<App />);
    expect(await screen.findByText("Olingan qarz yo'q.")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Kimdan"), "Dilshod");
    await user.type(screen.getByLabelText("Summa", { selector: "#loan-principal" }), "1 200 000");
    await user.clear(screen.getByLabelText(/To'lovlar soni/));
    await user.type(screen.getByLabelText(/To'lovlar soni/), "12");
    await user.click(screen.getByRole("button", { name: "Oylik yukni hisoblash" }));
    expect(
      await screen.findByText(
        /Ehtiyot bo'ling: yuk katta — oylik yuk 100 000 soʻm — daromadning 33,3 %/,
      ),
    ).toBeInTheDocument();
    expect(commands.checkBorrow).toHaveBeenCalledWith({ principal: "1 200 000", installments: 12 });

    const dateField = screen.getByLabelText("Birinchi to'lov sanasi");
    await user.type(dateField, "2026-11-15");
    await user.click(screen.getByLabelText("Bu zarurat (hashamat emas)"));
    await user.click(screen.getByRole("button", { name: "Qarzni yozish" }));

    expect(await screen.findByText("2027-10-15")).toBeInTheDocument();
    const call = vi.mocked(commands.addLoan).mock.calls[0]?.[0];
    expect(call?.installments).toBe(12);
    expect(call?.firstDueOn).toBe("2026-11-15");
    expect(call?.frictionNecessity).toBe(true);
    expect(call?.frictionAlternative).toBe(false);
  });

  it("to'lov qoldiqni kamaytiradi va ortiqcha to'lov xato beradi", async () => {
    vi.mocked(commands.getLoans).mockResolvedValue({ status: "ok", data: WITH_LOAN });
    vi.mocked(commands.payLoan).mockResolvedValueOnce({
      status: "ok",
      data: {
        ...WITH_LOAN,
        taken: [
          {
            ...LOAN,
            paid: money(10_000_000, "100 000 soʻm"),
            outstanding: money(110_000_000, "1 100 000 soʻm"),
            nextDueOn: "2026-12-15",
          },
        ],
      },
    });
    vi.mocked(commands.payLoan).mockResolvedValueOnce({
      status: "error",
      error: { code: "RULE", rule: "DEBT_OVERPAID" },
    });
    render(<App />);
    const list = await screen.findByRole("heading", { name: "Olingan qarzlar" });
    const card = list.closest("section") ?? list.parentElement;
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    const user = userEvent.setup();
    await user.type(within(card).getByLabelText("Summa"), "100 000");
    await user.click(within(card).getByRole("button", { name: "To'ladim" }));
    expect(await within(card).findByText("1 100 000 soʻm")).toBeInTheDocument();
    expect(commands.payLoan).toHaveBeenCalledWith({
      loanId: LOAN.id,
      amount: "100 000",
      paidOn: null,
    });

    await user.type(within(card).getByLabelText("Summa"), "5 000 000");
    await user.click(within(card).getByRole("button", { name: "To'ladim" }));
    expect(await within(card).findByText("Toʻlov nasiya qoldigʻidan katta.")).toBeInTheDocument();
  });
});
