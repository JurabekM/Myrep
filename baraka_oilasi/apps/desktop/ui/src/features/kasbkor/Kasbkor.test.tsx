import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { useUi } from "../../state/ui";
import { KkEntryDialog } from "./KkEntryDialog";
import { KkHomeScreen } from "./KkHomeScreen";
import { KkSalaryDialog } from "./KkSalaryDialog";

const kkOverview = vi.fn();
const kkRecordSale = vi.fn();
const kkRecordMove = vi.fn();
const kkSetOwnerSalary = vi.fn();
const kkPayOwnerSalary = vi.fn();
const recordExpense = vi.fn();
const allocateToVault = vi.fn();
const categories = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkOverview: (...a: unknown[]) => kkOverview(...a),
    kkRecordSale: (...a: unknown[]) => kkRecordSale(...a),
    kkRecordMove: (...a: unknown[]) => kkRecordMove(...a),
    kkSetOwnerSalary: (...a: unknown[]) => kkSetOwnerSalary(...a),
    kkPayOwnerSalary: (...a: unknown[]) => kkPayOwnerSalary(...a),
    recordExpense: (...a: unknown[]) => recordExpense(...a),
    allocateToVault: (...a: unknown[]) => allocateToVault(...a),
    categories: (...a: unknown[]) => categories(...a),
  },
}));

const money = (formatted: string, plain: string) => ({ minor: "0", currency: "UZS", formatted, plain });
const ok = (data: unknown) => ({ status: "ok", data });

const overview = {
  periodStart: "2026-10-01",
  periodEnd: "2026-10-31",
  ownerSalary: money("6 000 000 soʻm", "6 000 000"),
  revenue: money("20 000 000 soʻm", "20 000 000"),
  expenses: money("8 500 000 soʻm", "8 500 000"),
  cashFlow: money("11 500 000 soʻm", "11 500 000"),
  ownerDraws: money("1 000 000 soʻm", "1 000 000"),
  ownerSalaryTransferred: money("0 soʻm", "0"),
  contributions: money("0 soʻm", "0"),
  ownerPaid: money("1 000 000 soʻm", "1 000 000"),
  salaryRemaining: money("5 000 000 soʻm", "5 000 000"),
  overdrawn: null,
  cash: money("-200 000 soʻm", "-200 000"),
  card: money("12 300 000 soʻm", "12 300 000"),
  equipmentPurchases: money("0 soʻm", "0"),
  equipmentSales: money("0 soʻm", "0"),
  profit: {
    revenue: money("20 000 000 soʻm", "20 000 000"),
    cogs: money("0 soʻm", "0"),
    operatingExpenses: money("8 500 000 soʻm", "8 500 000"),
    visibleProfit: money("11 500 000 soʻm", "11 500 000"),
    ownerLabor: null,
    familyLabor: money("0 soʻm", "0"),
    familyLaborPaid: money("0 soʻm", "0"),
    depreciation: money("0 soʻm", "0"),
    disposal: money("0 soʻm", "0"),
    trueProfit: money("11 500 000 soʻm", "11 500 000"),
  },
  negativeWallets: ["CASH"],
  salaryCarry: null,
  closedUntil: null,
  closeDue: null,
  cashClosedUntil: null,
  receivables: money("0 soʻm", "0"),
  receivablesOverdue: money("0 soʻm", "0"),
  entries: [
    { id: "e1", kind: "SALE", wallet: "CARD", toWallet: null, amount: money("20 000 000 soʻm", "20 000 000"), occurredOn: "2026-10-05", note: "Toʻy libosi", categoryId: null },
    { id: "e2", kind: "EXPENSE", wallet: "CARD", toWallet: null, amount: money("8 500 000 soʻm", "8 500 000"), occurredOn: "2026-10-06", note: null, categoryId: "c-mat" },
    { id: "e3", kind: "TRANSFER", wallet: "CARD", toWallet: "CASH", amount: money("300 000 soʻm", "300 000"), occurredOn: "2026-10-07", note: null, categoryId: null },
  ],
};

