import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { useUi } from "../../state/ui";
import { MfHomeScreen } from "./MfHomeScreen";

const mfOverview = vi.fn();
const mfSetSettings = vi.fn();
const mfSetRate = vi.fn();
const mfRecordIncome = vi.fn();
const mfRecordMove = vi.fn();
const categories = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    mfOverview: (...a: unknown[]) => mfOverview(...a),
    mfSetSettings: (...a: unknown[]) => mfSetSettings(...a),
    mfSetRate: (...a: unknown[]) => mfSetRate(...a),
    mfRecordIncome: (...a: unknown[]) => mfRecordIncome(...a),
    mfRecordMove: (...a: unknown[]) => mfRecordMove(...a),
    mfRecordExpense: vi.fn(),
    categories: (...a: unknown[]) => categories(...a),
  },
}));

const m = (formatted: string, minor = "1", currency = "KRW") => ({ minor, currency, formatted, plain: formatted.replace(/ (soʻm|KRW)$/, "") });
const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const settings = {
  country: "Koreya",
  workCurrency: "KRW",
  homeCurrency: "UZS",
  shareBp: 2000,
  sharePercent: "20",
  target: m("120 000 000 soʻm", "12000000000", "UZS"),
  returnOn: "2027-12-01",
  currencyLocked: true,
};

const overview = (over: Record<string, unknown> = {}) => ({
  settings,
  defaultSharePercent: "20",
  periodStart: "2026-10-01",
  periodEnd: "2026-10-31",
  month: {
    income: m("2 600 000 KRW"),
    expenses: m("810 000 KRW"),
    sentHome: m("1 200 000 KRW"),
    fees: m("5 000 KRW"),
    fundIn: m("0 KRW", "0"),
    fundOut: m("0 KRW", "0"),
    fundNet: m("0 KRW", "0"),
    pocket: m("735 000 KRW"),
    shareTarget: m("520 000 KRW"),
    shareGap: m("520 000 KRW"),
    expensesPercent: "31,15",
    sentPercent: "46,35",
    fundPercent: "0",
    warnings: ["NO_SHARE"],
  },
  fund: {
    balance: m("6 000 000 KRW"),
    avgMonthly: m("520 000 KRW"),
    monthsUsed: 3,
    monthsUntilReturn: 13,
    balanceHome: m("54 600 000 soʻm", "5460000000", "UZS"),
    avgMonthlyHome: m("4 732 000 soʻm", "473200000", "UZS"),
    target: m("120 000 000 soʻm", "12000000000", "UZS"),
    remainingHome: m("65 400 000 soʻm", "6540000000", "UZS"),
    progressBp: 4550,
    progressPercent: "45,5",
    monthsToTarget: 14,
    projectedHome: m("116 116 000 soʻm", "11611600000", "UZS"),
    shortfallAtReturn: m("3 884 000 soʻm", "388400000", "UZS"),
    status: "BEHIND",
  },
  rate: { fromCurrency: "KRW", toCurrency: "UZS", rate: "9,1", rateOn: "2026-10-15", source: "Bank", stale: false, identity: false },
  entries: [{ id: "e1", kind: "SENT_HOME", amount: m("1 200 000 KRW"), fee: m("5 000 KRW"), received: m("10 900 000 soʻm", "1090000000", "UZS"), channel: null, categoryId: null, occurredOn: "2026-10-12", note: null }],
  ...over,
});

beforeEach(() => {
  [mfOverview, mfSetSettings, mfSetRate, mfRecordIncome, mfRecordMove, categories].forEach((f) => f.mockReset());
  categories.mockResolvedValue(ok([]));
  useUi.setState({ mfEntry: null });
});

