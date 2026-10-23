import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { IdeasScreen } from "./IdeasScreen";
import { LedgerView } from "./LedgerView";
import { OfferCheckDialog } from "./OfferCheckDialog";

const ventureLedger = vi.fn();
const venturePeriodPreview = vi.fn();
const closeVenturePeriod = vi.fn();
const checkOffer = vi.fn();
const ventureIdeas = vi.fn();
const skills = vi.fn();
const household = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    ventureLedger: (...a: unknown[]) => ventureLedger(...a),
    venturePeriodPreview: (...a: unknown[]) => venturePeriodPreview(...a),
    closeVenturePeriod: (...a: unknown[]) => closeVenturePeriod(...a),
    checkOffer: (...a: unknown[]) => checkOffer(...a),
    ventureIdeas: (...a: unknown[]) => ventureIdeas(...a),
    skills: (...a: unknown[]) => skills(...a),
    household: (...a: unknown[]) => household(...a),
  },
}));

const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const zero = money("0 soʻm", "0");
const party = (id: string, name: string, role: string, isMe: boolean, share: string, payout: string, capital: string) => ({
  partyId: id,
  name,
  role,
  isMe,
  share: money(share, "1"),
  recovered: zero,
  liability: zero,
  payout: money(payout, "1"),
  carriedAfter: zero,
  capitalAfter: money(capital, "1"),
});
const ledger = (writable: boolean) => ({
  partnershipId: "p1",
  title: "Tikuvchilik ustaxonasi",
  kind: "MUDARABA",
  status: "ACTIVE",
  currency: "UZS",
  writable,
  readOnlyReason: writable ? null : "NOT_KEEPER",
  keeperName: "Nilufar Karimova",
  startOn: "2026-11-01",
  open: { no: 1, from: "2026-11-01", entries: 2, income: money("15 000 000 soʻm", "1500000000"), expense: money("7 000 000 soʻm", "700000000"), forceMajeure: zero, corrections: zero, result: money("8 000 000 soʻm", "800000000") },
  entries: [
    { id: "e1", kind: "INCOME", category: "ORDER", amount: money("15 000 000 soʻm", "1500000000"), effect: money("15 000 000 soʻm", "1500000000"), occurredOn: "2026-11-05", note: "Toʻy koʻylaklari", correctsEntryId: null, corrected: false, periodNo: null, attachments: [], hashCode: "AB12-CD34-EF56-7890" },
  ],
  periods: [],
  balances: [
    { partyId: "P1", name: "Sobir Qodirov", role: "CAPITAL_PROVIDER", isMe: false, capital: money("30 000 000 soʻm", "3000000000"), carriedLoss: zero },
    { partyId: "P2", name: "Nilufar Karimova", role: "WORKER", isMe: true, capital: zero, carriedLoss: zero },
  ],
  buyout: null,
  chainCode: "AB12-CD34-EF56-7890",
  chainOk: true,
  lossPolicy: "CAPITAL_FIRST",
  inDispute: false,
});

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

describe("LedgerView", () => {
  it("hisob yurituvchi emas — faqat o'qish, yozish formasi yo'q", async () => {
    ventureLedger.mockResolvedValue({ status: "ok", data: ledger(false) });
    wrap(<LedgerView spaceId="uy" partnershipId="p1" />);
    expect(await screen.findByText(/Hisobni Nilufar Karimova yuritadi/)).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Daftarga yozish" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tuzatish" })).not.toBeInTheDocument();
  });

  it("taqsimot yadrodan keladi; yopish oldindan ko'rishdan keyin chiqadi", async () => {
    ventureLedger.mockResolvedValue({ status: "ok", data: ledger(true) });
    venturePeriodPreview.mockResolvedValue({
      status: "ok",
      data: {
        id: null,
        no: 1,
        startOn: "2026-11-01",
        endOn: "2026-11-30",
        closedAt: null,
        entries: 2,
        income: zero,
        expense: zero,
        forceMajeure: zero,
        corrections: zero,
        result: money("8 000 000 soʻm", "800000000"),
        recovered: zero,
        distributable: money("8 000 000 soʻm", "800000000"),
        parties: [party("P1", "Sobir Qodirov", "CAPITAL_PROVIDER", false, "4 000 000 soʻm", "7 000 000 soʻm", "27 000 000 soʻm"), party("P2", "Nilufar Karimova", "WORKER", true, "4 000 000 soʻm", "1 000 000 soʻm", "3 000 000 soʻm")],
        buyout: { paid: [1], unpaid: [], amount: money("3 000 000 soʻm", "300000000"), capital: money("3 000 000 soʻm", "300000000") },
        lossPolicy: "CAPITAL_FIRST",
        negligentParty: null,
        negligenceNote: null,
        myIncome: money("1 000 000 soʻm", "100000000"),
        chainCode: null,
        profitSpike: false,
        spikeRereads: [],
      },
    });
    const user = userEvent.setup();
    wrap(<LedgerView spaceId="uy" partnershipId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Taqsimotni koʻrish" }));
    expect(screen.queryByRole("button", { name: "Davrni yopish" })).toBeInTheDocument();
    expect(screen.getByText("Oila byudjetiga daromad boʻlib tushadi: 1 000 000 soʻm")).toBeInTheDocument();
    expect(screen.getByText("Buyout: 1-bosqich toʻlandi, 3 000 000 soʻm xaridor ulushidan sotuvchiga oʻtdi.")).toBeInTheDocument();
    expect(venturePeriodPreview).toHaveBeenCalledWith("uy", "p1", expect.objectContaining({ channel: "CASH", negligence: null }));
  });
});

