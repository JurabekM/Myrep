import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { IncomeDialog } from "./IncomeDialog";

const recordIncome = vi.fn();
const allocateToVault = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    recordIncome: (...a: unknown[]) => recordIncome(...a),
    allocateToVault: (...a: unknown[]) => allocateToVault(...a),
  },
}));

const money = (formatted: string, plain: string) => ({ minor: "0", currency: "UZS", formatted, plain });

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("IncomeDialog", () => {
  beforeEach(() => {
    recordIncome.mockReset();
    allocateToVault.mockReset();
  });

  it("taklif qilingan ulushni yadrodagi `plain` qiymat bilan oʻzgarishsiz yuboradi", async () => {
    recordIncome.mockResolvedValue({
      status: "ok",
      data: {
        income: { id: "inc-1", amount: money("800 000 soʻm", "800000"), source: "Taksi", channel: "CASH", occurredOn: "2026-10-15" },
        suggestedShare: money("40 000 soʻm", "40000"),
        progressiveSuggestionBp: null,
        progressiveSuggestionPercent: null,
      },
    });
    allocateToVault.mockResolvedValue({ status: "ok", data: {} });
    const onClose = vi.fn();
    const user = userEvent.setup();
    wrap(<IncomeDialog spaceId="s-uy" onClose={onClose} />);

    await user.type(screen.getByLabelText("Summa"), "800 000");
    await user.type(screen.getByLabelText("Manba"), "Taksi");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));

    expect(recordIncome).toHaveBeenCalledWith("s-uy", expect.objectContaining({ amount: "800 000", source: "Taksi", channel: "CASH" }));
    expect(await screen.findByText("Shundan 40 000 soʻm — kelajagingiz uchun")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ajratish" }));
    expect(allocateToVault).toHaveBeenCalledWith("s-uy", "inc-1", "40000");
    expect(onClose).toHaveBeenCalled();
  });

  it("yadro xatosini ayblamaydigan matn bilan koʻrsatadi", async () => {
    recordIncome.mockResolvedValue({ status: "error", error: { code: "AMOUNT_NOT_POSITIVE", field: "amount" } });
    const user = userEvent.setup();
    wrap(<IncomeDialog spaceId="s-uy" onClose={() => undefined} />);
    await user.type(screen.getByLabelText("Summa"), "0");
    await user.type(screen.getByLabelText("Manba"), "Taksi");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Summa noldan katta boʻlishi kerak");
  });
});
