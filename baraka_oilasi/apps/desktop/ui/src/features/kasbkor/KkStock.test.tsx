import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkHomeScreen } from "./KkHomeScreen";
import { KkStockScreen } from "./KkStockScreen";

const kkStock = vi.fn();
const kkAddItem = vi.fn();
const kkUpdateItem = vi.fn();
const kkStockMove = vi.fn();
const kkOverview = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkStock: (...a: unknown[]) => kkStock(...a),
    kkAddItem: (...a: unknown[]) => kkAddItem(...a),
    kkUpdateItem: (...a: unknown[]) => kkUpdateItem(...a),
    kkStockMove: (...a: unknown[]) => kkStockMove(...a),
    kkDeleteItem: vi.fn(),
    kkOverview: (...a: unknown[]) => kkOverview(...a),
    categories: () => Promise.resolve({ status: "ok", data: [] }),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

// kasbkor/SPEC 4.2–4.3 Bahodir aka: 70 kg shakar hisobda 840 000, joriy narx 13 500 → 945 000, farq 105 000.
const sugar = {
  id: "i1",
  name: "Shakar",
  unit: "G",
  method: "AVERAGE",
  qty: "70",
  value: m("840 000 soʻm"),
  unitCost: m("12 000 soʻm"),
  salePrice: m("13 000 soʻm"),
  replacementPriceInput: m("13 500 soʻm"),
  replacementPrice: m("13 500 soʻm"),
  replacementValue: m("945 000 soʻm"),
  inflationGap: m("105 000 soʻm"),
  saleBelowReplacement: true,
  minQty: null,
  belowMin: false,
  frozenDays: 90,
  lastSaleOn: "2026-11-03",
  frozen: false,
  note: null,
  moves: [
    { id: "mv3", kind: "SALE", occurredOn: "2026-11-03", qty: "-80", amount: m("1 120 000 soʻm"), cost: m("960 000 soʻm"), wallet: "CASH", reason: null },
    { id: "mv2", kind: "PURCHASE", occurredOn: "2026-11-02", qty: "100", amount: m("1 250 000 soʻm"), cost: m("1 250 000 soʻm"), wallet: "CARD", reason: null },
  ],
};
const salt = {
  ...sugar,
  id: "i2",
  name: "Tuz",
  qty: "10",
  value: m("30 000 soʻm"),
  unitCost: m("3 000 soʻm"),
  salePrice: null,
  replacementPriceInput: null,
  replacementPrice: m("3 000 soʻm"),
  replacementValue: m("30 000 soʻm"),
  inflationGap: zero,
  saleBelowReplacement: false,
  minQty: "20",
  belowMin: true,
  lastSaleOn: null,
  frozen: true,
  moves: [],
};
const stock = {
  items: [sugar, salt],
  value: m("870 000 soʻm"),
  replacementValue: m("975 000 soʻm"),
  inflationGap: m("105 000 soʻm"),
  frozenValue: m("30 000 soʻm"),
  frozenCount: 1,
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: tovarlar (K5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkStock.mockResolvedValue(ok(stock));
  });

  it("qoldiq: hisobdagi va qayta tiklash qiymati, inflyatsiya yegan kapital, ogohlantirishlar; axe toza", async () => {
    const { container } = wrap(<KkStockScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-stock-gap")).toHaveTextContent("105 000 soʻm");
    expect(screen.getByTestId("kk-stock-frozen")).toHaveTextContent("30 000 soʻm");
    const card = screen.getByTestId("kk-item-Shakar");
    expect(within(card).getByTestId("kk-item-qty")).toHaveTextContent("70 kg");
    expect(within(card).getByRole("rowheader", { name: "Qayta tiklash narxida" }).nextSibling).toHaveTextContent("945 000 soʻm");
    expect(within(card).getByRole("note")).toHaveTextContent("Shu narxda sotsangiz, bu tovarni qayta ololmaysiz.");
    const notes = within(screen.getByTestId("kk-item-Tuz"))
      .getAllByRole("note")
      .map((n) => n.textContent);
    expect(notes).toContainEqual(expect.stringContaining("Qoldiq minimaldan kam (20 kg)"));
    expect(notes).toContainEqual(expect.stringContaining("sadaqa"));
    expect(await axeViolations(container)).toEqual([]);
  });

  it("xarid: miqdor va summa matn holida; «ilovagacha bor edi» — hamyonsiz", async () => {
    kkStockMove.mockResolvedValue(ok(stock));
    const user = userEvent.setup();
    const { container } = wrap(<KkStockScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-item-Shakar");
    await user.click(within(card).getByRole("button", { name: "Xarid" }));
    const form = within(card).getByRole("form", { name: "Shakar: Xarid" });
    await user.type(within(form).getByLabelText("Miqdor (kg)"), "1,5");
    await user.type(within(form).getByLabelText("Jami narx"), "20 250");
    await user.click(within(form).getByRole("button", { name: "Ilovagacha bor edi" }));
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkStockMove).toHaveBeenCalledWith("s-kk", "i1", { kind: "PURCHASE", qty: "1,5", amount: "20 250", wallet: null, occurredOn: null, reason: null });
  });

  it("sotuv: summa bo'sh — sotuv narxi bo'yicha (yadroda); yetmasa — yadro xatosi", async () => {
    kkStockMove.mockResolvedValue({ status: "error", error: { code: "INSUFFICIENT_STOCK", field: "qty" } });
    const user = userEvent.setup();
    wrap(<KkStockScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-item-Shakar");
    await user.click(within(card).getByRole("button", { name: "Sotuv" }));
    const form = within(card).getByRole("form", { name: "Shakar: Sotuv" });
    expect(within(form).getByLabelText("Tushum")).toHaveAccessibleDescription("Boʻsh qoldirsangiz — 13 000 soʻm / kg boʻyicha");
    await user.type(within(form).getByLabelText("Miqdor (kg)"), "80");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkStockMove).toHaveBeenCalledWith("s-kk", "i1", { kind: "SALE", qty: "80", amount: null, wallet: "CASH", occurredOn: null, reason: null });
    expect(await within(form).findByRole("alert")).toHaveTextContent("Qoldiqda buncha tovar yoʻq");
  });

  it("sanash: hisobdagi miqdor ko'rsatiladi, sabab bilan yuboriladi", async () => {
    kkStockMove.mockResolvedValue(ok(stock));
    const user = userEvent.setup();
    wrap(<KkStockScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-item-Shakar");
    await user.click(within(card).getByRole("button", { name: "Sanash" }));
    const form = within(card).getByRole("form", { name: "Shakar: Sanash" });
    expect(within(form).getByLabelText("Sanalgan miqdor (kg)")).toHaveAccessibleDescription("Hisobda: 70 kg");
    await user.type(within(form).getByLabelText("Sanalgan miqdor (kg)"), "69,5");
    await user.type(within(form).getByLabelText("Sabab"), "Toʻkilgan");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkStockMove).toHaveBeenCalledWith("s-kk", "i1", { kind: "COUNT", qty: "69,5", amount: null, wallet: null, occurredOn: null, reason: "Toʻkilgan" });
  });

  it("yangi tovar: birlik, FIFO, narxlar; harakati bor tovarda usul qulflangan", async () => {
    kkAddItem.mockResolvedValue(ok(stock));
    const user = userEvent.setup();
    const { container } = wrap(<KkStockScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Yangi tovar" }));
    const form = screen.getByRole("form", { name: "Yangi tovar" });
    await user.type(within(form).getByLabelText("Nomi"), "Sut");
    await user.selectOptions(within(form).getByLabelText("Birlik"), "ML");
    await user.click(within(form).getByRole("button", { name: "FIFO" }));
    await user.type(within(form).getByLabelText("Sotuv narxi (1 l)"), "14 000");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Tovarni qoʻshish" }));
    expect(kkAddItem).toHaveBeenCalledWith("s-kk", {
      name: "Sut",
      unit: "ML",
      method: "FIFO",
      salePrice: "14 000",
      replacementPrice: null,
      minQty: null,
      frozenDays: 90,
      note: null,
    });

    const card = screen.getByTestId("kk-item-Shakar");
    await user.click(within(card).getByRole("button", { name: "Tahrirlash" }));
    const edit = within(card).getByRole("form", { name: "Shakar: tahrirlash" });
    expect(within(edit).getByRole("group", { name: "Tannarx usuli" })).toBeDisabled();
    expect(within(edit).getByLabelText("Birlik")).toBeDisabled();
  });
});

