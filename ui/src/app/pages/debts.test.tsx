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
    listMembers: vi.fn(),
    listChapters: vi.fn(),
    getWeeklyTasks: vi.fn(),
    getLoans: vi.fn(),
    checkBorrow: vi.fn(),
    addLoan: vi.fn(),
    payLoan: vi.fn(),
    setPayoffStrategy: vi.fn(),
    addSellableItem: vi.fn(),
    markSellableSold: vi.fn(),
    removeSellableItem: vi.fn(),
    createIou: vi.fn(),
  },
}));

const LOAN: LoanDto = {
  id: "0192e000-0000-7000-8000-0000000000d1",
  direction: "TAKEN",
  counterparty: "Jasur",
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
  contributions: [],
};

const EMPTY: LoansDto = {
  taken: [],
  given: [],
  totalOutstanding: money(0, "0 soʻm"),
  totalReceivable: money(0, "0 soʻm"),
  monthlyBurden: money(0, "0 soʻm"),
  monthlyIncome: money(300_000_000, "3 000 000 soʻm"),
  debtFreeDay: null,
  payoff: {
    strategy: "SNOWBALL",
    extra: money(0, "0 soʻm"),
    steps: [],
    totalMonths: 0,
    debtFreeDay: null,
    alternativeTotalMonths: 0,
  },
  sellable: { items: [], totalEstimate: money(0, "0 soʻm") },
  recoveryModeReset: false,
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
  vi.mocked(commands.getLoans).mockResolvedValue({ status: "ok", data: EMPTY });
  vi.mocked(commands.listMembers).mockResolvedValue({ status: "ok", data: [] });
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
    await user.type(screen.getByLabelText("Kimdan"), "Jasur");
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
      contributorId: null,
    });

    await user.type(within(card).getByLabelText("Summa"), "5 000 000");
    await user.click(within(card).getByRole("button", { name: "To'ladim" }));
    expect(await within(card).findByText("Toʻlov nasiya qoldigʻidan katta.")).toBeInTheDocument();
  });
  it("yopish tartibi: strategiya almashtiriladi va navbat yangilanadi", async () => {
    const second: LoanDto = {
      ...LOAN,
      id: "0192e000-0000-7000-8000-0000000000d2",
      counterparty: "Bank",
      hasMarkup: true,
      outstanding: money(500_000_000, "5 000 000 soʻm"),
    };
    const snowball: LoansDto = {
      ...WITH_LOAN,
      taken: [LOAN, second],
      payoff: {
        strategy: "SNOWBALL",
        extra: money(20_000_000, "200 000 soʻm"),
        steps: [
          {
            loanId: LOAN.id,
            counterparty: "Jasur",
            outstanding: LOAN.outstanding,
            hasMarkup: false,
            monthsToClear: 4,
            clearOn: "2027-02-15",
          },
          {
            loanId: second.id,
            counterparty: "Bank",
            outstanding: second.outstanding,
            hasMarkup: true,
            monthsToClear: 9,
            clearOn: "2027-07-15",
          },
        ],
        totalMonths: 9,
        debtFreeDay: "2027-07-15",
        alternativeTotalMonths: 10,
      },
    };
    const avalanche: LoansDto = {
      ...snowball,
      payoff: {
        ...snowball.payoff,
        strategy: "AVALANCHE",
        steps: [...snowball.payoff.steps].reverse(),
        totalMonths: 10,
        debtFreeDay: "2027-08-15",
        alternativeTotalMonths: 9,
      },
    };
    vi.mocked(commands.getLoans).mockResolvedValue({ status: "ok", data: snowball });
    vi.mocked(commands.setPayoffStrategy).mockResolvedValue({ status: "ok", data: avalanche });
    render(<App />);
    const order = await screen.findByRole("list", { name: "Yopish tartibi" });
    const rows = within(order).getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("1. Jasur · fokus");
    expect(rows[1]).toHaveTextContent(/2\. Bank · ustamali/);
    expect(screen.getByText("2027-07-15")).toBeInTheDocument();
    expect(screen.getByText("10 oy")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Qor to'pi" })).toBeChecked();

    const user = userEvent.setup();
    await user.click(screen.getByRole("radio", { name: "Ko'chki" }));
    expect(commands.setPayoffStrategy).toHaveBeenCalledWith("AVALANCHE");
    expect(await screen.findByText("2027-08-15")).toBeInTheDocument();
    const rows2 = within(screen.getByRole("list", { name: "Yopish tartibi" })).getAllByRole(
      "listitem",
    );
    expect(rows2[0]).toHaveTextContent(/1\. Bank · ustamali .* · fokus/);
    expect(screen.getByRole("radio", { name: "Ko'chki" })).toBeChecked();
  });

  it("sotiladigan buyum qo'shiladi va sotilgan deb belgilanadi", async () => {
    const added: LoansDto = {
      ...EMPTY,
      sellable: {
        items: [
          {
            id: "s-1",
            name: "Eski noutbuk",
            estimate: money(250_000_000, "2 500 000 soʻm"),
            note: null,
            soldOn: null,
          },
        ],
        totalEstimate: money(250_000_000, "2 500 000 soʻm"),
      },
    };
    const sold: LoansDto = {
      ...added,
      sellable: {
        items: added.sellable.items.map((item) => ({ ...item, soldOn: "2026-10-16" })),
        totalEstimate: money(0, "0 soʻm"),
      },
    };
    vi.mocked(commands.addSellableItem).mockResolvedValue({ status: "ok", data: added });
    vi.mocked(commands.markSellableSold).mockResolvedValue({ status: "ok", data: sold });
    vi.mocked(commands.removeSellableItem).mockResolvedValue({ status: "ok", data: EMPTY });
    render(<App />);
    const heading = await screen.findByRole("heading", { name: "Sotiladigan buyumlar" });
    const card = heading.closest("section") ?? heading.parentElement;
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    expect(within(card).getByText("Ro'yxat bo'sh.")).toBeInTheDocument();
    const user = userEvent.setup();
    const add = within(card).getByRole("button", { name: "Qo'shish" });
    expect(add).toBeDisabled();
    await user.type(within(card).getByLabelText("Buyum"), "Eski noutbuk");
    await user.type(within(card).getByLabelText("Taxminiy qiymat"), "2 500 000");
    await user.click(add);
    expect(commands.addSellableItem).toHaveBeenCalledWith({
      name: "Eski noutbuk",
      estimate: "2 500 000",
      note: null,
    });
    expect(await within(card).findByText(/Eski noutbuk · 2 500 000 soʻm/)).toBeInTheDocument();
    expect(within(card).getByLabelText("Buyum")).toHaveValue("");

    await user.click(within(card).getByRole("button", { name: "Sotildi" }));
    expect(commands.markSellableSold).toHaveBeenCalledWith("s-1");
    expect(await within(card).findByText(/sotildi 2026-10-16/)).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: "Sotildi" })).not.toBeInTheDocument();

    await user.click(within(card).getByRole("button", { name: "Eski noutbuk ni olib tashlash" }));
    expect(commands.removeSellableItem).toHaveBeenCalledWith("s-1");
    expect(await within(card).findByText("Ro'yxat bo'sh.")).toBeInTheDocument();
  });

  it("hissador tanlab to'lanadi; oxirgi qarz yopilsa tiklash rejimi xabari chiqadi", async () => {
    vi.mocked(commands.listMembers).mockResolvedValue({
      status: "ok",
      data: [
        { id: "m-1", name: "Akmal", role: "ADULT", hasPin: true },
        { id: "m-2", name: "Malika", role: "ADULT", hasPin: true },
      ],
    });
    vi.mocked(commands.getLoans).mockResolvedValue({ status: "ok", data: WITH_LOAN });
    vi.mocked(commands.payLoan).mockResolvedValue({
      status: "ok",
      data: {
        ...EMPTY,
        taken: [
          {
            ...LOAN,
            paid: LOAN.principal,
            outstanding: money(0, "0 soʻm"),
            settled: true,
            contributions: [{ memberId: "m-2", name: "Malika", total: LOAN.principal }],
          },
        ],
        recoveryModeReset: true,
      },
    });
    render(<App />);
    const list = await screen.findByRole("heading", { name: "Olingan qarzlar" });
    const card = list.closest("section") ?? list.parentElement;
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    const user = userEvent.setup();
    await user.selectOptions(
      await within(card).findByLabelText("Kim to'ladi (oila a'zosi)"),
      "m-2",
    );
    await user.type(within(card).getByLabelText("Summa"), "1 200 000");
    await user.click(within(card).getByRole("button", { name: "To'ladim" }));
    expect(commands.payLoan).toHaveBeenCalledWith({
      loanId: LOAN.id,
      amount: "1 200 000",
      paidOn: null,
      contributorId: "m-2",
    });
    expect(await within(card).findByText(/Hissalar: Malika 1 200 000 soʻm/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Qarz tiklash rejimi STANDARD ga qaytdi");
  });
});
