import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { TwoShoresScreen } from "./TwoShoresScreen";

const mfTwoShores = vi.fn();
const mfConfirmReceipt = vi.fn();
const mfRecordSpend = vi.fn();
const household = vi.fn();
const categories = vi.fn();
const debtsOverview = vi.fn();
const mfPayDebt = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    mfTwoShores: (...a: unknown[]) => mfTwoShores(...a),
    mfConfirmReceipt: (...a: unknown[]) => mfConfirmReceipt(...a),
    mfRecordSpend: (...a: unknown[]) => mfRecordSpend(...a),
    household: (...a: unknown[]) => household(...a),
    categories: (...a: unknown[]) => categories(...a),
    debtsOverview: (...a: unknown[]) => debtsOverview(...a),
    mfPayDebt: (...a: unknown[]) => mfPayDebt(...a),
  },
}));

const u = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const k = (formatted: string) => ({ minor: "1", currency: "KRW", formatted, plain: formatted.replace(" KRW", "") });
const ok = (data: unknown) => ({ status: "ok", data });
const share = (purpose: string, bp: number) => ({ purpose, bp, percent: String(bp / 100) });
const row = (purpose: string, received: string, spent: string, balance: string, overspent = false) => ({
  purpose,
  received: u(`${received} soʻm`),
  spent: u(`${spent} soʻm`),
  balance: u(`${balance} soʻm`),
  overspent,
});

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const pending = {
  moveId: "mv1",
  sent: k("1 200 000 KRW"),
  sentOn: "2026-10-12",
  note: null,
  shares: [share("HOUSEHOLD", 5000), share("DEBT", 3000), share("BUILD", 2000)],
  expected: u("10 900 000 soʻm", "1090000000"),
  receipt: null,
  allocation: [],
};

const view = (over: Record<string, unknown> = {}) => ({
  uySpaceId: "uy",
  remittances: [pending],
  purposes: [row("HOUSEHOLD", "0", "0", "0"), row("DEBT", "0", "0", "0"), row("BUILD", "0", "0", "0")],
  received: u("0 soʻm", "0"),
  spent: u("0 soʻm", "0"),
  balance: u("0 soʻm", "0"),
  pending: 1,
  overspent: false,
  spends: [],
  ...over,
});

beforeEach(() => {
  [mfTwoShores, mfConfirmReceipt, mfRecordSpend, household, categories, debtsOverview, mfPayDebt].forEach((f) => f.mockReset());
  household.mockResolvedValue(ok({ id: "h", name: "Oila", locale: "uz", baseCurrency: "UZS", monthStartDay: 1, spaces: [], members: [{ id: "m2", displayName: "Mohira", role: "ADULT" }] }));
  categories.mockResolvedValue(ok([{ id: "c1", nameKey: "category.food", customName: "Bozor", defaultNecessity: null, isSystem: false }]));
});

