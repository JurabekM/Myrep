import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PartnershipsScreen } from "./PartnershipsScreen";

const partnerships = vi.fn();
const partnership = vi.fn();
const createPartnership = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    partnerships: (...a: unknown[]) => partnerships(...a),
    partnership: (...a: unknown[]) => partnership(...a),
    createPartnership: (...a: unknown[]) => createPartnership(...a),
  },
}));

const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const answered = <T,>(value: T) => ({ status: "ANSWERED" as const, value });
const detail = {
  id: "p1",
  agreementId: "a1",
  kind: "MUDARABA",
  title: "Tikuvchilik ustaxonasi",
  status: "SIGNED",
  currency: "UZS",
  parties: [
    { id: "P1", fullName: "Laziz Tursunov", role: "CAPITAL_PROVIDER", profitShareBp: 5000, profitShare: "50%", isMe: true, capitalItems: [{ kind: "MONEY", description: "naqd", amount: money("30 000 000 soʻm", "3000000000") }], capital: money("30 000 000 soʻm", "3000000000"), lossShare: "100%" },
    { id: "P2", fullName: "Feruza Karimova", role: "WORKER", profitShareBp: 5000, profitShare: "50%", isMe: false, capitalItems: [], capital: money("0 soʻm", "0"), lossShare: "0%" },
  ],
  capitalTotal: money("30 000 000 soʻm", "3000000000"),
  duties: answered([{ id: "d1", title: "Tikish", ownerPartyId: "P2", breachClause: "xabar beradi" }]),
  negligenceClause: null,
  custody: answered({ location: "Karta", keeperPartyId: "P2", reviewEveryDays: 30, keeperDeviceId: null }),
  exitClause: answered({ noticeDays: 30, valuationMethod: "Bozor narxi", payoutTerms: "3 oy", assetSplit: null }),
  arbiter: answered({ fullName: "Hamid aka", role: null, partyId: null }),
  term: answered({ effectiveFrom: "2026-11-01", durationMonths: 12, reviewDate: "2027-11-01" }),
  witnesses: ["Dilnoza opa"],
  buyout: null,
  check: { answered: 9, complete: true, canSign: true, missing: [], errors: [], warnings: [] },
  version: 1,
  signedVersion: 1,
  amendmentPending: false,
  signers: [{ key: "party:P1", role: "PARTY", name: "Laziz Tursunov", signedAt: "15.10.2026", svg: null }],
  allSigned: true,
  meProvidesCapital: true,
  meReceivesCapital: false,
  gate: {
    open: false,
    reasons: ["EMERGENCY_FUND_BELOW_TARGET"],
    coverageMonths: "4",
    requiredMonths: 6,
    balance: money("20 000 000 soʻm", "2000000000"),
    monthlyEssentials: money("5 000 000 soʻm", "500000000"),
    hasInterestDebt: false,
    hasPayoffPlan: false,
  },
  consent: null,
  canActivate: false,
  activateBlocker: "GATE_CLOSED",
  history: [{ no: 1, createdOn: "15.10.2026", signed: 4, required: 4, inForce: true }],
  templateReview: "PENDING",
  hashCode: "F8B2-EF8C-8E72-218F",
};

function mount() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <PartnershipsScreen spaceId="uy" />
    </QueryClientProvider>,
  );
}

describe("PartnershipsScreen", () => {
  it("kafolatli daromadni UI ham bloklaydi: tushuntirish chiqadi, saqlash yopiq", async () => {
    partnerships.mockResolvedValue({ status: "ok", data: [] });
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Yangi sheriklik" }));
    await user.click(screen.getByRole("button", { name: /Foyda$/ }));
    await user.click(screen.getByRole("radio", { name: "Kapital egasiga har oy qatʼiy summa" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Bu sheriklik emas — ribo yoki qarz");
    expect(screen.getByRole("button", { name: "Saqlash" })).toBeDisabled();
    expect(createPartnership).not.toHaveBeenCalled();
  });

  it("kapital kirituvchiga darvoza koʻrsatiladi va boshlash yopiq", async () => {
    partnerships.mockResolvedValue({
      status: "ok",
      data: [{ id: "p1", kind: "MUDARABA", title: "Tikuvchilik ustaxonasi", status: "SIGNED", capitalTotal: money("30 000 000 soʻm", "3000000000"), myRole: "CAPITAL_PROVIDER", signedVersion: 1, answered: 9 }],
    });
    partnership.mockResolvedValue({ status: "ok", data: detail });
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByText("Tikuvchilik ustaxonasi"));
    await user.click(await screen.findByRole("button", { name: "Boshlash" }));
    expect(screen.getByText("Tayyorgarlik darvozasi hali yopiq")).toBeInTheDocument();
    expect(screen.getByText("• Zaxira pul 6 oylik zarur xarajatga yetmagan.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sheriklikni boshlash" })).toBeDisabled();
    expect(screen.queryByText("Bu qarz emas")).not.toBeInTheDocument();
  });
});
