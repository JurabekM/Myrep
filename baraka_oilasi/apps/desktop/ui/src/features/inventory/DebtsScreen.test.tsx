import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DebtsScreen } from "./DebtsScreen";

const debtsOverview = vi.fn();
const previewBorrowCheck = vi.fn();
const addDebt = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    debtsOverview: (...a: unknown[]) => debtsOverview(...a),
    previewBorrowCheck: (...a: unknown[]) => previewBorrowCheck(...a),
    addDebt: (...a: unknown[]) => addDebt(...a),
  },
}));

const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const empty = {
  debts: [],
  receivables: [],
  totalDebt: [],
  totalReceivable: [],
  monthlyDue: money("0 soʻm", "0"),
  monthlyIncome: null,
  loadPercent: null,
  loadHigh: false,
  loadExcludesForeign: false,
  hasRiboDebt: false,
  goals: [],
};

describe("DebtsScreen", () => {
  it("yangi qarzda avval «toʻxta va oʻyla», keyin saqlash", async () => {
    debtsOverview.mockResolvedValue({ status: "ok", data: empty });
    previewBorrowCheck.mockResolvedValue({
      status: "ok",
      data: {
        isRibo: true,
        projectedLoadPercent: "26,85",
        warnings: ["RIBO", "LUXURY"],
        plan: [],
        trueCost: {
          originalPrincipal: money("39 000 000 soʻm", "3900000000"),
          totalCost: money("45 100 675,73 soʻm", "4510067573"),
          overpay: money("6 100 675,73 soʻm", "610067573"),
          overpayPercent: "13,53",
          goalEquivalents: [],
        },
      },
    });
    addDebt.mockResolvedValue({ status: "ok", data: {} });
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DebtsScreen spaceId="uy" />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Daromad kiritilmagan")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Qarz qoʻshish" }));
    await user.selectOptions(screen.getByLabelText("Kimdan"), "BANK");
    await user.type(screen.getByLabelText("Kreditor (ism yoki bank)"), "Avtokredit");
    await user.type(screen.getByLabelText("Hozirgi qoldiq"), "39 000 000");
    await user.selectOptions(screen.getByLabelText("Toʻlov rejasi"), "ANNUITY");
    await user.click(screen.getByLabelText("Bu qarzni hozir olmoqchiman (yangi qarz)"));
    await user.click(screen.getByLabelText("Hashamat"));
    await user.click(screen.getByRole("button", { name: "Tekshirish" }));

    expect(previewBorrowCheck).toHaveBeenCalledWith(
      "uy",
      expect.objectContaining({ planKind: "ANNUITY", annualBp: 2400, months: 12, isNew: true, borrowCheck: { need: "LUXURY", alternatives: [] } }),
    );
    expect(addDebt).not.toHaveBeenCalled();
    expect(await screen.findByText("Bu qarz foizli (ribo). Foizsiz yoʻlini yana bir bor qidirib koʻring.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Oʻyladim, saqlash" }));
    expect(addDebt).toHaveBeenCalledTimes(1);
  });
});
