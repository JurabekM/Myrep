import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReceiptScreen } from "./ReceiptScreen";

const exportLoanReceipt = vi.fn();
vi.mock("../../bindings", () => ({ commands: { exportLoanReceipt: (...a: unknown[]) => exportLoanReceipt(...a) } }));

describe("ReceiptScreen", () => {
  it("jadvalni oʻzgarishsiz yadroga yuboradi va yadro xatosini koʻrsatadi", async () => {
    exportLoanReceipt.mockResolvedValue({ status: "error", error: { code: "SCHEDULE_SUM_MISMATCH", field: "schedule" } });
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ReceiptScreen />
      </QueryClientProvider>,
    );
    await user.type(screen.getByLabelText("Qarz beruvchi"), "Gʻayrat");
    await user.type(screen.getByLabelText("Qarz oluvchi"), "Karim");
    await user.type(screen.getByLabelText("Qarz summasi"), "2 000 000");
    await user.type(screen.getByLabelText("Joy (shahar, mahalla)"), "Toshkent");
    await user.type(screen.getByLabelText("Sana 1"), "15.11.2026");
    await user.type(screen.getByLabelText("Summa 1"), "1 000 000");
    await user.click(screen.getByRole("button", { name: "PDF saqlash" }));

    expect(exportLoanReceipt).toHaveBeenCalledWith(
      expect.objectContaining({ amount: "2 000 000", schedule: [{ date: "15.11.2026", amount: "1 000 000" }], note: null }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Jadvaldagi summalar yigʻindisi qarz summasiga teng boʻlishi kerak");
  });
});
