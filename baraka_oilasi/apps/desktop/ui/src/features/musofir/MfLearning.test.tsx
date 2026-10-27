import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { useUi } from "../../state/ui";
import { axeViolations } from "../../test/axe";
import { OfferCheckDialog } from "../venture/OfferCheckDialog";
import { MfLearningScreen } from "./MfLearningScreen";

const mfLearningOverview = vi.fn();
const mfHourSuggest = vi.fn();
const mfHourSave = vi.fn();
const mfLearningPlanCreate = vi.fn();
const mfLearningPlanSetStatus = vi.fn();
const mfLearningPlanResult = vi.fn();
const mfTeachingAdd = vi.fn();
const checkCourse = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    mfLearningOverview: (...a: unknown[]) => mfLearningOverview(...a),
    mfHourSuggest: (...a: unknown[]) => mfHourSuggest(...a),
    mfHourSave: (...a: unknown[]) => mfHourSave(...a),
    mfLearningPlanCreate: (...a: unknown[]) => mfLearningPlanCreate(...a),
    mfLearningPlanSetStatus: (...a: unknown[]) => mfLearningPlanSetStatus(...a),
    mfLearningPlanResult: (...a: unknown[]) => mfLearningPlanResult(...a),
    mfTeachingAdd: (...a: unknown[]) => mfTeachingAdd(...a),
    checkCourse: (...a: unknown[]) => checkCourse(...a),
    checkOffer: vi.fn(),
  },
}));

const m = (formatted: string, minor = "1", currency = "KRW") => ({ minor, currency, formatted, plain: formatted.replace(/ (soʻm|KRW)$/, "").replace(/ /g, "") });
const s = (formatted: string, minor = "1") => m(formatted, minor, "UZS");
const ok = (data: unknown) => ({ status: "ok", data });
const fail = (code: string, field: string | null = null) => ({ status: "error", error: { code, field, message: code } });

const rate = { fromCurrency: "KRW", toCurrency: "UZS", rate: "9,1", rateOn: "2026-10-15", source: "Bank", stale: false, identity: false };
// musofir/SPEC 6A (Bobur aka): 2 650 000 von / 220 soat = 12 045 von; 1 KRW = 9,1 soʻm → 109 609,50 soʻm.
const hour = (home: Record<string, unknown> = {}) => ({
  id: "h1",
  income: m("2 650 000 KRW", "2650000"),
  incomeSource: "AUTO",
  months: 3,
  minutesPerDay: 600,
  days: 22,
  monthlyMinutes: 13200,
  hourValue: m("12 045 KRW", "12045"),
  doubleTarget: m("24 090 KRW", "24090"),
  overCeiling: false,
  computedOn: "2026-10-20",
  home: { rateStatus: "FRESH", hourValue: s("109 609,50 soʻm", "10960950"), doubleTarget: s("219 219 soʻm", "21921900"), rate, ...home },
});
const plan = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  goal: "ABROAD",
  skill: "Ish joyidagi koreys tili",
  purpose: null,
  paths: ["BOOK", "COURSE"],
  budget: m("300 000 KRW", "300000"),
  weeklyMinutes: 240,
  startOn: "2026-10-20",
  reviewOn: "2027-01-20",
  status: "ACTIVE",
  baselineHourValue: m("12 045 KRW", "12045"),
  resultHourValue: null,
  ventureIdeaId: null,
  ventureIdeaTitle: null,
  courseCheckSuggested: true,
  reviewDue: false,
  ...over,
});
const overview = (over: Record<string, unknown> = {}) => ({
  periodStart: "2026-10-01",
  periodEnd: "2026-10-31",
  workCurrency: "KRW",
  homeCurrency: "UZS",
  hourValue: hour(),
  plans: [plan(), plan({ id: "p2", goal: "HOME", skill: "Payvandlash", paths: ["MENTOR"], courseCheckSuggested: false, ventureIdeaId: "i1", ventureIdeaTitle: "Payvandlash ustaxonasi", budget: null })],
  activePlans: 2,
  ideas: [{ id: "i1", title: "Payvandlash ustaxonasi" }],
  startupIdeaId: "i1",
  teachingCount: 1,
  teaching: [{ id: "t1", occurredOn: "2026-10-18", area: "DOCUMENTS", learner: "Yangi kelgan hamyurt", topic: "Yashash kartasi hujjatlari", minutes: 60 }],
  selfInvestment: { total: m("135 000 KRW", "135000"), income: m("2 700 000 KRW", "2700000"), shareBp: 500, sharePercent: "5" },
  ...over,
});

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  [mfLearningOverview, mfHourSuggest, mfHourSave, mfLearningPlanCreate, mfLearningPlanSetStatus, mfLearningPlanResult, mfTeachingAdd, checkCourse].forEach((f) => f.mockReset());
  mfHourSuggest.mockResolvedValue(
    ok({
      months: [
        { periodStart: "2026-09-01", periodEnd: "2026-09-30", total: m("2 600 000 KRW", "2600000") },
        { periodStart: "2026-08-01", periodEnd: "2026-08-31", total: m("2 750 000 KRW", "2750000") },
      ],
      average: m("2 675 000 KRW", "2675000"),
    }),
  );
  useUi.setState({ offerOpen: false, offerMode: "OFFER" });
});

