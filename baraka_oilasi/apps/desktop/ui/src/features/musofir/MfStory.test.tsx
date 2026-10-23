import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { DecisionDialog } from "./DecisionDialog";
import { ReturnCard } from "./ReturnCard";

const mfSetReturn = vi.fn();
const mfDecisions = vi.fn();
const mfDecisionQuestions = vi.fn();
const mfCheckDecision = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    mfSetReturn: (...a: unknown[]) => mfSetReturn(...a),
    mfDecisions: (...a: unknown[]) => mfDecisions(...a),
    mfDecisionQuestions: (...a: unknown[]) => mfDecisionQuestions(...a),
    mfCheckDecision: (...a: unknown[]) => mfCheckDecision(...a),
    mfRecordDecision: vi.fn(),
    mfSetOutcome: vi.fn(),
  },
}));

const m = (formatted: string, minor = "1", currency = "UZS") => ({ minor, currency, formatted, plain: formatted.replace(/ (soʻm|USD)$/, "").replace(/ /g, "") });
const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const overview = (cooling: unknown) =>
  ({
    settings: null,
    defaultSharePercent: "20",
    periodStart: "2026-11-01",
    periodEnd: "2026-11-30",
    month: null,
    fund: null,
    rate: null,
    entries: [],
    cooling,
    reserve: null,
    startup: null,
  }) as never;

beforeEach(() => {
  [mfSetReturn, mfDecisions, mfDecisionQuestions, mfCheckDecision].forEach((f) => f.mockReset());
  mfDecisions.mockResolvedValue(ok([]));
});

describe("Qaytish xavfsizligi: dollar, qal'a devori", () => {
  it("«Qaytdim» dollarda — kurs so'raladi", async () => {
    mfSetReturn.mockResolvedValue(ok(overview(null)));
    const user = userEvent.setup();
    wrap(<ReturnCard spaceId="mf" d={overview(null)} homeCurrency="UZS" />);
    await user.click(screen.getByRole("button", { name: "Qaytdim" }));
    const form = screen.getByRole("form", { name: "Qaytish" });
    expect(within(form).queryByLabelText("1 USD necha UZS")).not.toBeInTheDocument();
    await user.type(within(form).getByLabelText("Qaytgan sana"), "2026-11-17");
    await user.selectOptions(within(form).getByLabelText("Valyuta"), "USD");
    await user.type(within(form).getByLabelText("Olib kelingan summa (USD)"), "18 000");
    await user.type(within(form).getByLabelText("1 USD necha UZS"), "12 650");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(mfSetReturn).toHaveBeenCalledWith("mf", { returnedOn: "2026-11-17", broughtHome: "18 000", broughtCurrency: "USD", broughtRate: "12 650" });
  });

  it("qal'a devori va erkin pul — yadrodan", async () => {
    const cooling = {
      returnedOn: "2026-11-17",
      broughtHome: m("18 000 USD", "1800000", "USD"),
      broughtValue: m("227 700 000 soʻm", "22770000000"),
      broughtRate: "12 650",
      wall: m("48 000 000 soʻm", "4800000000"),
      wallAvgMonthly: m("8 000 000 soʻm", "800000000"),
      wallMonthsUsed: 1,
      free: m("179 700 000 soʻm", "17970000000"),
      inCooling: true,
      endsOn: "2027-02-15",
      daysLeft: 87,
    };
    const { container } = wrap(<ReturnCard spaceId="mf" d={overview(cooling)} homeCurrency="UZS" />);
    expect(screen.getByText(/≈ 227 700 000 soʻm \(12 650 kurs bilan\)/)).toBeInTheDocument();
    expect(screen.getByTestId("mf-wall")).toHaveTextContent("6 oylik roʻzgʻori: 48 000 000 soʻm");
    expect(screen.getByTestId("mf-wall")).toHaveTextContent("Erkin pul (savdo, sheriklik va xaridlar uchun): 179 700 000 soʻm");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("«Oltin foyda»: va'da hisobi, besh belgidan to'rttasi, qal'a devori bayrog'i", async () => {
    mfDecisionQuestions.mockResolvedValue(ok(["guaranteed", "exitEasy"]));
    mfCheckDecision.mockResolvedValue(
      ok({
        questions: ["guaranteed", "exitEasy"],
        inCooling: true,
        endsOn: "2027-02-15",
        daysLeft: 87,
        sharePercent: "55,56",
        flags: [
          { code: "GUARANTEED_PROFIT", level: "RED" },
          { code: "EXIT_HARD", level: "RED" },
          { code: "TWO_SIGNS", level: "RED" },
          { code: "FORTRESS_WALL", level: "RED" },
        ],
        verdict: "RED",
        waitUntil: "2027-02-15",
        signs: 4,
        free: m("179 700 000 soʻm", "17970000000"),
        promisedYearlyPercent: "420",
        promisedTimes: "5,2",
      }),
    );
    const user = userEvent.setup();
    const { container } = wrap(<DecisionDialog spaceId="mf" homeCurrency="UZS" onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Qaror turi"), "INVEST");
    await user.type(within(dialog).getByLabelText("Summa (UZS)"), "126 500 000");
    await user.type(within(dialog).getByLabelText("Oyiga vaʼda qilingan foyda, % (boʻlsa)"), "35");
    await user.type(within(dialog).getByLabelText("Nima haqida"), "Oltin foyda");
    await user.click(within(await within(dialog).findByRole("radiogroup", { name: /kafolatlanyaptimi/ })).getByRole("radio", { name: "Ha" }));
    await user.click(within(within(dialog).getByRole("radiogroup", { name: /qaytarib olish/ })).getByRole("radio", { name: "Yoʻq" }));
    await user.click(within(dialog).getByRole("button", { name: "Tekshirish" }));
    expect(mfCheckDecision).toHaveBeenCalledWith("mf", expect.objectContaining({ kind: "INVEST", promisedPercent: "35" }));
    const result = await within(dialog).findByTestId("mf-decision-result");
    expect(result).toHaveTextContent("Besh xavf belgisidan topildi: 4");
    expect(result).toHaveTextContent("ikkitasi — bu taklifdan voz kechishga yetarli sabab");
    expect(result).toHaveTextContent("Kirish oson, chiqish qiyin");
    expect(result).toHaveTextContent("erkin pul — 179 700 000 soʻm");
    expect(screen.getByTestId("mf-decision-promise")).toHaveTextContent("oyiga 35 % — bir yilda 420 %, pulingiz 5,2 barobar");
    expect(await axeViolations(container)).toEqual([]);
  });
});
