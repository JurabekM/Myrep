import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { axeViolations } from "../../test/axe";
import { ReturnCard } from "./ReturnCard";
import { TravelDebtCard } from "./TravelDebtCard";

const mfTravelDebt = vi.fn();
const mfSetTravelDebt = vi.fn();
const mfSetReturn = vi.fn();
const mfDecisions = vi.fn();
const mfDecisionQuestions = vi.fn();
const mfCheckDecision = vi.fn();
const mfRecordDecision = vi.fn();

vi.mock("../../bindings", () => ({
  commands: {
    mfTravelDebt: (...a: unknown[]) => mfTravelDebt(...a),
    mfSetTravelDebt: (...a: unknown[]) => mfSetTravelDebt(...a),
    mfSetReturn: (...a: unknown[]) => mfSetReturn(...a),
    mfDecisions: (...a: unknown[]) => mfDecisions(...a),
    mfDecisionQuestions: (...a: unknown[]) => mfDecisionQuestions(...a),
    mfCheckDecision: (...a: unknown[]) => mfCheckDecision(...a),
    mfRecordDecision: (...a: unknown[]) => mfRecordDecision(...a),
  },
}));

const u = (formatted: string, minor = "1") => ({ minor, currency: "UZS", formatted, plain: formatted.replace(/ soʻm$/, "").replace(/ /g, "") });
const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const debt = { id: "d1", creditor: "Togʻam", reason: "Koreyaga yoʻl va viza", status: "ACTIVE", outstanding: u("11 730 000 soʻm", "1173000000") };
const plan = {
  remaining: u("11 730 000 soʻm", "1173000000"),
  available: u("0 soʻm", "0"),
  avgMonthly: u("3 270 000 soʻm", "327000000"),
  monthsUsed: 1,
  monthsToClear: 4,
  clearOn: "2027-03-10",
  requiredMonthly: u("1 955 000 soʻm", "195500000"),
  status: "ON_TRACK",
};
const LEND = ["approached", "upfront", "abroadJobFee", "repaymentDate", "familyDiscussed"];

const overview = (cooling: unknown) => ({
  settings: null,
  defaultSharePercent: "20",
  periodStart: "2026-11-01",
  periodEnd: "2026-11-30",
  month: null,
  fund: null,
  rate: null,
  entries: [],
  cooling,
});

beforeEach(() => {
  [mfTravelDebt, mfSetTravelDebt, mfSetReturn, mfDecisions, mfDecisionQuestions, mfCheckDecision, mfRecordDecision].forEach((f) => f.mockReset());
  mfDecisions.mockResolvedValue(ok([]));
  mfDecisionQuestions.mockResolvedValue(ok(LEND));
});