const cats = [
  { id: "c-mat", nameKey: "category.kk.materials", customName: null, defaultNecessity: null, isSystem: true },
  { id: "c-rent", nameKey: "category.kk.rent", customName: null, defaultNecessity: null, isSystem: true },
];

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor", () => {
  beforeEach(() => {
    for (const f of [kkOverview, kkRecordSale, kkRecordMove, kkSetOwnerSalary, kkPayOwnerSalary, recordExpense, allocateToVault, categories]) f.mockReset();
    kkOverview.mockResolvedValue(ok(overview));
    categories.mockResolvedValue(ok(cats));
    useUi.setState({ kkEntry: null });
  });

  it("bosh sahifa: 2-raqam — egasiga toʻlangan, pul oqimi, manfiy hamyon ogohlantirishi; axe toza", async () => {
    const { container } = wrap(<KkHomeScreen spaceId="s-kk" />);
    expect(await screen.findByText("Oyiga 6 000 000 soʻm", { exact: false })).toBeInTheDocument();
    expect(screen.getByTestId("kk-owner-paid")).toHaveTextContent("1 000 000 soʻm");
    expect(screen.getByTestId("kk-cash-flow")).toHaveTextContent("11 500 000 soʻm");
    expect(screen.getByTestId("kk-salary-remaining")).toHaveTextContent("Shu oy qoldi: 5 000 000 soʻm");
    expect(screen.getByTestId("kk-wallet-CASH")).toHaveTextContent("-200 000 soʻm");
    expect(screen.getAllByRole("note").map((n) => n.textContent)).toContainEqual(expect.stringContaining("Qoldiq manfiy"));
    const table = within(screen.getByRole("region", { name: "Shu oy yozuvlari" })).getByRole("table");
    expect(await within(table).findByText("Material va xomashyo")).toBeInTheDocument();
    expect(within(table).getByText("Karta → Naqd kassa")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("tushum: summa va hamyon matn holida yadroga boradi", async () => {
    kkRecordSale.mockResolvedValue(ok(overview));
    const onClose = vi.fn();
    const user = userEvent.setup();
    const { container } = wrap(<KkEntryDialog spaceId="s-kk" mode="SALE" onClose={onClose} />);
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Summa"), "2 500 000");
    await user.click(screen.getByRole("button", { name: "Karta" }));
    await user.type(screen.getByLabelText("Buyurtma yoki mijoz"), "Kelin koʻylagi");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(kkRecordSale).toHaveBeenCalledWith("s-kk", { amount: "2 500 000", channel: "CARD", occurredOn: null, note: "Kelin koʻylagi" });
    expect(onClose).toHaveBeenCalled();
  });

  it("chiqim: Kasb-kor kategoriyasi bilan umumiy `recordExpense`", async () => {
    recordExpense.mockResolvedValue(ok({}));
    const user = userEvent.setup();
    wrap(<KkEntryDialog spaceId="s-kk" mode="EXPENSE" onClose={() => undefined} />);
    await screen.findByRole("option", { name: "Ijara (ustaxona, doʻkon)" });
    await user.type(screen.getByLabelText("Summa"), "1 200 000");
    await user.selectOptions(screen.getByLabelText("Kategoriya"), "c-rent");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(recordExpense).toHaveBeenCalledWith("s-kk", expect.objectContaining({ amount: "1 200 000", categoryId: "c-rent", channel: "CASH", necessity: null }));
  });

  it("hamyonlar orasida: bir xil hamyon — yadro xatosi koʻrsatiladi", async () => {
    kkRecordMove.mockResolvedValue({ status: "error", error: { code: "SAME_WALLET", field: "toWallet" } });
    const user = userEvent.setup();
    wrap(<KkEntryDialog spaceId="s-kk" mode="TRANSFER" onClose={() => undefined} />);
    await user.type(screen.getByLabelText("Summa"), "300 000");
    const to = screen.getByRole("group", { name: "Qaysi hamyonga" });
    await user.click(within(to).getByRole("button", { name: "Karta" }));
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(kkRecordMove).toHaveBeenCalledWith("s-kk", { kind: "TRANSFER", wallet: "CARD", toWallet: "CARD", amount: "300 000", occurredOn: null, note: null });
    expect(await screen.findByRole("alert")).toHaveTextContent("Ikki xil hamyonni tanlang");
  });

  it("maosh: Uy'ga oʻtkaziladi, keyin Uy'dagi ulush yadrodagi `plain` bilan ajratiladi", async () => {
    kkPayOwnerSalary.mockResolvedValue(
      ok({
        overview,
        uySpaceId: "s-uy",
        uyIncome: {
          income: { id: "inc-9", amount: money("5 000 000 soʻm", "5 000 000"), source: "Kasb-kor", channel: "CARD", occurredOn: "2026-10-25" },
          suggestedShare: money("250 000 soʻm", "250 000"),
          progressiveSuggestionBp: null,
          progressiveSuggestionPercent: null,
        },
      }),
    );
    allocateToVault.mockResolvedValue(ok({}));
    const onClose = vi.fn();
    const user = userEvent.setup();
    const { container } = wrap(<KkSalaryDialog spaceId="s-kk" overview={overview} onClose={onClose} />);
    expect(screen.getByLabelText("Summa")).toHaveValue("5 000 000");
    await user.click(screen.getByRole("button", { name: "Oʻtkazish" }));
    expect(kkPayOwnerSalary).toHaveBeenCalledWith("s-kk", { amount: "5 000 000", wallet: "CARD", occurredOn: null, note: null });
    expect(await screen.findByText("Shundan 250 000 soʻm — kelajagingiz uchun")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Ajratish" }));
    expect(allocateToVault).toHaveBeenCalledWith("s-uy", "inc-9", "250 000");
    expect(onClose).toHaveBeenCalled();
  });

  it("maosh belgilash: notoʻgʻri summa — yadro xatosi", async () => {
    kkSetOwnerSalary.mockResolvedValue({ status: "error", error: { code: "AMOUNT_NEGATIVE", field: "amount" } });
    const user = userEvent.setup();
    wrap(<KkHomeScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Oʻzgartirish" }));
    const input = screen.getByLabelText("Oylik maosh");
    await user.clear(input);
    await user.type(input, "-5");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(kkSetOwnerSalary).toHaveBeenCalledWith("s-kk", "-5");
    expect(await screen.findByRole("alert")).toHaveTextContent("Summa manfiy boʻlmaydi");
  });
});
