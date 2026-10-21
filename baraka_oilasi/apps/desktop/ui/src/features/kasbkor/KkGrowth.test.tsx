import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkGateScreen } from "./KkGateScreen";
import { KkMeasureScreen } from "./KkMeasureScreen";
import { KkZakatScreen } from "./KkZakatScreen";

const kkGate = vi.fn();
const kkUseFund = vi.fn();
const kkGrowthSettings = vi.fn();
const kkZakatDraft = vi.fn();
const kkSaveZakat = vi.fn();
const kkZakatHistory = vi.fn();
const kkScale = vi.fn();
const kkScaleCheck = vi.fn();
const kkStock = vi.fn();
const kkInventory = vi.fn();
const kkStockCounts = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkGate: (...a: unknown[]) => kkGate(...a),
    kkUseFund: (...a: unknown[]) => kkUseFund(...a),
    kkGrowthSettings: (...a: unknown[]) => kkGrowthSettings(...a),
    kkSetGrowthSettings: vi.fn(),
    kkZakatDraft: (...a: unknown[]) => kkZakatDraft(...a),
    kkSaveZakat: (...a: unknown[]) => kkSaveZakat(...a),
    kkZakatHistory: (...a: unknown[]) => kkZakatHistory(...a),
    kkScale: (...a: unknown[]) => kkScale(...a),
    kkScaleCheck: (...a: unknown[]) => kkScaleCheck(...a),
    kkStock: (...a: unknown[]) => kkStock(...a),
    kkInventory: (...a: unknown[]) => kkInventory(...a),
    kkStockCounts: (...a: unknown[]) => kkStockCounts(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

const fund = (f: string, balance: string) => ({ fund: f, added: m(balance), used: zero, balance: m(balance) });
const gate = {
  open: false,
  conditions: [
    { code: "RESERVE", ok: false },
    { code: "PROFIT", ok: false },
    { code: "RECEIVABLES", ok: true },
    { code: "INTEREST_DEBT", ok: true },
    { code: "PLAN", ok: true },
  ],
  reasons: ["RESERVE", "PROFIT"],
  reserve: m("1 780 000 soʻm"),
  averageOpex: m("2 000 000 soʻm"),
  requiredReserve: m("6 000 000 soʻm"),
  coverageMonths: "0,89",
  requiredMonths: 3,
  trueProfits: [m("8 000 000 soʻm")],
  receivables: zero,
  receivables90: zero,
  badDebtPercent: "0",
  maxBadPercent: "10",
  hasInterestDebt: false,
  hasPayoffPlan: false,
  plans: 1,
  funds: [fund("TAX", "0 soʻm"), fund("RESERVE", "1 780 000 soʻm"), fund("WORKING", "3 800 000 soʻm"), fund("EXPANSION", "1 520 000 soʻm"), fund("SADAQA", "0 soʻm")],
};
const settings = {
  reserveMonths: 3,
  maxBadPercent: "10",
  zakatMonth: 6,
  zakatDay: 20,
  nextZakatDay: "2026-12-01",
  goldPrice: m("1 100 000 soʻm"),
  nisabGrams: 85,
  stockValuation: "REPLACEMENT",
  scaleReminder: true,
  todayHijri: "1448-06-09",
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: kengayish darvozasi (K7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkGate.mockResolvedValue(ok(gate));
    kkGrowthSettings.mockResolvedValue(ok(settings));
  });

  it("shartlar, raqamlar va keyingi qadam; konvertlar; axe toza", async () => {
    const { container } = wrap(<KkGateScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-gate-status")).toHaveTextContent("Darvoza yopiq: 2");
    const reserve = screen.getByTestId("kk-gate-RESERVE");
    expect(reserve).toHaveTextContent("kerak 6 000 000 soʻm");
    expect(reserve).toHaveTextContent("0,89 oylik");
    expect(reserve).toHaveTextContent("Keyingi qadam");
    expect(within(screen.getByTestId("kk-gate-PLAN")).queryByText(/Keyingi qadam/)).toBeNull();
    expect(screen.getByTestId("kk-fund-RESERVE")).toHaveTextContent("1 780 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("konvertdan foydalanish: yadro qoldiqni tekshiradi", async () => {
    kkUseFund.mockResolvedValue({ status: "error", error: { code: "FUND_INSUFFICIENT", field: "amount" } });
    const user = userEvent.setup();
    wrap(<KkGateScreen spaceId="s-kk" />);
    const form = await screen.findByRole("form", { name: "Konvertdan foydalanish" });
    expect(within(form).queryByRole("option", { name: "Soliq zaxirasi" })).toBeNull();
    await user.selectOptions(within(form).getByLabelText("Konvert"), "WORKING");
    await user.type(within(form).getByLabelText("Summa"), "5 000 000");
    await user.type(within(form).getByLabelText("Nimaga"), "Mato");
    await user.click(within(form).getByRole("button", { name: "Yozib qoʻyish" }));
    expect(kkUseFund).toHaveBeenCalledWith("s-kk", { fund: "WORKING", amount: "5 000 000", usedOn: null, note: "Mato" });
    expect(await within(form).findByRole("alert")).toHaveTextContent("Konvertda buncha pul yoʻq");
  });
});

// kasbkor/SPEC 8.3 (shartli misol): baza 100 mln, nisob 93,5 mln → 2 500 000.
const zakat = {
  calculatedOn: "2026-11-20",
  hijriDate: "1448-06-09",
  valuation: "REPLACEMENT",
  stock: m("90 000 000 soʻm"),
  cash: m("12 000 000 soʻm"),
  receivables: m("8 000 000 soʻm"),
  payables: m("10 000 000 soʻm"),
  wagesDue: zero,
  debts: m("10 000 000 soʻm"),
  goldPrice: m("1 100 000 soʻm"),
  nisabGrams: 85,
  nisab: m("93 500 000 soʻm"),
  base: m("100 000 000 soʻm"),
  zakat: m("2 500 000 soʻm"),
  due: true,
  reason: null,
  hawlComplete: true,
  hawlSuggested: false,
  hawlSince: "2026-11-20",
  receivableLines: [{ saleId: "c1", customer: "Malika", item: "Koʻylak", outstanding: m("660 000 soʻm"), overdueDays: 120, d90Plus: true, hopeless: false }],
  religiousNote: null,
  religiousReview: "PENDING",
};

describe("Kasb-kor: zakot hisobi (K7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkGrowthSettings.mockResolvedValue(ok(settings));
    kkZakatDraft.mockResolvedValue(ok(zakat));
    kkZakatHistory.mockResolvedValue(ok([]));
  });

  it("hisob, fatvo emas: diniy izoh tasdiqlanmagan — ko'rinmaydi; hijriy sana; axe toza", async () => {
    const { container } = wrap(<KkZakatScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-zakat-amount")).toHaveTextContent("2 500 000 soʻm");
    expect(screen.getByTestId("kk-zakat-base")).toHaveTextContent("100 000 000 soʻm");
    expect(screen.getAllByRole("note")[0]).toHaveTextContent("Hisob, fatvo emas");
    expect(screen.queryByText(/qamariy yil oʻtganda, 2,5 foiz/)).toBeNull();
    expect(screen.getByText("Bugun: 9 jumodul oxir 1448")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("umidsiz nasiya va hawl yadroga yuboriladi", async () => {
    kkSaveZakat.mockResolvedValue(ok([]));
    const user = userEvent.setup();
    wrap(<KkZakatScreen spaceId="s-kk" />);
    await user.click(await screen.findByLabelText(/Malika — Koʻylak/));
    expect(kkZakatDraft).toHaveBeenLastCalledWith("s-kk", { goldPrice: null, nisabGrams: null, valuation: null, hopelessSaleIds: ["c1"], hawlComplete: null });
    await user.click(screen.getByRole("button", { name: "Hisobni saqlash" }));
    expect(kkSaveZakat).toHaveBeenCalledWith("s-kk", expect.objectContaining({ hopelessSaleIds: ["c1"] }));
  });
});

describe("Kasb-kor: tarozi va sanoq (K7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkGrowthSettings.mockResolvedValue(ok(settings));
    kkScale.mockResolvedValue(ok({ checks: [], reminder: true, due: true }));
    kkStock.mockResolvedValue(
      ok({
        items: [
          { id: "i1", name: "Shakar", unit: "G", qty: "10" },
          { id: "i2", name: "Tuz", unit: "G", qty: "10" },
        ],
        value: zero,
        replacementValue: zero,
        inflationGap: zero,
        frozenValue: zero,
        frozenCount: 0,
      }),
    );
    kkStockCounts.mockResolvedValue(ok([]));
  });

  it("tarozi: eslatma, natija va izoh; inventarizatsiya bitta yozuvda; axe toza", async () => {
    kkScaleCheck.mockResolvedValue({ status: "error", error: { code: "REQUIRED", field: "note" } });
    kkInventory.mockResolvedValue(ok({}));
    const user = userEvent.setup();
    const { container } = wrap(<KkMeasureScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-scale-due")).toHaveTextContent("30 kundan koʻp");
    const check = screen.getByRole("form", { name: "Tekshiruv natijasi" });
    await user.click(within(check).getByRole("button", { name: "Sozlandi" }));
    await user.click(within(check).getByRole("button", { name: "Tekshirildi" }));
    expect(kkScaleCheck).toHaveBeenCalledWith("s-kk", { result: "ADJUSTED", checkedOn: null, note: null });
    expect(await within(check).findByRole("alert")).toBeInTheDocument();

    const inv = screen.getByRole("form", { name: "Sanalgan miqdorlar" });
    await user.type(within(inv).getByLabelText("Shakar: sanalgan (kg)"), "9,5");
    await user.type(within(inv).getByLabelText("Izoh (farqlar uchun)"), "Yillik sanoq");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(inv).getByRole("button", { name: "Inventarizatsiyani yozish" }));
    expect(kkInventory).toHaveBeenCalledWith("s-kk", {
      countedOn: null,
      reason: "Yillik sanoq",
      lines: [
        { itemId: "i1", counted: "9,5" },
        { itemId: "i2", counted: "" },
      ],
    });
  });
});