describe("Ikki qirg'oq — uy tomoni", () => {
  it("yo'ldagi pul: summa musofirning yozuvidan taklif, kim oldi, qabul", async () => {
    mfTwoShores.mockResolvedValue(ok(view()));
    mfConfirmReceipt.mockResolvedValue(ok(view({ pending: 0 })));
    const user = userEvent.setup();
    const { container } = wrap(<TwoShoresScreen mfSpaceId="mf" uySpaceId="uy" />);
    const r = await screen.findByTestId("mf-remittance");
    expect(r).toHaveTextContent("1 200 000 KRW");
    expect(r).toHaveTextContent("Yoʻlda");
    expect(r).toHaveTextContent("Uy xarajati 50 % · Qarz toʻlovi 30 % · Qurilish va taʼmir 20 %");
    const form = within(r).getByRole("form", { name: "Qabul qilish" });
    expect(within(form).getByLabelText("Olingan summa (soʻmda)")).toHaveValue("10 900 000");
    await user.selectOptions(await within(form).findByLabelText("Kim oldi"), await within(form).findByRole("option", { name: "Mohira" }));
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Qabul qildim" }));
    expect(mfConfirmReceipt).toHaveBeenCalledWith("mf", "mv1", { received: "10 900 000", channel: "CARD", memberId: "m2", receivedOn: null, note: null });
  });

  it("maqsad bo'yicha xarajat va ortiq sarf — ayblovsiz savol", async () => {
    const received = {
      ...pending,
      receipt: { received: u("10 900 000 soʻm"), receivedOn: "2026-10-13", memberId: "m2", memberName: "Mohira", note: null },
      allocation: [
        { purpose: "HOUSEHOLD", amount: u("5 450 000 soʻm") },
        { purpose: "DEBT", amount: u("3 270 000 soʻm") },
        { purpose: "BUILD", amount: u("2 180 000 soʻm") },
      ],
    };
    mfTwoShores.mockResolvedValue(
      ok(
        view({
          remittances: [received],
          pending: 0,
          overspent: true,
          purposes: [row("HOUSEHOLD", "5 450 000", "6 000 000", "-550 000", true), row("DEBT", "3 270 000", "0", "3 270 000"), row("BUILD", "2 180 000", "0", "2 180 000")],
          spends: [{ id: "e1", kind: "EXPENSE", purpose: "HOUSEHOLD", amount: u("6 000 000 soʻm"), categoryId: "c1", debtId: null, creditor: null, occurredOn: "2026-10-14", note: "Bozor" }],
        }),
      ),
    );
    mfRecordSpend.mockResolvedValue(ok(view()));
    const user = userEvent.setup();
    const { container } = wrap(<TwoShoresScreen mfSpaceId="mf" uySpaceId="uy" />);
    expect(await screen.findByTestId("mf-shores-overspent")).toHaveTextContent("Kelishuvni birga yangilaymizmi?");
    expect(screen.getByTestId("mf-remittance")).toHaveTextContent("Qabul qilindi: 10 900 000 soʻm");
    expect(screen.getByTestId("mf-remittance")).toHaveTextContent("Uy xarajati: 5 450 000 soʻm");
    expect(screen.getByTestId("mf-purpose-HOUSEHOLD")).toHaveTextContent("-550 000");
    expect(await axeViolations(container)).toEqual([]);
    const form = screen.getByRole("form", { name: "Maqsad boʻyicha xarajat" });
    await user.selectOptions(within(form).getByLabelText("Maqsad"), "BUILD");
    await user.type(within(form).getByLabelText("Summa"), "1 000 000");
    await user.click(within(form).getByRole("button", { name: "Xarajatni yozish" }));
    expect(mfRecordSpend).toHaveBeenCalledWith("mf", { purpose: "BUILD", amount: "1 000 000", categoryId: "c1", channel: "CASH", occurredOn: null, note: null });
  });

  it("«Qarz to'lovi» maqsadi: kategoriya o'rniga Uy qarzi va «Qarzni to'lash»", async () => {
    mfTwoShores.mockResolvedValue(
      ok(
        view({
          pending: 0,
          spends: [{ id: "r1", kind: "DEBT_PAYMENT", purpose: "DEBT", amount: u("1 000 000 soʻm"), categoryId: null, debtId: "d1", creditor: "Togʻam", occurredOn: "2026-10-15", note: null }],
        }),
      ),
    );
    debtsOverview.mockResolvedValue(
      ok({
        debts: [
          { id: "d0", creditor: "Bank", status: "CLOSED", balance: u("0 soʻm", "0") },
          { id: "d1", creditor: "Togʻam", status: "ACTIVE", balance: u("14 000 000 soʻm", "1400000000") },
        ],
      }),
    );
    mfPayDebt.mockResolvedValue(ok(view()));
    const user = userEvent.setup();
    const { container } = wrap(<TwoShoresScreen mfSpaceId="mf" uySpaceId="uy" />);
    expect(await screen.findByTestId("mf-spend")).toHaveTextContent("kimga: Togʻam");
    const form = screen.getByRole("form", { name: "Maqsad boʻyicha xarajat" });
    await user.selectOptions(within(form).getByLabelText("Maqsad"), "DEBT");
    const debt = await within(form).findByLabelText("Qaysi qarz");
    expect(await within(debt).findByRole("option", { name: "Togʻam · 14 000 000 soʻm" })).toBeInTheDocument();
    expect(within(debt).queryByRole("option", { name: /Bank/ })).not.toBeInTheDocument();
    expect(within(form).queryByLabelText("Kategoriya")).not.toBeInTheDocument();
    await user.type(within(form).getByLabelText("Summa"), "500 000");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Qarzni toʻlash" }));
    expect(mfPayDebt).toHaveBeenCalledWith("mf", { debtId: "d1", amount: "500 000", paidOn: null, note: null });
    expect(mfRecordSpend).not.toHaveBeenCalled();
  });
});
