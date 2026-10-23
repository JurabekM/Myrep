import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CeremoniesScreen } from "./CeremoniesScreen";

const ceremonies = vi.fn();
const ceremony = vi.fn();
const debtsOverview = vi.fn();
const agreeDiscussion = vi.fn();
const saveDiscussion = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    ceremonies: (...a: unknown[]) => ceremonies(...a),
    ceremony: (...a: unknown[]) => ceremony(...a),
    debtsOverview: (...a: unknown[]) => debtsOverview(...a),
    agreeDiscussion: (...a: unknown[]) => agreeDiscussion(...a),
    saveDiscussion: (...a: unknown[]) => saveDiscussion(...a),
  },
}));

const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const scenario = {
  id: "s1",
  name: "3 kunlik, 200 kishi",
  guests: 200,
  selected: true,
  lines: [{ id: "l1", title: "Xonanda va zal", kind: "ONE_OFF", amount: money("20 000 000 soʻm", "2000000000"), total: money("20 000 000 soʻm", "2000000000"), source: "DEBT" }],
  total: money("20 000 000 soʻm", "2000000000"),
  bySource: { savings: money("0 soʻm", "0"), family: money("0 soʻm", "0"), expectedGifts: money("0 soʻm", "0"), debt: money("20 000 000 soʻm", "2000000000") },
  hasDebt: true,
  payoffMonths: 9,
  payoffDate: "2028-01-01",
  notRepayable: false,
  savedVsMax: money("0 soʻm", "0"),
  goalEquivalents: [],
};
const detail = {
  id: "c1",
  kind: "TOY",
  title: "Sanjarning toʻyi",
  plannedOn: "2027-05-20",
  status: "DRAFT",
  monthlyCapacity: money("2 400 000 soʻm", "240000000"),
  capacitySource: "MANUAL",
  scenarios: [scenario],
  discussion: {
    required: true,
    answers: [{ key: "guests", note: "150 ga tushiramiz" }, { key: "days", note: "" }, { key: "cut", note: "" }, { key: "sources", note: "" }],
    adults: [{ memberId: "m1", name: "Karim", agreedOn: null }, { memberId: "m2", name: "Mohira", agreedOn: "2026-10-15" }],
    complete: false,
  },
  canConfirm: false,
  confirmBlocker: "DISCUSSION_REQUIRED",
  giftsWarning: false,
};

describe("CeremoniesScreen", () => {
  it("qarzli stsenariyda muhokamasiz tasdiqlash yopiq; katta aʼzo rozilik beradi", async () => {
    ceremonies.mockResolvedValue({ status: "ok", data: [{ id: "c1", kind: "TOY", title: "Sanjarning toʻyi", plannedOn: "2027-05-20", status: "DRAFT", total: money("20 000 000 soʻm", "2000000000"), hasDebt: true }] });
    ceremony.mockResolvedValue({ status: "ok", data: detail });
    debtsOverview.mockResolvedValue({ status: "ok", data: { goals: [] } });
    agreeDiscussion.mockResolvedValue({ status: "ok", data: detail });
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <CeremoniesScreen spaceId="uy" />
      </QueryClientProvider>,
    );
    await user.click(await screen.findByText("Sanjarning toʻyi"));
    expect(await screen.findByText("Qarzni uzish: 9 oy (01.2028 gacha)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rejani tasdiqlash" })).toBeDisabled();
    expect(screen.getByText("Qarzli stsenariyni tasdiqlashdan oldin oilaviy muhokama kerak.")).toBeInTheDocument();
    expect(screen.getByText("✓ rozi, 15.10.2026")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Karim: muhokamaga roziman" }));
    expect(agreeDiscussion).toHaveBeenCalledWith("uy", "c1", "m1");
  });
});