describe("Kasb-kor bosh sahifa: tovar (K5) va majburiyatlar (K6)", () => {
  it("tovar qoldig'i, muzlagan tovar va tovar yo'qotishlari foyda tarkibida", async () => {
    kkOverview.mockResolvedValue(
      ok({
        periodStart: "2026-11-01",
        periodEnd: "2026-11-30",
        ownerSalary: null,
        salaryCarry: null,
        revenue: m("1 120 000 soʻm"),
        expenses: zero,
        cashFlow: m("1 120 000 soʻm"),
        ownerDraws: zero,
        ownerSalaryTransferred: zero,
        contributions: zero,
        ownerPaid: zero,
        salaryRemaining: null,
        overdrawn: null,
        cash: m("1 120 000 soʻm"),
        card: m("-1 250 000 soʻm"),
        equipmentPurchases: zero,
        equipmentSales: zero,
        stockPurchases: m("1 250 000 soʻm"),
        stockValue: m("834 000 soʻm"),
        stockFrozenValue: m("30 000 soʻm"),
        stockFrozenCount: 1,
        payables: m("750 000 soʻm"),
        payablesOverdue: m("750 000 soʻm"),
        wagesOwed: m("3 000 000 soʻm"),
        zakatReminder: "2026-12-01",
        scaleCheckDue: true,
        profit: {
          revenue: m("1 120 000 soʻm"),
          cogs: m("960 000 soʻm"),
          stockLosses: m("6 000 soʻm"),
          operatingExpenses: zero,
          visibleProfit: m("154 000 soʻm"),
          ownerLabor: null,
          familyLabor: zero,
          familyLaborPaid: zero,
          depreciation: zero,
          disposal: zero,
          trueProfit: m("154 000 soʻm"),
        },
        negativeWallets: ["CARD"],
        entries: [],
        closedUntil: null,
        closeDue: null,
        cashClosedUntil: null,
        receivables: zero,
        receivablesOverdue: zero,
      }),
    );
    const { container } = wrap(<KkHomeScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-stock-value")).toHaveTextContent("834 000 soʻm");
    expect(screen.getByTestId("kk-stock-frozen")).toHaveTextContent("Muzlagan tovar: 30 000 soʻm (1 ta)");
    expect(screen.getByText(/Tovar xaridi: 1 250 000 soʻm/)).toBeInTheDocument();
    // K6: ta'minotchilarga qarz va xodimlarga to'lanadigani.
    expect(screen.getByTestId("kk-payables")).toHaveTextContent("750 000 soʻm");
    expect(screen.getByText("Shundan muddati oʻtgan: 750 000 soʻm")).toBeInTheDocument();
    expect(screen.getByTestId("kk-wages-owed")).toHaveTextContent("3 000 000 soʻm");
    // K7: «Zakot kuni» va tarozi eslatmalari.
    expect(screen.getByTestId("kk-zakat-reminder")).toHaveTextContent("01.12.2026");
    expect(screen.getByTestId("kk-scale-reminder")).toHaveTextContent("Tarozini tekshirish vaqti keldi");
    const card = screen.getByRole("region", { name: "Foyda qanday hosil boʻldi" });
    expect(within(card).getByRole("rowheader", { name: /Sotilgan tovar tannarxi/ }).nextSibling).toHaveTextContent("− 960 000 soʻm");
    expect(within(card).getByRole("rowheader", { name: /Tovar yoʻqotishlari/ }).nextSibling).toHaveTextContent("− 6 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
  });
});