describe("Yo'l qarzi", () => {
  it("belgilanmagan: Uy qarzlaridan tanlash va 6 oylik maqsad", async () => {
    mfTravelDebt.mockResolvedValue(ok({ debt: null, targetMonths: 6, candidates: [debt], plan: null }));
    mfSetTravelDebt.mockResolvedValue(ok({ debt, targetMonths: 6, candidates: [debt], plan }));
    const user = userEvent.setup();
    const { container } = wrap(<TravelDebtCard spaceId="mf" />);
    await user.click(await screen.findByRole("button", { name: "Yoʻl qarzini belgilash" }));
    const form = screen.getByRole("form", { name: "Yoʻl qarzi sozlamasi" });
    expect(within(form).getByLabelText("Necha oyda yopmoqchisiz")).toHaveValue(6);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(mfSetTravelDebt).toHaveBeenCalledWith("mf", { debtId: "d1", targetMonths: 6 });
  });

  it("reja: necha oyda yopiladi va oyiga qancha kerak (yadrodan)", async () => {
    mfTravelDebt.mockResolvedValue(ok({ debt, targetMonths: 6, candidates: [debt], plan }));
    const { container } = wrap(<TravelDebtCard spaceId="mf" />);
    expect(await screen.findByTestId("mf-travel-status")).toHaveTextContent("4 oyda (10.03.2027) yopiladi");
    expect(screen.getByTestId("mf-travel-remaining")).toHaveTextContent("11 730 000 soʻm");
    expect(screen.getByText("1 955 000 soʻm")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("Uyda qarz yo'q — avval «Qarzlar»da yozishga yo'naltiradi", async () => {
    mfTravelDebt.mockResolvedValue(ok({ debt: null, targetMonths: 6, candidates: [], plan: null }));
    wrap(<TravelDebtCard spaceId="mf" />);
    expect(await screen.findByText(/Avval Uy makonidagi «Qarzlar»da/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Yoʻl qarzini belgilash" })).not.toBeInTheDocument();
  });
});

describe("Qaytdim va sovutish davri", () => {
  it("«Qaytdim»: sana va olib kelingan summa", async () => {
    mfSetReturn.mockResolvedValue(ok(overview(null)));
    const user = userEvent.setup();
    wrap(<ReturnCard spaceId="mf" d={overview(null) as never} homeCurrency="UZS" />);
    await user.click(screen.getByRole("button", { name: "Qaytdim" }));
    const form = screen.getByRole("form", { name: "Qaytish" });
    await user.type(within(form).getByLabelText("Qaytgan sana"), "2026-11-01");
    await user.type(within(form).getByLabelText("Olib kelingan summa (UZS)"), "120 000 000");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(mfSetReturn).toHaveBeenCalledWith("mf", { returnedOn: "2026-11-01", broughtHome: "120 000 000", broughtCurrency: "UZS", broughtRate: null });
  });

  it("katta qaror: savollar → sariq natija → «Kutaman» jurnalga", async () => {
    const cooling = { returnedOn: "2026-11-01", broughtHome: u("120 000 000 soʻm", "12000000000"), inCooling: true, endsOn: "2027-01-30", daysLeft: 81 };
    mfCheckDecision.mockResolvedValue(
      ok({
        questions: LEND,
        inCooling: true,
        endsOn: "2027-01-30",
        daysLeft: 81,
        sharePercent: "12,5",
        flags: [
          { code: "FRESH_RETURN_APPROACH", level: "YELLOW" },
          { code: "NO_REPAYMENT_DATE", level: "YELLOW" },
          { code: "COOLING_BIG_DECISION", level: "YELLOW" },
        ],
        verdict: "YELLOW",
        waitUntil: "2027-01-30",
      }),
    );
    mfRecordDecision.mockResolvedValue(ok([]));
    const user = userEvent.setup();
    const { container } = wrap(<ReturnCard spaceId="mf" d={overview(cooling) as never} homeCurrency="UZS" />);
    expect(screen.getByTestId("mf-cooling")).toHaveTextContent("yana 81 kun (30.01.2027 gacha)");
    await user.click(screen.getByRole("button", { name: "Katta qarorni tekshirish" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Nima haqida"), "Togʻamga qarz");
    await user.type(within(dialog).getByLabelText("Summa (UZS)"), "15 000 000");
    const replies: Record<string, string> = { approached: "Ha", upfront: "Yoʻq", abroadJobFee: "Yoʻq", repaymentDate: "Yoʻq", familyDiscussed: "Ha" };
    for (const q of LEND) {
      const group = await within(dialog).findByRole("radiogroup", { name: new RegExp(q === "approached" ? "qaytganingizdan keyin" : q === "upfront" ? "Avval pul" : q === "abroadJobFee" ? "Chet elga" : q === "repaymentDate" ? "Qaytarish muddati" : "Oila bilan") });
      await user.click(within(group).getByRole("radio", { name: replies[q] }));
    }
    await user.click(within(dialog).getByRole("button", { name: "Tekshirish" }));
    const result = await within(dialog).findByTestId("mf-decision-result");
    expect(result).toHaveTextContent("Sariq: kuting va aniqlang");
    expect(result).toHaveTextContent("olib kelinganning 12,5 %i");
    expect(result).toHaveTextContent("Kutish sanasi: 30.01.2027");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(result).getByRole("button", { name: "Kutaman" }));
    expect(mfRecordDecision).toHaveBeenCalledWith("mf", {
      kind: "LEND",
      title: "Togʻamga qarz",
      amount: "15 000 000",
      answers: [
        { key: "approached", reply: "YES" },
        { key: "upfront", reply: "NO" },
        { key: "abroadJobFee", reply: "NO" },
        { key: "repaymentDate", reply: "NO" },
        { key: "familyDiscussed", reply: "YES" },
      ],
      choice: "WAIT",
      note: null,
      promisedPercent: null,
    });
  });
});
