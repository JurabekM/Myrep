import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReceiptScreen } from "./ReceiptScreen";

const issueLoanReceipt = vi.fn();
const exportAgreementReceipt = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    issueLoanReceipt: (...a: unknown[]) => issueLoanReceipt(...a),
    exportAgreementReceipt: (...a: unknown[]) => exportAgreementReceipt(...a),
  },
}));

function renderScreen() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReceiptScreen spaceId="uy" />
    </QueryClientProvider>,
  );
}

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Qarz beruvchi"), "Ulugʻbek");
  await user.type(screen.getByLabelText("Qarz oluvchi"), "Karim");
  await user.type(screen.getByLabelText("Qarz summasi"), "2 000 000");
  await user.type(screen.getByLabelText("Joy (shahar, mahalla)"), "Toshkent");
  await user.type(screen.getByLabelText("Sana 1"), "15.11.2026");
  await user.type(screen.getByLabelText("Summa 1"), "1 000 000");
}

describe("ReceiptScreen", () => {
  beforeEach(() => {
    issueLoanReceipt.mockReset();
    exportAgreementReceipt.mockReset();
  });

  it("jadvalni oʻzgarishsiz yadroga yuboradi va yadro xatosini koʻrsatadi", async () => {
    issueLoanReceipt.mockResolvedValue({ status: "error", error: { code: "SCHEDULE_SUM_MISMATCH", field: "schedule" } });
    const user = userEvent.setup();
    renderScreen();
    await fill(user);
    await user.click(screen.getByLabelText("Hashamat"));
    await user.click(screen.getByRole("button", { name: "Tilxatni saqlash va PDF" }));

    expect(issueLoanReceipt).toHaveBeenCalledWith(
      "uy",
      expect.objectContaining({
        direction: "BORROWED",
        isNew: true,
        borrowCheck: { need: "LUXURY", alternatives: [] },
        receipt: expect.objectContaining({ amount: "2 000 000", schedule: [{ date: "15.11.2026", amount: "1 000 000" }], note: null }),
      }),
    );
    expect(exportAgreementReceipt).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent("Jadvaldagi summalar yigʻindisi qarz summasiga teng boʻlishi kerak");
  });

  it("bergan qarzda «toʻxta va oʻyla» soʻralmaydi; saqlangach tekshirish kodi koʻrinadi", async () => {
    issueLoanReceipt.mockResolvedValue({
      status: "ok",
      data: { agreementId: "a1", recordType: "RECEIVABLE", recordId: "r1", shortCode: "F8B2-EF8C-8E72-218F" },
    });
    exportAgreementReceipt.mockResolvedValue({ status: "ok", data: true });
    const user = userEvent.setup();
    renderScreen();
    await user.click(screen.getByLabelText("Men qarz berdim"));
    expect(screen.queryByText("Toʻxta va oʻyla")).toBeNull();
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Tilxatni saqlash va PDF" }));

    expect(issueLoanReceipt).toHaveBeenCalledWith("uy", expect.objectContaining({ direction: "LENT", isNew: false, borrowCheck: null, creditorType: null }));
    expect(exportAgreementReceipt).toHaveBeenCalledWith("uy", "a1");
    expect(await screen.findByText("F8B2-EF8C-8E72-218F")).toBeInTheDocument();
  });
});
