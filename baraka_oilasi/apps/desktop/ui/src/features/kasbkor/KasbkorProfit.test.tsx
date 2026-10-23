import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkEquipmentScreen } from "./KkEquipmentScreen";
import { KkHomeScreen } from "./KkHomeScreen";
import { KkLaborScreen } from "./KkLaborScreen";
import { KkQuoteScreen } from "./KkQuoteScreen";

const kkOverview = vi.fn();
const kkSetOwnerLabor = vi.fn();
const kkEquipment = vi.fn();
const kkAddEquipment = vi.fn();
const kkDisposeEquipment = vi.fn();
const kkDeleteEquipment = vi.fn();
const kkFamilyLabor = vi.fn();
const kkAddFamilyLabor = vi.fn();
const kkDeleteFamilyLabor = vi.fn();
const kkOrderQuote = vi.fn();
const categories = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkOverview: (...a: unknown[]) => kkOverview(...a),
    kkSetOwnerLabor: (...a: unknown[]) => kkSetOwnerLabor(...a),
    kkEquipment: (...a: unknown[]) => kkEquipment(...a),
    kkAddEquipment: (...a: unknown[]) => kkAddEquipment(...a),
    kkDisposeEquipment: (...a: unknown[]) => kkDisposeEquipment(...a),
    kkDeleteEquipment: (...a: unknown[]) => kkDeleteEquipment(...a),
    kkFamilyLabor: (...a: unknown[]) => kkFamilyLabor(...a),
    kkAddFamilyLabor: (...a: unknown[]) => kkAddFamilyLabor(...a),
    kkDeleteFamilyLabor: (...a: unknown[]) => kkDeleteFamilyLabor(...a),
    kkOrderQuote: (...a: unknown[]) => kkOrderQuote(...a),
    categories: (...a: unknown[]) => categories(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

// kasbkor/SPEC 3.1 Feruza: ko'rinadigan 9 500 000, haqiqiy 3 100 000.
const overview = {
  periodStart: "2026-11-01",
  periodEnd: "2026-11-30",
  ownerSalary: m("4 000 000 soʻm"),
  revenue: m("18 000 000 soʻm"),
  expenses: m("8 500 000 soʻm"),
  cashFlow: m("9 500 000 soʻm"),
  ownerDraws: zero,
  ownerSalaryTransferred: zero,
  contributions: zero,
  ownerPaid: zero,
  salaryRemaining: m("4 000 000 soʻm"),
  overdrawn: null,
  cash: zero,
  card: m("-2 500 000 soʻm"),
  equipmentPurchases: m("12 000 000 soʻm"),
  equipmentSales: zero,
  stockPurchases: zero,
  stockValue: zero,
  stockFrozenValue: zero,
  stockFrozenCount: 0,
  payables: zero,
  payablesOverdue: zero,
  wagesOwed: zero,
  zakatReminder: null,
  scaleCheckDue: false,
  profit: {
    revenue: m("18 000 000 soʻm"),
    cogs: zero,
    stockLosses: zero,
    operatingExpenses: m("8 500 000 soʻm"),
    visibleProfit: m("9 500 000 soʻm"),
    ownerLabor: m("5 000 000 soʻm"),
    familyLabor: m("1 200 000 soʻm"),
    familyLaborPaid: m("50 000 soʻm"),
    depreciation: m("200 000 soʻm"),
    disposal: zero,
    trueProfit: m("3 100 000 soʻm"),
  },
  negativeWallets: ["CARD"],
  salaryCarry: null,
  closedUntil: null,
  closeDue: null,
  cashClosedUntil: null,
  receivables: zero,
  receivablesOverdue: zero,
  entries: [],
};

const machine = {
  id: "eq-1",
  name: "Tikuv mashinalari",
  cost: m("12 000 000 soʻm"),
  salvage: zero,
  usefulMonths: 60,
  acquiredOn: "2026-11-05",
  wallet: "CARD",
  monthDepreciation: m("200 000 soʻm"),
  bookValue: m("11 800 000 soʻm"),
  monthsLeft: 59,
  status: "ACTIVE",
  disposedOn: null,
  disposalProceeds: null,
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: haqiqiy foyda (K2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkOverview.mockResolvedValue(ok(overview));
    categories.mockResolvedValue(ok([]));
    kkEquipment.mockResolvedValue(ok([machine]));
    kkFamilyLabor.mockResolvedValue(ok([]));
  });

  it("bosh sahifa: 1-raqam — haqiqiy foyda, tarkibi va o'z mehnati maosh bilan yonma-yon; axe toza", async () => {
    const { container } = wrap(<KkHomeScreen spaceId="s-kk" />);
    const card = await screen.findByRole("region", { name: "Foyda qanday hosil boʻldi" });
    expect(screen.getByTestId("kk-true-profit")).toHaveTextContent("3 100 000 soʻm");
    expect(within(card).getByRole("rowheader", { name: "Koʻrinadigan foyda" }).nextSibling).toHaveTextContent("9 500 000 soʻm");
    expect(within(card).getByRole("rowheader", { name: /Oilaviy mehnat/ }).nextSibling).toHaveTextContent("− 1 200 000 soʻm");
    expect(within(card).getByText("Toʻlangan 50 000 soʻm chiqimda bor — qayta ayirilmaydi")).toBeInTheDocument();
    expect(within(card).getByText("Oʻz mehnatingiz bahosi: 5 000 000 soʻm · Oʻzingizga belgilagan maosh: 4 000 000 soʻm")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("o'z mehnati kiritilmagan — ogohlantirish; kiritilgan summa matn holida yadroga", async () => {
    kkOverview.mockResolvedValue(ok({ ...overview, profit: { ...overview.profit, ownerLabor: null } }));
    kkSetOwnerLabor.mockResolvedValue(ok(overview));
    const user = userEvent.setup();
    wrap(<KkHomeScreen spaceId="s-kk" />);
    expect(await screen.findByText(/«foyda» aslida maoshingiz/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bahoni kiritish" }));
    await user.type(screen.getByLabelText("Oʻz mehnatingiz bahosi (oyiga)"), "5 000 000");
    await user.click(within(screen.getByRole("region", { name: "Foyda qanday hosil boʻldi" })).getByRole("button", { name: "Saqlash" }));
    expect(kkSetOwnerLabor).toHaveBeenCalledWith("s-kk", "5 000 000");
  });

  it("uskuna: qo'shish (ilovagacha bor edi — hamyonsiz) va sotish; axe toza", async () => {
    kkAddEquipment.mockResolvedValue(ok([machine]));
    kkDisposeEquipment.mockResolvedValue(ok([machine]));
    const user = userEvent.setup();
    const { container } = wrap(<KkEquipmentScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-eq-dep-Tikuv mashinalari")).toHaveTextContent("200 000 soʻm");
    expect(screen.getByText("Yana 59 oy")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);

    const form = screen.getByRole("form", { name: "Uskuna qoʻshish" });
    await user.type(within(form).getByLabelText("Nomi"), "Overlok");
    await user.type(within(form).getByLabelText("Narxi"), "3 600 000");
    await user.clear(within(form).getByLabelText("Foydali muddat (oy)"));
    await user.type(within(form).getByLabelText("Foydali muddat (oy)"), "36");
    await user.click(within(form).getByRole("button", { name: "Ilovagacha bor edi" }));
    await user.click(within(form).getByRole("button", { name: "Qoʻshish" }));
    expect(kkAddEquipment).toHaveBeenCalledWith("s-kk", { name: "Overlok", cost: "3 600 000", salvage: null, usefulMonths: 36, acquiredOn: null, wallet: null });

    await user.click(screen.getByRole("button", { name: "Sotildi / yaroqsiz" }));
    const dispose = screen.getByRole("form", { name: "Tikuv mashinalari: sotildi yoki yaroqsiz" });
    expect(within(dispose).getByText(/Hozirgi balans qiymati 11 800 000 soʻm/)).toBeInTheDocument();
    await user.type(within(dispose).getByLabelText("Sotilgan narx"), "4 000 000");
    await user.click(within(dispose).getByRole("button", { name: "Karta" }));
    await user.click(within(dispose).getByRole("button", { name: "Tasdiqlash" }));
    expect(kkDisposeEquipment).toHaveBeenCalledWith("s-kk", "eq-1", { proceeds: "4 000 000", wallet: "CARD", disposedOn: null });
  });

  it("oilaviy mehnat: kasr soat matn holida, to'langan belgisi; yadro xatosi ko'rsatiladi", async () => {
    kkAddFamilyLabor.mockResolvedValueOnce({ status: "error", error: { code: "INVALID_HOURS", field: "hours" } }).mockResolvedValueOnce(ok([]));
    const user = userEvent.setup();
    const { container } = wrap(<KkLaborScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-family-labor")).toHaveTextContent("1 200 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Kim"), "Madina");
    await user.type(screen.getByLabelText("Soat"), "2,555");
    await user.type(screen.getByLabelText("Soat bahosi"), "15 000");
    await user.click(screen.getByRole("button", { name: "Yozish" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Soatni toʻgʻri kiriting");
    await user.clear(screen.getByLabelText("Soat"));
    await user.type(screen.getByLabelText("Soat"), "2,5");
    await user.click(screen.getByLabelText("Pul toʻlangan (chiqim sifatida yozilgan)"));
    await user.click(screen.getByRole("button", { name: "Yozish" }));
    expect(kkAddFamilyLabor).toHaveBeenLastCalledWith("s-kk", { person: "Madina", hours: "2,5", hourlyRate: "15 000", paid: true, workedOn: null, note: null });
  });

  it("buyurtma narxi: tannarxdan past — ogohlantirish va avans yetmasligi; axe toza", async () => {
    kkOrderQuote.mockResolvedValue(
      ok({
        labor: m("240 000 soʻm"),
        subtotal: m("760 000 soʻm"),
        reserve: m("38 000 soʻm"),
        cost: m("798 000 soʻm"),
        margin: m("-98 000 soʻm"),
        laborPaid: m("142 000 soʻm"),
        belowCost: true,
        effectiveHourlyRate: m("23 666,67 soʻm"),
        materialShortfall: m("150 000 soʻm"),
        advanceAfterMaterial: zero,
      }),
    );
    const user = userEvent.setup();
    const { container } = wrap(<KkQuoteScreen spaceId="s-kk" />);
    await user.type(screen.getByLabelText("Material"), "450 000");
    await user.type(screen.getByLabelText("Mehnat (soat)"), "6");
    await user.type(screen.getByLabelText("Zaxira (%)"), "5");
    await user.type(screen.getByLabelText("Mijozga aytiladigan narx"), "700 000");
    await user.click(screen.getByRole("button", { name: "Hisoblash" }));
    expect(kkOrderQuote).toHaveBeenCalledWith("s-kk", {
      material: "450 000",
      hours: "6",
      hourlyRate: null,
      travel: null,
      depreciation: null,
      reservePercent: "5",
      price: "700 000",
      advance: null,
    });
    expect(await screen.findByTestId("kk-quote-cost")).toHaveTextContent("798 000 soʻm");
    expect(screen.getByRole("alert")).toHaveTextContent("Narx tannarxdan past (marja -98 000 soʻm). Bu buyurtmada oʻz mehnatingizga 142 000 soʻm toʻlab ishlaysiz — soatiga 23 666,67 soʻm.");
    expect(screen.getByTestId("kk-quote-advance")).toHaveTextContent("Avans materialga yetmaydi: yana 150 000 soʻm kerak.");
    expect(await axeViolations(container)).toEqual([]);
  });
});
