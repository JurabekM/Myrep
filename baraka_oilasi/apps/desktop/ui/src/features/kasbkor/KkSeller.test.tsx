import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkSellerCreditScreen, KkSellerScreen } from "./KkSellerScreen";
import { KkShiftScreen, KkShiftsTable } from "./KkShiftScreen";

const kkSellerDay = vi.fn();
const kkCatalog = vi.fn();
const kkSellerSale = vi.fn();
const kkCreditBook = vi.fn();
const kkCreditPayment = vi.fn();
const kkShiftDraft = vi.fn();
const kkCloseShift = vi.fn();
const kkShifts = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkSellerDay: (...a: unknown[]) => kkSellerDay(...a),
    kkCatalog: (...a: unknown[]) => kkCatalog(...a),
    kkSellerSale: (...a: unknown[]) => kkSellerSale(...a),
    kkCreditBook: (...a: unknown[]) => kkCreditBook(...a),
    kkCreditPayment: (...a: unknown[]) => kkCreditPayment(...a),
    kkShiftDraft: (...a: unknown[]) => kkShiftDraft(...a),
    kkCloseShift: (...a: unknown[]) => kkCloseShift(...a),
    kkShifts: (...a: unknown[]) => kkShifts(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const day = (over: Record<string, unknown> = {}) => ({
  day: "2026-12-02",
  sales: [{ id: "i1", kind: "SALE", label: "Shakar", qty: "2", amount: m("30 000 soʻm"), channel: "CASH" }],
  cash: m("30 000 soʻm"),
  card: zero,
  shiftClosed: false,
  ...over,
});

const shift = (over: Record<string, unknown> = {}) => ({
  day: "2026-12-02",
  opening: m("200 000 soʻm"),
  openingKnown: false,
  cashSales: m("30 000 soʻm"),
  creditPayments: m("220 000 soʻm"),
  cardIn: m("50 000 soʻm"),
  expected: m("450 000 soʻm"),
  counted: null,
  difference: null,
  status: null,
  handedOver: null,
  left: null,
  suggestSearch: false,
  closed: false,
  ...over,
});

const record = {
  id: "s1",
  deviceId: "dev-shop",
  deviceName: "Do'kon telefoni",
  day: "2026-12-02",
  opening: m("200 000 soʻm"),
  cashSales: m("30 000 soʻm"),
  creditPayments: m("220 000 soʻm"),
  cardIn: m("50 000 soʻm"),
  expected: m("450 000 soʻm"),
  counted: m("440 000 soʻm"),
  difference: m("−10 000 soʻm"),
  status: "SHORT",
  reason: "CHANGE_ERROR",
  handedOver: m("300 000 soʻm"),
  left: m("140 000 soʻm"),
  note: null,
};

beforeEach(() => {
  [kkSellerDay, kkCatalog, kkSellerSale, kkCreditBook, kkCreditPayment, kkShiftDraft, kkCloseShift, kkShifts].forEach((f) => f.mockReset());
  kkCatalog.mockResolvedValue(ok([{ id: "it1", name: "Shakar", unit: "G", salePrice: m("15 000 soʻm") }]));
  kkShifts.mockResolvedValue(ok([]));
});

describe("Sotuvchi qurilmasi", () => {
  it("sotuv: katalogdan tovar va miqdor; bugungi yozuvlar; foyda yo'q", async () => {
    kkSellerDay.mockResolvedValue(ok(day()));
    kkSellerSale.mockResolvedValue(ok(day()));
    const user = userEvent.setup();
    const { container } = wrap(<KkSellerScreen spaceId="kk" />);
    expect(await screen.findByTestId("kk-seller-totals")).toHaveTextContent("Naqd: 30 000 soʻm");
    expect(screen.queryByText(/foyda \(/i)).not.toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Yangi sotuv" });
    await user.selectOptions(within(form).getByLabelText("Tovar"), await within(form).findByRole("option", { name: /Shakar/ }));
    await user.type(within(form).getByLabelText("Miqdor (kg)"), "2");
    await user.click(within(form).getByRole("button", { name: "Sotuvni yozish" }));
    expect(kkSellerSale).toHaveBeenCalledWith("kk", { itemId: "it1", qty: "2", amount: null, channel: "CASH", note: null });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("smena yopilgan bo'lsa — sotuv formasi yo'q", async () => {
    kkSellerDay.mockResolvedValue(ok(day({ shiftClosed: true })));
    wrap(<KkSellerScreen spaceId="kk" />);
    expect(await screen.findByTestId("kk-seller-closed")).toHaveTextContent("smena yopilgan");
    expect(screen.queryByRole("form", { name: "Yangi sotuv" })).not.toBeInTheDocument();
  });

  it("nasiya to'lovi: faqat ochiq nasiyalar", async () => {
    const sale = (id: string, name: string, outstanding: string) => ({
      id,
      customerId: "c",
      customerName: name,
      customerPhone: null,
      item: "Gilam",
      soldOn: "2026-11-10",
      cashPrice: null,
      creditPrice: m("660 000 soʻm"),
      installments: 3,
      witness: null,
      note: null,
      schedule: [],
      paid: zero,
      forgiven: zero,
      outstanding: m(`${outstanding} soʻm`, outstanding === "0" ? "0" : "1"),
      status: "CURRENT",
      overdueDays: 0,
      bucket: null,
      events: [],
      talkThisWeek: false,
      reminder: null,
    });
    kkCreditBook.mockResolvedValue(ok({ sales: [sale("a", "Malika", "440 000"), sale("b", "Aziz", "0")], aging: {}, weekStart: "2026-11-27" }));
    kkCreditPayment.mockResolvedValue(ok({ sales: [], aging: {}, weekStart: "2026-11-27" }));
    const user = userEvent.setup();
    const { container } = wrap(<KkSellerCreditScreen spaceId="kk" />);
    const row = await screen.findByTestId("kk-seller-credit-Malika");
    expect(row).toHaveTextContent("Qoldiq: 440 000 soʻm");
    expect(screen.queryByTestId("kk-seller-credit-Aziz")).not.toBeInTheDocument();
    await user.type(within(row).getByLabelText("Toʻlov summasi"), "220 000");
    await user.click(within(row).getByRole("button", { name: "Toʻlovni yozish" }));
    expect(kkCreditPayment).toHaveBeenCalledWith("kk", "a", { amount: "220 000", wallet: "CASH", paidOn: null, note: null });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("smena: birinchi smenada ochilish, farq va sabab, yopish", async () => {
    kkShiftDraft.mockImplementation((_s: string, input: { counted: string | null }) =>
      Promise.resolve(
        ok(
          input.counted
            ? shift({ counted: m("440 000 soʻm"), difference: m("−10 000 soʻm", "-1000000"), status: "SHORT", handedOver: m("300 000 soʻm"), left: m("140 000 soʻm") })
            : shift(),
        ),
      ),
    );
    kkCloseShift.mockResolvedValue(ok(shift({ closed: true })));
    const user = userEvent.setup();
    const { container } = wrap(<KkShiftScreen spaceId="kk" />);
    const form = await screen.findByRole("form", { name: "Smenani yopish" });
    expect(within(form).getByTestId("kk-shift-expected")).toHaveTextContent("450 000");
    await user.type(within(form).getByLabelText("Kassadagi boshlangʻich naqd"), "200 000");
    await user.type(within(form).getByLabelText("Sanalgan summa"), "440 000");
    await user.type(within(form).getByLabelText("Egasiga topshirildi"), "300 000");
    expect(await within(form).findByTestId("kk-shift-difference")).toHaveTextContent("Kamomad");
    expect(within(form).getByText(/ertangi ochilish/)).toHaveTextContent("140 000");
    await user.click(within(form).getByLabelText("Qaytim xatosi"));
    await user.click(within(form).getByRole("button", { name: "Smenani yopish" }));
    expect(kkCloseShift).toHaveBeenCalledWith("kk", { opening: "200 000", counted: "440 000", handedOver: "300 000", reason: "CHANGE_ERROR", note: null });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("egasi: sotuvchi smenalari jadvali", async () => {
    kkShifts.mockResolvedValue(ok([record]));
    wrap(<KkShiftsTable spaceId="kk" title="Sotuvchi smenalari" hideEmpty />);
    const row = await screen.findByTestId("kk-shift-row");
    expect(row).toHaveTextContent("Do'kon telefoni");
    expect(row).toHaveTextContent("Qaytim xatosi");
  });
});
