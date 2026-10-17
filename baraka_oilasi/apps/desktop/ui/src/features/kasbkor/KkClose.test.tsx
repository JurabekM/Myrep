import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { KkCloseScreen } from "./KkCloseScreen";

const kkCloseDraft = vi.fn();
const kkCloseRules = vi.fn();
const kkSetCloseRules = vi.fn();
const kkCloseMonth = vi.fn();
const kkMonthCloses = vi.fn();
const exportKkMonthClose = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    kkCloseDraft: (...a: unknown[]) => kkCloseDraft(...a),
    kkCloseRules: (...a: unknown[]) => kkCloseRules(...a),
    kkSetCloseRules: (...a: unknown[]) => kkSetCloseRules(...a),
    kkCloseMonth: (...a: unknown[]) => kkCloseMonth(...a),
    kkMonthCloses: (...a: unknown[]) => kkMonthCloses(...a),
    exportKkMonthClose: (...a: unknown[]) => exportKkMonthClose(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(" soʻm", "") });
const ok = (data: unknown) => ({ status: "ok", data });

const rules = { taxBase: "REVENUE", taxPercent: "4", taxFixed: null, reservePercent: "30", workingPercent: "50", expansionPercent: "20", sadaqaPercent: "0" };
// kasbkor/SPEC 4.5 Nilufar.
const draft = {
  periodStart: "2026-11-01",
  periodEnd: "2026-11-30",
  revenue: m("18 000 000 soʻm"),
  expenses: m("9 700 000 soʻm"),
  depreciation: m("200 000 soʻm"),
  trueProfit: m("3 100 000 soʻm"),
  ownerSalary: m("5 000 000 soʻm"),
  ownerPaid: m("5 000 000 soʻm"),
  salaryRemaining: m("0 soʻm", "0"),
  rules,
  tax: m("720 000 soʻm"),
  ownerPay: m("5 000 000 soʻm"),
  overdrawn: null,
  remaining: m("2 580 000 soʻm"),
  needsExplanation: false,
  allocation: { reserve: m("774 000 soʻm"), working: m("1 290 000 soʻm"), expansion: m("516 000 soʻm"), sadaqa: m("0 soʻm", "0") },
  reserveBelowDepreciation: false,
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: Hisob kuni (K3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    kkCloseRules.mockResolvedValue(ok(rules));
    kkCloseDraft.mockResolvedValue(ok(draft));
    kkMonthCloses.mockResolvedValue(ok([]));
  });

  it("qoralama: soliq, maosh, qolgan pul va taqsimot yadrodan; yopish; axe toza", async () => {
    kkCloseMonth.mockResolvedValue(ok({ id: "c1", closedAt: "2026-12-03T05:00:00Z", summary: draft, carryForward: m("0 soʻm", "0"), explanation: null, shortCode: "A226-B35D-44AC-EAF8" }));
    const user = userEvent.setup();
    const { container } = wrap(<KkCloseScreen spaceId="s-kk" />);
    expect(await screen.findByTestId("kk-close-remaining")).toHaveTextContent("2 580 000 soʻm");
    expect(screen.getByTestId("kk-close-tax")).toHaveTextContent("− 720 000 soʻm");
    expect(screen.getByTestId("kk-close-reserve")).toHaveTextContent("774 000 soʻm");
    expect(screen.getByTestId("kk-close-working")).toHaveTextContent("1 290 000 soʻm");
    expect(screen.getByText(/Soliq zaxirasi: tushumdan 4 %/)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Oyni yopish" }));
    expect(kkCloseMonth).toHaveBeenCalledWith("s-kk", { periodStart: "2026-11-01", carryOverdraw: false, explanation: null });
  });

  it("qolgan manfiy: izoh maydoni; maoshdan ortig'ini o'tkazish belgisi", async () => {
    kkCloseDraft.mockResolvedValue(
      ok({ ...draft, remaining: m("-500 000 soʻm"), needsExplanation: true, allocation: null, overdrawn: m("1 500 000 soʻm") }),
    );
    kkCloseMonth.mockResolvedValue({ status: "error", error: { code: "REQUIRED", field: "explanation" } });
    const user = userEvent.setup();
    const { container } = wrap(<KkCloseScreen spaceId="s-kk" />);
    const why = await screen.findByLabelText("Nima boʻldi?");
    expect(screen.queryByTestId("kk-close-reserve")).toBeNull();
    await user.click(screen.getByLabelText("Maoshdan 1 500 000 soʻm ortiq olindi. Keyingi oy maoshidan ushlab qolinsin."));
    await user.type(why, "Toʻy");
    await user.click(screen.getByRole("button", { name: "Oyni yopish" }));
    expect(kkCloseMonth).toHaveBeenCalledWith("s-kk", { periodStart: "2026-11-01", carryOverdraw: true, explanation: "Toʻy" });
    expect(await screen.findByRole("alert")).toHaveTextContent("Bu maydonni toʻldiring");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("qoidalar: foizlar matn holida, jami 100 % bo'lmasa — yadro xatosi", async () => {
    kkSetCloseRules.mockResolvedValue({ status: "error", error: { code: "INVALID_RULE", field: "rule" } });
    const user = userEvent.setup();
    wrap(<KkCloseScreen spaceId="s-kk" />);
    await user.click(await screen.findByRole("button", { name: "Oʻzgartirish" }));
    const form = screen.getByRole("form", { name: "Qoidalarni oʻzgartirish" });
    await user.click(within(form).getByLabelText("Foydadan foiz"));
    await user.clear(within(form).getByLabelText("Foiz (%)"));
    await user.type(within(form).getByLabelText("Foiz (%)"), "2,5");
    await user.clear(within(form).getByLabelText("Sadaqa (%)"));
    await user.type(within(form).getByLabelText("Sadaqa (%)"), "5");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(kkSetCloseRules).toHaveBeenCalledWith("s-kk", {
      taxBase: "PROFIT",
      taxPercent: "2,5",
      taxFixed: null,
      reservePercent: "30",
      workingPercent: "50",
      expansionPercent: "20",
      sadaqaPercent: "5",
    });
    expect(await within(form).findByRole("alert")).toHaveTextContent("jami 100 %");
  });

  it("o'tgan oy yopilgan: holat matni va bayonnoma PDF", async () => {
    kkCloseDraft.mockResolvedValue({ status: "error", error: { code: "ALREADY_CLOSED", field: "periodStart" } });
    kkMonthCloses.mockResolvedValue(ok([{ id: "c1", closedAt: "2026-12-03T05:00:00Z", summary: draft, carryForward: m("0 soʻm", "0"), explanation: null, shortCode: "A226-B35D-44AC-EAF8" }]));
    exportKkMonthClose.mockResolvedValue(ok(true));
    const user = userEvent.setup();
    const { container } = wrap(<KkCloseScreen spaceId="s-kk" />);
    expect(await screen.findByRole("status")).toHaveTextContent("Oʻtgan oy yopilgan");
    expect(await screen.findByText("A226-B35D-44AC-EAF8")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "PDF saqlash: 01.11.2026 – 30.11.2026" }));
    expect(exportKkMonthClose).toHaveBeenCalledWith("s-kk", "c1");
    expect(await axeViolations(container)).toEqual([]);
  });
});