describe("Musofir «Oʻzimga sarmoya»", () => {
  it("soat qiymati vonda va kurs bilan soʻmda; ikki maqsadli rejalar; sarmoya qatori", async () => {
    mfLearningOverview.mockResolvedValue(ok(overview()));
    const { container } = wrap(<MfLearningScreen spaceId="mf" />);
    expect(await screen.findByTestId("mfl-hour-value")).toHaveTextContent("12 045 KRW");
    expect(screen.getByTestId("mfl-hour-double")).toHaveTextContent("24 090 KRW");
    const home = screen.getByTestId("mfl-hour-home");
    expect(home).toHaveTextContent("≈ 109 609,50 soʻm / soat");
    expect(home).toHaveTextContent("1 KRW = 9,1 UZS");
    expect(screen.getByText(/oxirgi oylar oʻrtachasi \(3 oy\)/)).toBeInTheDocument();
    expect(await screen.findByTestId("mfl-months")).toHaveTextContent("2 750 000 KRW");
    expect(screen.getByTestId("mfl-self-investment")).toHaveTextContent("135 000 KRW — daromadning 5 %");
    const abroad = screen.getByTestId("mfl-plan-p1");
    expect(within(abroad).getByTestId("mfl-plan-goal")).toHaveTextContent("Chet elda");
    expect(abroad).toHaveTextContent("Byudjet: 300 000 KRW");
    const homePlan = screen.getByTestId("mfl-plan-p2");
    expect(within(homePlan).getByTestId("mfl-plan-goal")).toHaveTextContent("Uyda");
    expect(within(homePlan).getByTestId("mfl-plan-idea")).toHaveTextContent("Payvandlash ustaxonasi");
    expect(screen.getByTestId("mfl-teach-count")).toHaveTextContent("1 marta");
    expect(screen.getByText("Hujjatlar")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("kurs yo'q — soʻmdagi qiymat koʻrsatilmaydi; eski kurs — ogohlantirish", async () => {
    mfLearningOverview.mockResolvedValue(ok(overview({ hourValue: hour({ rateStatus: "NO_RATE", hourValue: null, doubleTarget: null, rate: null }) })));
    const { unmount } = wrap(<MfLearningScreen spaceId="mf" />);
    const home = await screen.findByTestId("mfl-hour-home");
    expect(home).toHaveAttribute("data-status", "NO_RATE");
    expect(home).toHaveTextContent("Kurs kiritilmagan");
    expect(home).not.toHaveTextContent("soʻm /");
    unmount();
    mfLearningOverview.mockResolvedValue(ok(overview({ hourValue: hour({ rateStatus: "STALE", rate: { ...rate, stale: true } }) })));
    wrap(<MfLearningScreen spaceId="mf" />);
    const stale = await screen.findByTestId("mfl-hour-home");
    expect(stale).toHaveTextContent("≈ 109 609,50 soʻm");
    expect(stale).toHaveTextContent("30 kundan eski");
  });

  it("soat qiymatini saqlash: bo'sh daromad — avtomatik, vaqt daqiqada", async () => {
    mfLearningOverview.mockResolvedValue(ok(overview({ hourValue: null })));
    mfHourSave.mockResolvedValue(ok(hour()));
    const user = userEvent.setup();
    wrap(<MfLearningScreen spaceId="mf" />);
    const card = await screen.findByTestId("mfl-hour");
    expect(card).toHaveTextContent("Hali hisoblanmagan");
    expect(within(card).getByLabelText("Oylik daromad, KRW (boʻsh — avtomatik)")).toHaveValue("");
    await user.click(within(card).getByRole("button", { name: "Hisoblash va saqlash" }));
    expect(mfHourSave).toHaveBeenCalledWith("mf", { income: null, minutesPerDay: 600, days: 22 });
  });

  it("yangi reja: uyda — g'oya standart tanlangan; chet elda — g'oya yuborilmaydi; chegara xatosi", async () => {
    mfLearningOverview.mockResolvedValue(ok(overview({ plans: [] })));
    mfLearningPlanCreate.mockResolvedValueOnce(ok(plan())).mockResolvedValueOnce(fail("ACTIVE_PLAN_LIMIT"));
    const user = userEvent.setup();
    wrap(<MfLearningScreen spaceId="mf" />);
    await user.click(await screen.findByRole("button", { name: "Yangi reja" }));
    let dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("radio", { name: /uyda daromad beradigan hunar/ }));
    expect(within(dialog).getByLabelText("«Hunardan ishga» gʻoyasi (ixtiyoriy)")).toHaveValue("i1");
    await user.type(within(dialog).getByLabelText("Koʻnikma"), "Payvandlash");
    await user.click(within(dialog).getByRole("checkbox", { name: "Ustoz" }));
    await user.type(within(dialog).getByLabelText("Haftasiga soat"), "4");
    expect(await axeViolations(dialog)).toEqual([]);
    await user.click(within(dialog).getByRole("button", { name: "Rejani ochish" }));
    expect(mfLearningPlanCreate).toHaveBeenCalledWith("mf", { goal: "HOME", skill: "Payvandlash", purpose: null, paths: ["MENTOR"], budget: null, weeklyMinutes: 240, startOn: null, reviewOn: null, ventureIdeaId: "i1" });

    await user.click(await screen.findByRole("button", { name: "Yangi reja" }));
    dialog = screen.getByRole("dialog");
    // Chet el maqsadida g'oya tanlovi yo'q va yuborilmaydi.
    expect(within(dialog).queryByLabelText("«Hunardan ishga» gʻoyasi (ixtiyoriy)")).not.toBeInTheDocument();
    await user.type(within(dialog).getByLabelText("Koʻnikma"), "Forklift guvohnomasi");
    await user.click(within(dialog).getByRole("checkbox", { name: "Kurs" }));
    await user.click(within(dialog).getByRole("button", { name: "Rejani ochish" }));
    expect(mfLearningPlanCreate.mock.calls[1]?.[1]).toMatchObject({ goal: "ABROAD", paths: ["COURSE"], ventureIdeaId: null });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("koʻpi bilan 2 ta faol reja");
  });

  it("holat, natija va «Ilm zakoti» yozuvi; kurs tekshiruvi ochiladi", async () => {
    mfLearningOverview.mockResolvedValue(ok(overview()));
    mfLearningPlanSetStatus.mockResolvedValue(ok(plan({ status: "PAUSED" })));
    mfLearningPlanResult.mockResolvedValue(
      ok({ planId: "p1", baseline: hour(), current: { ...hour(), id: "h2", hourValue: m("13 250 KRW", "13250") }, diff: m("1 205 KRW", "1205"), changeBp: 1000, changePercent: "10" }),
    );
    mfTeachingAdd.mockResolvedValue(ok({ id: "t2", occurredOn: "2026-10-20", area: "LANGUAGE", learner: null, topic: "Sexdagi xavfsizlik soʻzlari", minutes: null }));
    const user = userEvent.setup();
    wrap(<MfLearningScreen spaceId="mf" />);
    const card = await screen.findByTestId("mfl-plan-p1");
    await user.click(within(card).getByRole("button", { name: "Toʻxtatish" }));
    expect(mfLearningPlanSetStatus).toHaveBeenCalledWith("mf", "p1", "PAUSED");
    await user.click(within(card).getByRole("button", { name: "Natijani oʻlchash" }));
    expect(await within(card).findByTestId("plan-result")).toHaveTextContent("12 045 KRW → 13 250 KRW / soat");

    await user.click(screen.getByRole("button", { name: "Oʻrgatganimni yozish" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Til" }));
    await user.type(within(dialog).getByLabelText("Nimani oʻrgatdi"), "Sexdagi xavfsizlik soʻzlari");
    await user.click(within(dialog).getByRole("button", { name: "Saqlash" }));
    expect(mfTeachingAdd).toHaveBeenCalledWith("mf", { occurredOn: null, area: "LANGUAGE", learner: null, topic: "Sexdagi xavfsizlik soʻzlari", minutes: null });

    await user.click(within(screen.getByTestId("mfl-plan-p1")).getByRole("button", { name: "Kursni tekshirish" }));
    expect(useUi.getState()).toMatchObject({ offerOpen: true, offerMode: "COURSE" });
  });
});

describe("OfferCheckDialog: Musofir kurs savoli", () => {
  it("9-savol — chet elda ish kafolati; javob yadroga boradi va bayroq matni chiqadi", async () => {
    checkCourse.mockResolvedValue(ok({ verdict: "RED", flags: [{ code: "JOB_ABROAD_PROMISE", level: "RED" }], signs: 1 }));
    const user = userEvent.setup();
    const { container } = wrap(<OfferCheckDialog initialMode="COURSE" askJobAbroad onClose={() => {}} />);
    const groups = screen.getAllByRole("radiogroup");
    expect(groups).toHaveLength(9);
    expect(screen.getByText("Kursdan keyin chet elda ish kafolatlanyaptimi?")).toBeInTheDocument();
    const pick = ["Yoʻq", "Yoʻq", "Yoʻq", "Ha", "Ha", "Yoʻq", "Yoʻq", "Ha", "Ha"];
    for (const [i, g] of groups.entries()) {
      const radio = Array.from(g.querySelectorAll("label")).find((l) => l.textContent === pick[i])?.querySelector("input");
      if (radio) await user.click(radio);
    }
    await user.click(screen.getByRole("button", { name: "Tekshirish" }));
    const r = await screen.findByTestId("offer-result");
    expect(r).toHaveTextContent("Qizil: pul toʻlamang");
    expect(r).toHaveTextContent("chet elda ish vaʼda qilinmoqda");
    expect(checkCourse).toHaveBeenCalledWith({ fastRich: "NO", secretFormula: "NO", incomeGuarantee: "NO", syllabus: "YES", teacherVerifiable: "YES", urgency: "NO", recruitment: "NO", trialOrRefund: "YES", jobAbroad: "YES" });
    expect(await axeViolations(container)).toEqual([]);
  });
});