describe("OfferCheckDialog", () => {
  it("9 savolga javobsiz tekshirib bo'lmaydi; qizil natija bayroqlari va besh belgi bilan", async () => {
    checkOffer.mockResolvedValue({
      status: "ok",
      data: {
        verdict: "RED",
        flags: [
          { code: "GUARANTEED_PROFIT", level: "RED" },
          { code: "URGENCY", level: "YELLOW" },
          { code: "TWO_SIGNS", level: "RED" },
        ],
        signs: 2,
      },
    });
    const user = userEvent.setup();
    wrap(<OfferCheckDialog onClose={() => {}} />);
    const btn = screen.getByRole("button", { name: "Tekshirish" });
    expect(btn).toBeDisabled();
    const groups = screen.getAllByRole("radiogroup");
    const pick = ["Ha", "Ha", "Ha", "Yoʻq", "Ha", "Yoʻq", "Ha", "Ha", "Ha"];
    for (const [i, g] of groups.entries()) {
      const radio = Array.from(g.querySelectorAll("label")).find((l) => l.textContent === pick[i])?.querySelector("input");
      if (radio) await user.click(radio);
    }
    expect(btn).toBeEnabled();
    await user.click(btn);
    expect(await screen.findByText("Qizil: pul bermang")).toBeInTheDocument();
    expect(screen.getByText(/Kafolatlangan foyda vaʼda qilinmoqda/)).toBeInTheDocument();
    expect(screen.getByText("Besh xavf belgisidan topildi: 2")).toBeInTheDocument();
    expect(screen.getByText(/ikkitasi — bu taklifdan voz kechishga yetarli sabab/)).toBeInTheDocument();
    expect(checkOffer).toHaveBeenCalledWith({
      guaranteed: "YES",
      lossShared: "YES",
      realActivity: "YES",
      recruitment: "NO",
      urgency: "YES",
      written: "NO",
      licensed: "YES",
      inspection: "YES",
      exitEasy: "YES",
    });
  });
});

describe("IdeasScreen", () => {
  it("payback va ulushlar yadrodan; qoplanmasa — «qoplanmaydi»", async () => {
    skills.mockResolvedValue({ status: "ok", data: [] });
    household.mockResolvedValue({ status: "ok", data: { members: [] } });
    const sc = (name: string, net: string, pay: number | null) => ({
      name,
      income: zero,
      expense: zero,
      net: money(net, net.startsWith("-") ? "-1" : "1"),
      annualNet: zero,
      paybackMonths: pay,
      workerMonthly: zero,
      investorMonthly: zero,
      investorPaybackMonths: pay == null ? null : pay * 2,
    });
    ventureIdeas.mockResolvedValue({
      status: "ok",
      data: [
        {
          id: "i1",
          title: "Uyda tikuv",
          skillId: null,
          skillTitle: null,
          capexLines: [],
          capex: money("8 000 000 soʻm", "800000000"),
          scenarios: [sc("PESSIMISTIC", "-500 000 soʻm", null), sc("BASE", "2 500 000 soʻm", 4), sc("OPTIMISTIC", "4 000 000 soʻm", 2)],
          workerShareBp: 5000,
          warnings: [],
          partnershipId: null,
        },
      ],
    });
    wrap(<IdeasScreen spaceId="uy" />);
    expect(await screen.findByText("Uyda tikuv")).toBeInTheDocument();
    expect(screen.getAllByText("4 oyda")).toHaveLength(2);
    expect(screen.getByText("8 oyda")).toBeInTheDocument();
    expect(screen.getAllByText("qoplanmaydi")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Sheriklik shartnomasiga oʻtish" })).toBeInTheDocument();
  });
});
