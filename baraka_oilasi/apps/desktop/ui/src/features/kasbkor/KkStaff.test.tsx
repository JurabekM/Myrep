import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkStaffScreen } from "./KkStaffScreen";
import { KkSuppliersScreen } from "./KkSuppliersScreen";

const kkStaff = vi.fn();
const kkAddEmployee = vi.fn();
const kkStaffAdvance = vi.fn();
const kkStaffPay = vi.fn();
const kkSignAgreement = vi.fn();
const kkSuppliers = vi.fn();
const kkAddSupplier = vi.fn();
const kkSupplyDelivery = vi.fn();
const kkSupplyPayment = vi.fn();
const kkStock = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkStaff: (...a: unknown[]) => kkStaff(...a),
    kkAddEmployee: (...a: unknown[]) => kkAddEmployee(...a),
    kkUpdateEmployee: vi.fn(),
    kkStaffAdvance: (...a: unknown[]) => kkStaffAdvance(...a),
    kkStaffPay: (...a: unknown[]) => kkStaffPay(...a),
    kkSignAgreement: (...a: unknown[]) => kkSignAgreement(...a),
    kkEndAgreement: vi.fn(),
    kkDeleteAgreement: vi.fn(),
    exportKkAgreement: vi.fn(),
    exportKkPayslip: vi.fn(),
    kkSuppliers: (...a: unknown[]) => kkSuppliers(...a),
    kkAddSupplier: (...a: unknown[]) => kkAddSupplier(...a),
    kkUpdateSupplier: vi.fn(),
    kkSupplyDelivery: (...a: unknown[]) => kkSupplyDelivery(...a),
    kkSupplyPayment: (...a: unknown[]) => kkSupplyPayment(...a),
    kkStock: (...a: unknown[]) => kkStock(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const zero = m("0 soʻm", "0");
const ok = (data: unknown) => ({ status: "ok", data });

const signed = {
  status: "SIGNED",
  signedVersions: 1,
  signedOn: "2026-11-01",
  effectiveFrom: "2026-11-01",
  unsignedChanges: false,
  missing: [],
  canSign: false,
  templateVersion: 1,
  templateReview: "PENDING",
  startedOn: "2026-11-01",
  endedOn: null,
  reviewOn: "2027-11-01",
};

// kasbkor/SPEC 7.2: Sardor — haq 3 000 000, noyabrda 1 000 000 avans dekabrdan 2 oyda.
const sardor = {
  id: "e1",
  name: "Sardor",
  phone: null,
  agreement: signed,
  terms: {
    role: "Sotuvchi",
    duties: "Savdo va kassa",
    hours: null,
    salary: m("3 000 000 soʻm"),
    payDay: 5,
    noticeDays: 14,
    maxAdvance: m("1 500 000 soʻm"),
    maxAdvanceInstallments: 3,
    openingBalance: zero,
    arbiter: null,
    note: null,
  },
  balance: m("5 500 000 soʻm"),
  dueNow: m("3 000 000 soʻm"),
  advancesOutstanding: m("500 000 soʻm"),
  months: [
    { periodStart: "2026-12-01", periodEnd: "2026-12-31", salary: m("3 000 000 soʻm"), deducted: m("500 000 soʻm"), net: m("2 500 000 soʻm"), paid: zero, balance: m("5 500 000 soʻm") },
    { periodStart: "2026-11-01", periodEnd: "2026-11-30", salary: m("3 000 000 soʻm"), deducted: zero, net: m("3 000 000 soʻm"), paid: zero, balance: m("3 000 000 soʻm") },
  ],
  advances: [
    {
      id: "a1",
      givenOn: "2026-11-15",
      amount: m("1 000 000 soʻm"),
      installments: 2,
      schedule: [
        { date: "2026-12-01", amount: m("500 000 soʻm") },
        { date: "2027-01-01", amount: m("500 000 soʻm") },
      ],
      deducted: m("500 000 soʻm"),
      outstanding: m("500 000 soʻm"),
    },
  ],
  events: [],
};
const draft = {
  ...sardor,
  id: "e2",
  name: "Dilshod",
  agreement: { ...signed, status: "DRAFT", signedVersions: 0, signedOn: null, effectiveFrom: null, unsignedChanges: true, missing: ["duties"], canSign: false },
  terms: { ...sardor.terms, duties: null, role: "Shogird" },
  balance: zero,
  dueNow: zero,
  advancesOutstanding: zero,
  months: [],
  advances: [],
};
const staff = { employees: [sardor, draft], owed: m("3 000 000 soʻm"), advancesOutstanding: m("500 000 soʻm"), templateReview: "PENDING" };

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: xodimlar (K6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkStaff.mockResolvedValue(ok(staff));
  });

  it("hisob, kelishuv holati, shablon ogohlantirishi va yetishmayotgan maydon; axe toza", async () => {
    const { container } = wrap(<KkStaffScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-staff-owed")).toHaveTextContent("3 000 000 soʻm");
    expect(screen.getAllByRole("note")[0]).toHaveTextContent("yurist koʻrigidan oʻtmagan");
    const card = screen.getByTestId("kk-employee-Sardor");
    expect(within(card).getByTestId("kk-employee-due")).toHaveTextContent("3 000 000 soʻm");
    expect(within(card).getByTestId("kk-employee-status")).toHaveTextContent("Imzolangan: 1-versiya, 01.11.2026");
    const dil = screen.getByTestId("kk-employee-Dilshod");
    expect(within(dil).getByRole("note")).toHaveTextContent("Imzolashdan oldin toʻldiring: vazifalar");
    expect(within(dil).queryByRole("button", { name: "Avans" })).toBeNull();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("avans: kelishuv qoidasi ko'rsatiladi, yadro chegarani tekshiradi", async () => {
    kkStaffAdvance.mockResolvedValue({ status: "error", error: { code: "ADVANCE_ABOVE_LIMIT", field: "amount" } });
    const user = userEvent.setup();
    const { container } = wrap(<KkStaffScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-employee-Sardor");
    await user.click(within(card).getByRole("button", { name: "Avans" }));
    const form = within(card).getByRole("form", { name: "Sardor: avans" });
    expect(within(form).getByLabelText("Summa")).toHaveAccessibleDescription(/foizsiz, jarimasiz; qoldigʻi 1 500 000 soʻm gacha, koʻpi bilan 3 oyda/);
    await user.type(within(form).getByLabelText("Summa"), "1 200 000");
    await user.selectOptions(within(form).getByLabelText("Necha oyda ushlanadi"), "2");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Avansni yozish" }));
    expect(kkStaffAdvance).toHaveBeenCalledWith("s-kk", "e1", { amount: "1 200 000", installments: 2, startOn: null, wallet: "CASH", occurredOn: null, note: null });
    expect(await within(form).findByRole("alert")).toHaveTextContent("Avans qoldigʻi kelishilgan chegaradan oshadi");
  });

  it("haq to'lash: hozir to'lanadigani taklif qilinadi", async () => {
    kkStaffPay.mockResolvedValue(ok(staff));
    const user = userEvent.setup();
    wrap(<KkStaffScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-employee-Sardor");
    await user.click(within(card).getByRole("button", { name: "Haq toʻlash" }));
    const form = within(card).getByRole("form", { name: "Sardor: haq toʻlash" });
    expect(within(form).getByLabelText("Summa")).toHaveValue("3 000 000");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkStaffPay).toHaveBeenCalledWith("s-kk", "e1", { amount: "3 000 000", wallet: "CARD", occurredOn: null, note: null });
  });

  it("yangi xodim: matn holida yadroga; telefon roziliksiz — yadro xatosi", async () => {
    kkAddEmployee.mockResolvedValue({ status: "error", error: { code: "PHONE_CONSENT_REQUIRED", field: "phoneConsent" } });
    const user = userEvent.setup();
    const { container } = wrap(<KkStaffScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Yangi xodim" }));
    const form = screen.getByRole("form", { name: "Yangi xodim" });
    await user.type(within(form).getByLabelText("Ism"), "Sardor");
    await user.type(within(form).getByLabelText("Lavozim"), "Sotuvchi");
    await user.type(within(form).getByLabelText("Telefon (ixtiyoriy)"), "+998 90 000 00 00");
    await user.type(within(form).getByLabelText("Oylik haq"), "3 000 000");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Xodimni qoʻshish" }));
    expect(kkAddEmployee).toHaveBeenCalledWith("s-kk", expect.objectContaining({ name: "Sardor", role: "Sotuvchi", salary: "3 000 000", payDay: 5, phone: "+998 90 000 00 00", phoneConsent: false }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("roziligini belgilang");
  });
});

// kasbkor/SPEC 7.1 SUPPLY: 100 kg shakar 12 500 dan, 30 kunlik muddat; 500 000 to'langan, 4 kun kechikkan.
const baza = {
  id: "s1",
  name: "Ulgurji baza",
  phone: null,
  agreement: signed,
  terms: { goods: "Shakar", itemId: "i1", itemName: "Shakar", unit: "G", unitPrice: m("12 500 soʻm"), paymentDays: 30, delivery: null, returns: null, arbiter: null, note: null },
  outstanding: m("750 000 soʻm"),
  overdue: m("750 000 soʻm"),
  dueSoon: zero,
  nextDue: { date: "2026-12-01", amount: m("750 000 soʻm") },
  deliveries: [
    { id: "d1", deliveredOn: "2026-11-01", dueOn: "2026-12-01", amount: m("1 250 000 soʻm"), paid: m("500 000 soʻm"), outstanding: m("750 000 soʻm"), state: "OVERDUE", overdueDays: 4, qty: "100", note: null },
  ],
  payments: [{ id: "p1", paidOn: "2026-11-10", amount: m("500 000 soʻm"), wallet: "CARD", asExpense: false, note: null }],
};
const suppliers = { suppliers: [baza], outstanding: m("750 000 soʻm"), overdue: m("750 000 soʻm"), dueSoon: zero, templateReview: "PENDING" };

describe("Kasb-kor: ta'minotchilar (K6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkSuppliers.mockResolvedValue(ok(suppliers));
    kkStock.mockResolvedValue(ok({ items: [{ id: "i1", name: "Shakar", unit: "G" }], value: zero, replacementValue: zero, inflationGap: zero, frozenValue: zero, frozenCount: 0 }));
  });

  it("qarz, kechikish (jarimasiz) va tarix; axe toza", async () => {
    const { container } = wrap(<KkSuppliersScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-supply-overdue")).toHaveTextContent("750 000 soʻm");
    const card = screen.getByTestId("kk-supplier-Ulgurji baza");
    expect(within(card).getByRole("rowheader", { name: "Narx" }).nextSibling).toHaveTextContent("12 500 soʻm / kg");
    expect(within(card).getByRole("note")).toHaveTextContent("Jarima yoʻq");
    expect(within(card).getByText("100 kg · 4 kun kechikkan (muddati 01.12.2026)")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("yetkazish: miqdor kg da; to'lov — eng yaqin muddatdagi qoldiq taklif qilinadi", async () => {
    kkSupplyDelivery.mockResolvedValue(ok(suppliers));
    kkSupplyPayment.mockResolvedValue(ok(suppliers));
    const user = userEvent.setup();
    wrap(<KkSuppliersScreen spaceId="s-kk" />);
    const card = await screen.findByTestId("kk-supplier-Ulgurji baza");
    await user.click(within(card).getByRole("button", { name: "Yetkazish" }));
    const form = within(card).getByRole("form", { name: "Ulgurji baza: yetkazish" });
    await user.type(within(form).getByLabelText("Miqdor (kg)"), "50");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkSupplyDelivery).toHaveBeenCalledWith("s-kk", "s1", { deliveredOn: null, qty: "50", amount: null, note: null });

    await user.click(within(card).getByRole("button", { name: "Toʻlov" }));
    const pay = within(card).getByRole("form", { name: "Ulgurji baza: toʻlov" });
    expect(within(pay).getByLabelText("Summa")).toHaveValue("750 000");
    await user.click(within(pay).getByRole("button", { name: "Saqlash" }));
    expect(kkSupplyPayment).toHaveBeenCalledWith("s-kk", "s1", { amount: "750 000", wallet: "CARD", paidOn: null, note: null });
  });

  it("yangi ta'minotchi: tovar bog'lansa narx birligi va izoh o'zgaradi", async () => {
    kkAddSupplier.mockResolvedValue(ok(suppliers));
    const user = userEvent.setup();
    const { container } = wrap(<KkSuppliersScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Yangi taʼminotchi" }));
    const form = screen.getByRole("form", { name: "Yangi taʼminotchi" });
    expect(within(form).getByLabelText("Tovar qoldigʻidagi tovar")).toHaveAccessibleDescription(/chiqim sifatida/);
    await user.type(within(form).getByLabelText("Nomi"), "Ulgurji baza");
    await user.selectOptions(await within(form).findByLabelText("Tovar qoldigʻidagi tovar"), "i1");
    expect(within(form).getByLabelText("Tovar qoldigʻidagi tovar")).toHaveAccessibleDescription(/tovar qoldigʻiga kiradi/);
    await user.type(within(form).getByLabelText("Qotirilgan narx (1 kg)"), "12 500");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Taʼminotchini qoʻshish" }));
    expect(kkAddSupplier).toHaveBeenCalledWith("s-kk", expect.objectContaining({ name: "Ulgurji baza", itemId: "i1", unitPrice: "12 500", paymentDays: 30 }));
  });
});
