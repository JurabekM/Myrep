import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CelebrationDialog } from "../../components/CelebrationDialog";
import { PayoffScreen } from "./PayoffScreen";

const budgetMode = vi.fn();
const setBudgetMode = vi.fn();
const payoffPlanner = vi.fn();
const sellableItems = vi.fn();
const depositToVault = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    budgetMode: (...a: unknown[]) => budgetMode(...a),
    setBudgetMode: (...a: unknown[]) => setBudgetMode(...a),
    payoffPlanner: (...a: unknown[]) => payoffPlanner(...a),
    sellableItems: (...a: unknown[]) => sellableItems(...a),
    depositToVault: (...a: unknown[]) => depositToVault(...a),
  },
}));

const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const mode = {
  mode: "STANDARD",
  householdBp: 7000,
  extraDebtBp: 2000,
  savingsBp: 1000,
  householdPercent: "70",
  extraDebtPercent: "20",
  savingsPercent: "10",
  suggested: true,
  hasActiveDebt: true,
  monthlyIncome: money("12 000 000 soʻm", "1200000000"),
  household: money("8 400 000 soʻm", "840000000"),
  extraDebt: money("2 400 000 soʻm", "240000000"),
  savings: money("1 200 000 soʻm", "120000000"),
  mandatoryDebtPayments: money("3 221 476,84 soʻm", "322147684"),
  householdAfterDebts: money("5 178 523,16 soʻm", "517852316"),
  householdShort: false,
  changedOn: null,
};
const totals = (date: string, months: number) => ({
  payoffDate: date,
  months,
  interest: money("0 soʻm", "0"),
  fees: money("168 000 soʻm", "16800000"),
  paid: money("0 soʻm", "0"),
});
const plan = {
  extraPerMonth: money("2 400 000 soʻm", "240000000"),
  extraSource: "NONE",
  base: totals("2027-12-05", 14),
  accelerated: totals("2027-06-05", 8),
  monthsSaved: 6,
  interestSaved: money("2 683 106,88 soʻm", "268310688"),
  netSaved: money("2 515 106,88 soʻm", "251510688"),
  debts: [
    {
      id: "d1",
      creditor: "Avtokredit",
      isRibo: true,
      order: 1,
      manualOrder: false,
      balance: money("39 000 000 soʻm", "3900000000"),
      basePayoff: "2027-12-05",
      acceleratedPayoff: "2027-06-05",
      monthsSaved: 6,
      interestSaved: money("2 683 106,88 soʻm", "268310688"),
      fees: money("168 000 soʻm", "16800000"),
      prepaymentFeeBp: 100,
    },
  ],
  timeline: [
    { month: "2026-11-01", baseBalance: money("36 558 523 soʻm", "3655852316"), acceleratedBalance: money("34 158 523 soʻm", "3415852316") },
    { month: "2026-12-01", baseBalance: money("34 068 216 soʻm", "3406821678"), acceleratedBalance: money("0 soʻm", "0") },
  ],
  schedule: [],
  excludedForeign: 0,
};

function wrap(ui: React.ReactNode) {
  render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

describe("PayoffScreen", () => {
  it("rejimni 70/20/10 bilan yoqadi va «Qarzsiz kun»ni yadrodan koʻrsatadi", async () => {
    budgetMode.mockResolvedValue({ status: "ok", data: mode });
    payoffPlanner.mockResolvedValue({ status: "ok", data: plan });
    sellableItems.mockResolvedValue({ status: "ok", data: [] });
    setBudgetMode.mockResolvedValue({ status: "ok", data: { ...mode, mode: "DEBT_RECOVERY", suggested: false } });
    const user = userEvent.setup();
    wrap(<PayoffScreen spaceId="uy" />);
    expect(await screen.findByText("05.06.2027")).toBeInTheDocument();
    expect(screen.getByText("6 oy erta")).toBeInTheDocument();
    expect(screen.getByText("2 515 106,88 soʻm")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Umumiy qarz qoldigʻi/ })).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Kelajagim, %"));
    await user.type(screen.getByLabelText("Kelajagim, %"), "0");
    await user.clear(screen.getByLabelText("Qoʻshimcha toʻlov, %"));
    await user.type(screen.getByLabelText("Qoʻshimcha toʻlov, %"), "30");
    await user.click(screen.getByRole("button", { name: "Yoqish" }));
    expect(setBudgetMode).toHaveBeenCalledWith("uy", { mode: "DEBT_RECOVERY", householdBp: 7000, extraDebtBp: 3000, savingsBp: 0 });
  });

  it("qarz yopilganda boʻshagan toʻlovni «Kelajagim»ga oʻtkazishni taklif qiladi", async () => {
    depositToVault.mockResolvedValue({ status: "ok", data: {} });
    const onClose = vi.fn();
    const user = userEvent.setup();
    wrap(
      <CelebrationDialog
        spaceId="uy"
        onClose={onClose}
        result={{
          repayment: { id: "r", amount: money("3 000 000 soʻm", "300000000"), date: "2026-11-20", isPrepayment: false, note: null, journalShortCode: null, contributorId: null },
          closed: true,
          debtFree: true,
          modeReturned: true,
          freedMonthly: { minor: "300000000", currency: "UZS", formatted: "3 000 000 soʻm", plain: "3000000" },
        }}
      />,
    );
    expect(screen.getByText("Qarzsiz kun keldi!")).toBeInTheDocument();
    expect(screen.getByText("«Qarzdan chiqish» rejimi oddiy rejimga qaytdi.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "«Kelajagim»ga oʻtkazish" }));
    expect(depositToVault).toHaveBeenCalledWith("uy", "3000000", "Boʻshagan qarz toʻlovi");
    expect(onClose).toHaveBeenCalled();
  });
});
