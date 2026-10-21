import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkCashScreen } from "./KkCashScreen";
import { KkCreditScreen } from "./KkCreditScreen";

const kkCashDraft = vi.fn();
const kkCloseCashDay = vi.fn();
const kkCashDays = vi.fn();
const kkCreditBook = vi.fn();
const kkCustomers = vi.fn();
const kkAddCustomer = vi.fn();
const kkAddCreditSale = vi.fn();
const kkCreditPayment = vi.fn();
const kkCreditMark = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkCashDraft: (...a: unknown[]) => kkCashDraft(...a),
    kkCloseCashDay: (...a: unknown[]) => kkCloseCashDay(...a),
    kkCashDays: (...a: unknown[]) => kkCashDays(...a),
    kkCreditBook: (...a: unknown[]) => kkCreditBook(...a),
    kkCustomers: (...a: unknown[]) => kkCustomers(...a),
    kkAddCustomer: (...a: unknown[]) => kkAddCustomer(...a),
    kkAddCreditSale: (...a: unknown[]) => kkAddCreditSale(...a),
    kkCreditPayment: (...a: unknown[]) => kkCreditPayment(...a),
    kkCreditMark: (...a: unknown[]) => kkCreditMark(...a),
    kkCreditExtend: vi.fn(),
    kkCreditForgive: vi.fn(),
    kkDeleteCreditSale: vi.fn(),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "").replace(/\s/g, "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

// kasbkor/SPEC 5.1 Bahodir aka.
const draft = {
  day: "2026-11-20",
  opening: m("500 000 soʻm"),
  cashSales: m("3 200 000 soʻm"),
  cashExpenses: m("400 000 soʻm"),
  ownerDraws: m("300 000 soʻm"),
  handedOver: m("1 500 000 soʻm"),
  otherIn: zero,
  otherOut: zero,
  expected: m("1 500 000 soʻm"),
  counted: null,
  difference: null,
  status: null,
  suggestSearch: false,
  lastClosed: null,
};

// kasbkor/SPEC 5.2 Malika.
const sale = {
  id: "s1",
  customerId: "c1",
  customerName: "Malika",
  customerPhone: "+998 90 123 45 67",
  item: "Koʻylak",
  soldOn: "2026-11-10",
  cashPrice: m("600 000 soʻm"),
  creditPrice: m("660 000 soʻm"),
  installments: 3,
  witness: null,
  note: null,
  schedule: [
    { due: "2026-11-10", amount: m("220 000 soʻm"), covered: m("220 000 soʻm"), state: "PAID" },
    { due: "2026-12-10", amount: m("220 000 soʻm"), covered: zero, state: "OVERDUE" },
    { due: "2027-01-10", amount: m("220 000 soʻm"), covered: zero, state: "DUE" },
  ],
  paid: m("220 000 soʻm"),
  forgiven: zero,
  outstanding: m("440 000 soʻm"),
  status: "OVERDUE",
  overdueDays: 20,
  bucket: "D1_30",
  nextDue: { date: "2026-12-10", amount: m("220 000 soʻm") },
  creditMarkup: m("60 000 soʻm"),
  events: [{ id: "e1", kind: "PAYMENT", occurredOn: "2026-11-10", amount: m("220 000 soʻm"), months: null, wallet: "CARD", note: null }],
  talkThisWeek: false,
};
const book = {
  sales: [sale],
  aging: { current: zero, d1_30: m("440 000 soʻm"), d31_60: zero, d61_90: zero, d90_plus: zero, total: m("440 000 soʻm") },
  weekStart: "2026-12-25",
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: kassa (K4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkCashDays.mockResolvedValue(ok([]));
  });

  it("kutilgan qoldiq yadrodan; sanalgan → farq → sabab → kunni yopish; axe toza", async () => {
    kkCashDraft.mockImplementation((_s: string, day: string | null, counted: string | null) =>
      Promise.resolve(ok(counted ? { ...draft, day: day ?? draft.day, counted: m("1 450 000 soʻm"), difference: m("-50 000 soʻm"), status: "SHORT" } : draft)),
    );
    kkCloseCashDay.mockResolvedValue(ok({}));
    const user = userEvent.setup();
    const { container } = wrap(<KkCashScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-cash-expected")).toHaveTextContent("1 500 000 soʻm");
    expect(screen.getByTestId("kk-cash-opening")).toHaveTextContent("500 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Sanalgan summa"), "1 450 000");
    await user.click(screen.getByRole("button", { name: "Tekshirish" }));
    expect(kkCashDraft).toHaveBeenLastCalledWith("s-kk", "2026-11-20", "1 450 000");
    expect(await screen.findByTestId("kk-cash-difference")).toHaveTextContent("Kamomad: -50 000 soʻm");
    await user.click(screen.getByLabelText("Nomaʼlum"));
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Kunni yopish" }));
    expect(kkCloseCashDay).toHaveBeenCalledWith("s-kk", { day: "2026-11-20", counted: "1 450 000", reason: "UNKNOWN", note: null });
  });

  it("bugungi kassa yopilgan — holat matni va tarix", async () => {
    kkCashDraft.mockResolvedValue({ status: "error", error: { code: "CASH_DAY_CLOSED", field: "day" } });
    kkCashDays.mockResolvedValue(
      ok([{ id: "d1", day: "2026-11-20", opening: m("500 000 soʻm"), expected: m("1 500 000 soʻm"), counted: m("1 450 000 soʻm"), difference: m("-50 000 soʻm"), status: "SHORT", reason: "UNKNOWN", note: null, suggestSearch: false }]),
    );
    const { container } = wrap(<KkCashScreen spaceId="s-kk" />);
    expect(await screen.findByRole("status")).toHaveTextContent("Bugungi kassa yopilgan");
    const history = await screen.findByRole("region", { name: "Yopilgan kunlar" });
    expect(within(history).getByText("-50 000 soʻm")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("Kasb-kor: nasiya daftari (K4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkCreditBook.mockResolvedValue(ok(book));
    kkCustomers.mockResolvedValue(ok([{ id: "c1", name: "Malika", phone: null, note: null, outstanding: m("440 000 soʻm"), openSales: 1 }]));
  });

  it("yosh guruhlari, haftalik ko'rik eslatmasi va belgi; axe toza", async () => {
    kkCreditMark.mockResolvedValue(ok(book));
    const user = userEvent.setup();
    const { container } = wrap(<KkCreditScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-credit-total")).toHaveTextContent("440 000 soʻm");
    expect(screen.getByTestId("kk-credit-d1_30")).toHaveTextContent("440 000 soʻm");
    const review = screen.getByRole("region", { name: "Haftalik koʻrik (juma)" });
    expect(within(review).getByLabelText("Eslatma matni")).toHaveValue(
      "Assalomu alaykum, Malika! Koʻylak uchun 220 000 soʻm toʻlov muddati 10.12.2026 edi. Imkoningiz boʻlganda toʻlab qoʻysangiz, xursand boʻlardik. Rahmat!",
    );
    await user.click(within(review).getByLabelText("Bu hafta gaplashaman"));
    expect(kkCreditMark).toHaveBeenCalledWith("s-kk", "s1", true);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("to'lov: navbatdagi summa taklif qilinadi, hamyon tanlanadi", async () => {
    kkCreditPayment.mockResolvedValue(ok(book));
    const user = userEvent.setup();
    wrap(<KkCreditScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-credit-sale-Malika");
    expect(within(card).getByTestId("kk-credit-status")).toHaveTextContent("20 kun kechikkan");
    await user.click(within(card).getByRole("button", { name: "Toʻlov" }));
    const form = within(card).getByRole("form", { name: "Toʻlov" });
    expect(within(form).getByLabelText("Summa")).toHaveValue("220000");
    await user.click(within(form).getByRole("button", { name: "Karta" }));
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkCreditPayment).toHaveBeenCalledWith("s-kk", "s1", { amount: "220000", wallet: "CARD", paidOn: null, note: null });
  });

  it("yangi nasiya: shartlar matn holida; telefon roziliksiz — yadro xatosi", async () => {
    kkAddCreditSale.mockResolvedValue(ok(book));
    kkAddCustomer.mockResolvedValue({ status: "error", error: { code: "PHONE_CONSENT_REQUIRED", field: "phoneConsent" } });
    const user = userEvent.setup();
    const { container } = wrap(<KkCreditScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Yangi nasiya" }));
    const form = await screen.findByRole("form", { name: "Nasiya shartlari" });
    await user.type(within(form).getByLabelText("Tovar yoki xizmat"), "Koʻylak");
    await user.type(within(form).getByLabelText("Naqd narxi (maʼlumot uchun)"), "600 000");
    await user.type(within(form).getByLabelText("Nasiya narxi (qotiriladi)"), "660 000");
    expect(within(form).getByText(/ustama, jarima yoki foiz maydoni yoʻq/)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkAddCreditSale).toHaveBeenCalledWith("s-kk", {
      customerId: "c1",
      item: "Koʻylak",
      cashPrice: "600 000",
      creditPrice: "660 000",
      installments: 3,
      soldOn: null,
      firstDue: null,
      witness: null,
      note: null,
    });

    await user.click(await screen.findByRole("button", { name: "Yangi nasiya" }));
    await user.click(screen.getByRole("button", { name: "Yangi mijoz" }));
    const cust = screen.getByRole("form", { name: "Yangi mijoz" });
    await user.type(within(cust).getByLabelText("Ism"), "Dilnoza");
    await user.type(within(cust).getByLabelText("Telefon (ixtiyoriy)"), "+998 91 000 00 00");
    await user.click(within(cust).getByRole("button", { name: "Mijozni saqlash" }));
    expect(await within(cust).findByRole("alert")).toHaveTextContent("mijoz roziligini belgilang");
  });
});