describe("Musofir bosh sahifasi", () => {
  it("sozlanmagan: usta — valyuta, ulush (standart yadrodan), maqsad", async () => {
    mfOverview.mockResolvedValue(ok(overview({ settings: null, month: null, fund: null, rate: null, entries: [] })));
    mfSetSettings.mockResolvedValue(ok(overview()));
    const user = userEvent.setup();
    const { container } = wrap(<MfHomeScreen spaceId="mf" />);
    const form = await screen.findByRole("form", { name: "Musofir makonini sozlash" });
    expect(within(form).getByLabelText("Oʻz ulushi (%)")).toHaveValue("20");
    await user.selectOptions(within(form).getByLabelText("Ish valyutasi"), "RUB");
    await user.type(within(form).getByLabelText("Qaytish jamgʻarmasi maqsadi (soʻmda)"), "120 000 000");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(mfSetSettings).toHaveBeenCalledWith("mf", { country: null, workCurrency: "RUB", sharePercent: "20", target: "120 000 000", returnOn: null });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("ikki raqam, kurs bilan so'mdagi qiymat, prognoz va ogohlantirish", async () => {
    mfOverview.mockResolvedValue(ok(overview()));
    const { container } = wrap(<MfHomeScreen spaceId="mf" />);
    expect(await screen.findByTestId("mf-fund")).toHaveTextContent("6 000 000 KRW");
    expect(screen.getByTestId("mf-fund-home")).toHaveTextContent("54 600 000 soʻm");
    expect(screen.getByTestId("mf-fund-home")).toHaveTextContent("1 KRW = 9,1 UZS");
    expect(screen.getByTestId("mf-share-gap")).toHaveTextContent("520 000 KRW");
    expect(screen.getByTestId("mf-warning-NO_SHARE")).toHaveTextContent("avval oʻzingizga");
    expect(screen.getByTestId("mf-fund-status")).toHaveTextContent("3 884 000 soʻm yetmaydi");
    expect(screen.getByTestId("mf-sent")).toHaveTextContent("1 200 000 KRW");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "45");
    expect(screen.getByTestId("mf-entry")).toHaveTextContent("uyda 10 900 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("kurssiz — so'mdagi qiymat taxmin qilinmaydi", async () => {
    mfOverview.mockResolvedValue(ok(overview({ rate: null, fund: { ...overview().fund, balanceHome: null, status: "NO_RATE", projectedHome: null, shortfallAtReturn: null, remainingHome: null, progressBp: null } })));
    wrap(<MfHomeScreen spaceId="mf" />);
    expect(await screen.findByText(/Kurs kiritilmagan/)).toBeInTheDocument();
    expect(screen.queryByTestId("mf-fund-home")).not.toBeInTheDocument();
    expect(screen.getByTestId("mf-fund-status")).toHaveTextContent("kursni kiriting");
  });

  it("maosh → o'z ulushi taklifi → jamg'armaga (summa yadrodan)", async () => {
    mfOverview.mockResolvedValue(ok(overview()));
    mfRecordIncome.mockResolvedValue(ok({ overview: overview(), suggestedShare: m("520 000 KRW", "520000") }));
    mfRecordMove.mockResolvedValue(ok(overview()));
    const user = userEvent.setup();
    wrap(<MfHomeScreen spaceId="mf" />);
    await user.click(await screen.findByRole("button", { name: /^Maosh/ }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Summa (KRW)"), "2 600 000");
    await user.click(within(dialog).getByRole("button", { name: "Saqlash" }));
    expect(mfRecordIncome).toHaveBeenCalledWith("mf", { kind: "SALARY", amount: "2 600 000", channel: "CARD", occurredOn: null, note: null });
    expect(await screen.findByTestId("mf-offer")).toHaveTextContent("520 000 KRW");
    await user.click(screen.getByRole("button", { name: "Jamgʻarmaga qoʻyish" }));
    const fund = screen.getByRole("dialog");
    expect(within(fund).getByLabelText("Summa (KRW)")).toHaveValue("520 000");
    await user.click(within(fund).getByRole("button", { name: "Saqlash" }));
    expect(mfRecordMove).toHaveBeenCalledWith("mf", { kind: "FUND_IN", amount: "520 000", fee: null, received: null, occurredOn: null, note: null });
  });

  it("uyga yuborish: komissiya va uyda olingan summa", async () => {
    mfOverview.mockResolvedValue(ok(overview()));
    mfRecordMove.mockResolvedValue(ok(overview()));
    const user = userEvent.setup();
    wrap(<MfHomeScreen spaceId="mf" />);
    await user.click(await screen.findByRole("button", { name: "Uyga yuborish" }));
    const dialog = screen.getByRole("dialog");
    expect(await axeViolations(dialog)).toEqual([]);
    await user.type(within(dialog).getByLabelText("Summa (KRW)"), "1 200 000");
    await user.type(within(dialog).getByLabelText("Komissiya (KRW)"), "5 000");
    await user.type(within(dialog).getByLabelText("Uyda olingan summa (UZS)"), "10 900 000");
    await user.click(within(dialog).getByRole("button", { name: "Saqlash" }));
    expect(mfRecordMove).toHaveBeenCalledWith("mf", { kind: "SENT_HOME", amount: "1 200 000", fee: "5 000", received: "10 900 000", occurredOn: null, note: null });
  });

  it("kurs: «1 KRW necha UZS»", async () => {
    mfOverview.mockResolvedValue(ok(overview({ rate: null })));
    mfSetRate.mockResolvedValue(ok(overview()));
    const user = userEvent.setup();
    wrap(<MfHomeScreen spaceId="mf" />);
    const form = await screen.findByRole("form", { name: "Valyuta kursi" });
    await user.type(within(form).getByLabelText("1 KRW necha UZS"), "9,1");
    await user.click(within(form).getByRole("button", { name: "Kursni saqlash" }));
    expect(mfSetRate).toHaveBeenCalledWith("mf", { rate: "9,1", rateOn: null, source: null });
  });
});
