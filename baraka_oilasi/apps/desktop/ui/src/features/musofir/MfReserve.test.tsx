import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { ReserveCard } from "./ReserveCard";
import { ReturnCard } from "./ReturnCard";
import { StartupCard } from "./StartupCard";

const mfSetPlan = vi.fn();
const household = vi.fn();
const ventureIdeas = vi.fn();
const mfDecisions = vi.fn();
const mfSetOutcome = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    mfSetPlan: (...a: unknown[]) => mfSetPlan(...a),
    household: (...a: unknown[]) => household(...a),
    ventureIdeas: (...a: unknown[]) => ventureIdeas(...a),
    mfDecisions: (...a: unknown[]) => mfDecisions(...a),
    mfSetOutcome: (...a: unknown[]) => mfSetOutcome(...a),
    mfSetReturn: vi.fn(),
  },
}));

const m = (formatted: string, minor = "1", currency = "KRW") => ({ minor, currency, formatted, plain: formatted.replace(/ (soʻm|KRW)$/, "").replace(/ /g, "") });
const u = (formatted: string, minor = "1") => m(formatted, minor, "UZS");
const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const reserve = {
  balance: m("800 000 KRW", "800000"),
  months: 1,
  monthsUsed: 3,
  avgMonthly: m("805 000 KRW", "805000"),
  target: m("805 000 KRW", "805000"),
  gap: m("5 000 KRW", "5000"),
  progressBp: 9938,
  progressPercent: "99,38",
  status: "PARTIAL",
};
const overview = (over: Record<string, unknown> = {}) =>
  ({
    settings: null,
    defaultSharePercent: "20",
    periodStart: "2026-10-01",
    periodEnd: "2026-10-31",
    month: null,
    fund: null,
    rate: null,
    entries: [],
    cooling: null,
    reserve,
    startup: null,
    ...over,
  }) as never;

beforeEach(() => {
  [mfSetPlan, household, ventureIdeas, mfDecisions, mfSetOutcome].forEach((f) => f.mockReset());
  household.mockResolvedValue(ok({ id: "h", name: "Oila", locale: "uz", baseCurrency: "UZS", monthStartDay: 1, members: [], spaces: [{ id: "uy", kind: "UY" }, { id: "mf", kind: "MUSOFIR" }] }));
  mfDecisions.mockResolvedValue(ok([]));
});

describe("Qorovul pul", () => {
  it("holat, to'lishi va oylar soni (ish boshlash summasi saqlanadi)", async () => {
    mfSetPlan.mockResolvedValue(ok(overview()));
    const onAction = vi.fn();
    const user = userEvent.setup();
    const d = overview({ startup: { startup: u("30 000 000 soʻm", "3000000000"), living: null, startupPercent: null, exceedsTarget: false, ideaId: "i1", ideaTitle: "Tikuv sexi" } });
    const { container } = wrap(<ReserveCard spaceId="mf" d={d} r={reserve} onAction={onAction} />);
    expect(screen.getByTestId("mf-reserve")).toHaveTextContent("800 000 KRW");
    expect(screen.getByTestId("mf-reserve-status")).toHaveTextContent("Yana 5 000 KRW");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "99");
    expect(screen.getByText(/805 000 KRW \(3 oy\)/)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
    await user.selectOptions(screen.getByLabelText("Necha oylik xarajat"), "2");
    expect(mfSetPlan).toHaveBeenCalledWith("mf", { reserveMonths: 2, startup: "30000000", startupIdeaId: "i1" });
    await user.click(screen.getByRole("button", { name: "Qorovul puldan" }));
    expect(onAction).toHaveBeenCalledWith("RESERVE_OUT");
  });
});

describe("Ish boshlash summasi", () => {
  it("«Hunardan ishga» g'oyasi tanlansa — sarmoyasi taklif qilinadi", async () => {
    ventureIdeas.mockResolvedValue(ok([{ id: "i1", title: "Tikuv sexi", capex: u("30 000 000 soʻm", "3000000000") }]));
    mfSetPlan.mockResolvedValue(ok(overview()));
    const user = userEvent.setup();
    const { container } = wrap(<StartupCard spaceId="mf" d={overview()} homeCurrency="UZS" />);
    await user.click(await screen.findByRole("button", { name: "Ish boshlash summasini belgilash" }));
    const form = screen.getByRole("form", { name: "Ish boshlash summasi" });
    await within(form).findByRole("option", { name: "Tikuv sexi · 30 000 000 soʻm" });
    await user.selectOptions(within(form).getByLabelText("«Hunardan ishga» gʻoyasi"), "i1");
    expect(within(form).getByLabelText("Ish boshlash summasi (UZS)")).toHaveValue("30000000");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(mfSetPlan).toHaveBeenCalledWith("mf", { reserveMonths: 1, startup: "30000000", startupIdeaId: "i1" });
  });

  it("belgilangan: yashash uchun qolgani yadrodan", () => {
    const d = overview({ startup: { startup: u("30 000 000 soʻm"), living: u("90 000 000 soʻm"), startupPercent: "25", exceedsTarget: false, ideaId: "i1", ideaTitle: "Tikuv sexi" } });
    wrap(<StartupCard spaceId="mf" d={d} homeCurrency="UZS" />);
    expect(screen.getByTestId("mf-startup")).toHaveTextContent("Ish boshlash uchun: 30 000 000 soʻm · Tikuv sexi");
    expect(screen.getByTestId("mf-startup")).toHaveTextContent("Yashash uchun: 90 000 000 soʻm (ish boshlash — maqsadning 25 %i)");
  });
});

describe("Qaror natijasi", () => {
  const decision = (outcome: unknown) => ({
    id: "d1",
    decidedOn: "2026-10-18",
    kind: "LEND",
    title: "Doʻstga qarz",
    amount: u("5 000 000 soʻm"),
    answers: [],
    flags: [],
    verdict: "YELLOW",
    inCooling: false,
    waitUntil: null,
    choice: "WAIT",
    note: null,
    outcome,
  });

  it("bir marta: «Qilmadim»", async () => {
    mfDecisions.mockResolvedValue(ok([decision(null)]));
    mfSetOutcome.mockResolvedValue(ok([]));
    const user = userEvent.setup();
    const { container } = wrap(<ReturnCard spaceId="mf" d={overview()} homeCurrency="UZS" />);
    const group = await screen.findByRole("group", { name: "Natija qanday boʻldi?" });
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(group).getByRole("button", { name: "Qilmadim" }));
    expect(mfSetOutcome).toHaveBeenCalledWith("mf", "d1", { outcome: "DROPPED", outcomeOn: null, note: null });
  });

  it("belgilangan natija — tugmalarsiz", async () => {
    mfDecisions.mockResolvedValue(ok([decision({ outcome: "DONE", outcomeOn: "2026-10-20", note: null })]));
    wrap(<ReturnCard spaceId="mf" d={overview()} homeCurrency="UZS" />);
    expect(await screen.findByTestId("mf-decision-outcome")).toHaveTextContent("Natija: qildim (20.10.2026)");
    expect(screen.queryByRole("group", { name: "Natija qanday boʻldi?" })).not.toBeInTheDocument();
  });
});
