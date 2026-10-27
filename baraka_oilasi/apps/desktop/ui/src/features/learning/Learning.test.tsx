import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { useUi } from "../../state/ui";
import { axeViolations } from "../../test/axe";
import { AuditScreen } from "../audit/AuditScreen";
import { ExpensesScreen } from "../expenses/ExpensesScreen";
import { OfferCheckDialog } from "../venture/OfferCheckDialog";
import { LearningScreen } from "./LearningScreen";
import { parseCount, toMinutes } from "./time";

const learningOverview = vi.fn();
const hourValueSuggest = vi.fn();
const hourValueSave = vi.fn();
const learningPlanCreate = vi.fn();
const learningPlanSetStatus = vi.fn();
const learningPlanResult = vi.fn();
const studyLogAdd = vi.fn();
const teachingLogAdd = vi.fn();
const checkCourse = vi.fn();
const household = vi.fn();
const categories = vi.fn();
const monthlySummary = vi.fn();
const recordExpense = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    learningOverview: (...a: unknown[]) => learningOverview(...a),
    hourValueSuggest: (...a: unknown[]) => hourValueSuggest(...a),
    hourValueSave: (...a: unknown[]) => hourValueSave(...a),
    learningPlanCreate: (...a: unknown[]) => learningPlanCreate(...a),
    learningPlanSetStatus: (...a: unknown[]) => learningPlanSetStatus(...a),
    learningPlanResult: (...a: unknown[]) => learningPlanResult(...a),
    studyLogAdd: (...a: unknown[]) => studyLogAdd(...a),
    teachingLogAdd: (...a: unknown[]) => teachingLogAdd(...a),
    checkCourse: (...a: unknown[]) => checkCourse(...a),
    household: (...a: unknown[]) => household(...a),
    categories: (...a: unknown[]) => categories(...a),
    monthlySummary: (...a: unknown[]) => monthlySummary(...a),
    recordExpense: (...a: unknown[]) => recordExpense(...a),
  },
}));

const ok = (data: unknown) => ({ status: "ok", data });
const fail = (code: string, field: string | null = null) => ({ status: "error", error: { code, field } });
const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });

const hv = {
  id: "h1",
  memberId: "m1",
  income: money("12 000 000 soʻm", "1200000000"),
  incomeSource: "AUTO",
  minutesPerDay: 720,
  days: 26,
  monthlyMinutes: 18720,
  hourValue: money("38 461,54 soʻm", "3846154"),
  doubleTarget: money("76 923,08 soʻm", "7692308"),
  overCeiling: true,
  computedOn: "2026-11-10",
};
const plan = (id: string, skill: string, status: string, extra: Record<string, unknown> = {}) => ({
  id,
  memberId: "m1",
  skill,
  purpose: "Ustaxonaga bermasdan oʻzim qilaman",
  paths: ["COURSE", "PRACTICE"],
  budget: money("1 500 000 soʻm", "150000000"),
  weeklyMinutes: 180,
  startOn: "2026-11-10",
  reviewOn: "2027-02-10",
  status,
  baselineHourValue: money("38 461,54 soʻm", "3846154"),
  resultHourValue: null,
  studyMinutes: 150,
  spent: money("1 200 000 soʻm", "120000000"),
  courseCheckSuggested: true,
  reviewDue: false,
  ...extra,
});
const overview = {
  periodStart: "2026-11-01",
  periodEnd: "2026-11-30",
  members: [
    { memberId: "m1", displayName: "Bekzod", hourValue: hv, activePlans: 2 },
    { memberId: "m2", displayName: "Feruza", hourValue: null, activePlans: 0 },
  ],
  plans: [plan("p1", "Elektr montaj asoslari", "ACTIVE"), plan("p2", "Buxgalteriya", "PAUSED", { paths: ["BOOK"], courseCheckSuggested: false, budget: null }), plan("p3", "Ingliz tili", "DONE", { courseCheckSuggested: false })],
  teachingCount: 1,
  teaching: [{ id: "t1", memberId: "m1", occurredOn: "2026-11-14", learner: "hamkasb", topic: "Rozetka ulash", minutes: 45 }],
  selfInvestment: { total: money("1 200 000 soʻm", "120000000"), income: money("12 000 000 soʻm", "1200000000"), shareBp: 1000, sharePercent: "10" },
};
const suggestion = { memberId: "m1", months: [{ periodStart: "2026-10-01", periodEnd: "2026-10-31", total: money("12 000 000 soʻm", "1200000000") }], average: money("12 000 000 soʻm", "1200000000") };

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  for (const f of [learningOverview, hourValueSuggest, hourValueSave, learningPlanCreate, learningPlanSetStatus, learningPlanResult, studyLogAdd, teachingLogAdd, checkCourse, household, categories, monthlySummary, recordExpense]) f.mockReset();
  learningOverview.mockResolvedValue(ok(overview));
  hourValueSuggest.mockImplementation((_s: string, m: string) => Promise.resolve(ok(m === "m1" ? suggestion : { memberId: m, months: [], average: null })));
  useUi.setState({ offerOpen: false, offerMode: "OFFER" });
});

describe("LearningScreen", () => {
  it("soat qiymati yadrodan: AUTO manba, ikki barobar maqsad, soat chegarasi — ayblovsiz; qoʻlda daromad bilan saqlash", async () => {
    hourValueSave.mockResolvedValue(ok({ ...hv, incomeSource: "MANUAL" }));
    const user = userEvent.setup();
    const { container } = wrap(<LearningScreen spaceId="uy" />);
    const card = await screen.findByRole("region", { name: "Bir soatim qancha? — Bekzod" });
    expect(within(card).getByTestId("hour-value")).toHaveTextContent("38 461,54 soʻm");
    expect(within(card).getByTestId("hour-double")).toHaveTextContent("76 923,08 soʻm");
    expect(within(card).getByText("Oylik daromad: 12 000 000 soʻm — oxirgi oylar oʻrtachasi (avtomatik)")).toBeInTheDocument();
    expect(within(card).getByText(/Oyiga ish vaqti: 312 soat/)).toBeInTheDocument();
    expect(within(card).getByTestId("hour-ceiling")).toHaveTextContent("Soatni yana koʻpaytirish oʻrniga");
    expect(await within(card).findByText("Boʻsh qoldirsangiz — oxirgi 1 oy oʻrtachasi: 12 000 000 soʻm")).toBeInTheDocument();
    const other = screen.getByRole("region", { name: "Bir soatim qancha? — Feruza" });
    expect(within(other).getByText(/Hali hisoblanmagan/)).toBeInTheDocument();
    expect(await within(other).findByText(/daromad yozuvi yoʻq/)).toBeInTheDocument();
    expect(screen.getByTestId("learn-self-investment")).toHaveTextContent("1 200 000 soʻm — daromadning 10 %");
    expect(screen.getByText("Bu haftaning 3 vazifasi")).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);

    await user.type(within(card).getByLabelText("Oylik daromad (boʻsh — avtomatik)"), "10 000 000");
    await user.clear(within(card).getByLabelText("Kuniga soat"));
    await user.type(within(card).getByLabelText("Kuniga soat"), "9");
    await user.clear(within(card).getByLabelText("Kuniga daqiqa"));
    await user.type(within(card).getByLabelText("Kuniga daqiqa"), "30");
    await user.clear(within(card).getByLabelText("Oyda ish kunlari"));
    await user.type(within(card).getByLabelText("Oyda ish kunlari"), "24");
    await user.click(within(card).getByRole("button", { name: "Hisoblash va saqlash" }));
    expect(hourValueSave).toHaveBeenCalledWith("uy", { memberId: "m1", income: "10 000 000", minutesPerDay: 570, days: 24 });
  });

  it("reja kartasi: vaqt, byudjet va sarflangan, holat tugmalari, kurs tekshiruvi; 2 faol reja chegarasi xatosi", async () => {
    learningPlanSetStatus.mockResolvedValue(fail("ACTIVE_PLAN_LIMIT"));
    studyLogAdd.mockResolvedValue(ok(plan("p1", "Elektr montaj asoslari", "ACTIVE")));
    const user = userEvent.setup();
    wrap(<LearningScreen spaceId="uy" />);
    const p1 = await screen.findByRole("region", { name: "Bilim rejasi: Elektr montaj asoslari" });
    expect(within(p1).getByTestId("plan-status")).toHaveTextContent("Faol");
    expect(within(p1).getByTestId("plan-studied")).toHaveTextContent("Jami oʻqildi: 2 soat 30 daqiqa");
    expect(within(p1).getByTestId("plan-spent")).toHaveTextContent("Byudjet: 1 500 000 soʻm · sarflandi: 1 200 000 soʻm");
    expect(within(p1).getByText("Haftalik reja: 3 soat")).toBeInTheDocument();
    expect(within(p1).getByText("Boshlangʻich nuqta: 38 461,54 soʻm / soat")).toBeInTheDocument();
    expect(within(p1).getByRole("button", { name: "Toʻxtatish" })).toBeInTheDocument();

    await user.click(within(p1).getByRole("button", { name: "Kursni tekshirish" }));
    expect(useUi.getState()).toMatchObject({ offerOpen: true, offerMode: "COURSE" });

    await user.type(within(p1).getByLabelText("Oʻqish, soat"), "1");
    await user.type(within(p1).getByLabelText("Oʻqish, daqiqa"), "15");
    await user.click(within(p1).getByRole("button", { name: "Vaqtni yozish" }));
    expect(studyLogAdd).toHaveBeenCalledWith("uy", "p1", { occurredOn: null, minutes: 75, note: null });

    const p2 = screen.getByRole("region", { name: "Bilim rejasi: Buxgalteriya" });
    expect(within(p2).getByTestId("plan-spent")).toHaveTextContent("Sarflandi: 1 200 000 soʻm");
    expect(within(p2).queryByRole("button", { name: "Kursni tekshirish" })).not.toBeInTheDocument();
    await user.click(within(p2).getByRole("button", { name: "Davom ettirish" }));
    expect(learningPlanSetStatus).toHaveBeenCalledWith("uy", "p2", "ACTIVE");
    expect(await within(p2).findByRole("alert")).toHaveTextContent("koʻpi bilan 2 ta faol reja");

    // Yopilgan reja: holat tugmalari va o'qish formasi yo'q.
    const p3 = screen.getByRole("region", { name: "Bilim rejasi: Ingliz tili" });
    expect(within(p3).getByTestId("plan-status")).toHaveTextContent("Tugatildi");
    expect(within(p3).queryByRole("button", { name: "Davom ettirish" })).not.toBeInTheDocument();
    expect(within(p3).queryByLabelText("Oʻqish, soat")).not.toBeInTheDocument();
  });

  it("natijani oʻlchash: farq va foiz yadrodan; yangi hisob yoʻq — tushunarli xabar; pasaysa — uyaltirmaydi", async () => {
    learningPlanResult
      .mockResolvedValueOnce(fail("NO_NEW_HOUR_VALUE"))
      .mockResolvedValueOnce(ok({ planId: "p1", baseline: hv, current: { ...hv, id: "h2", hourValue: money("57 692,31 soʻm", "5769231") }, diff: money("19 230,77 soʻm", "1923077"), changeBp: 5000, changePercent: "50" }))
      .mockResolvedValueOnce(ok({ planId: "p1", baseline: hv, current: { ...hv, id: "h3", hourValue: money("30 000 soʻm", "3000000") }, diff: money("−8 461,54 soʻm", "-846154"), changeBp: -2200, changePercent: "−22" }));
    const user = userEvent.setup();
    wrap(<LearningScreen spaceId="uy" />);
    const p1 = await screen.findByRole("region", { name: "Bilim rejasi: Elektr montaj asoslari" });
    await user.click(within(p1).getByRole("button", { name: "Natijani oʻlchash" }));
    expect(await within(p1).findByRole("alert")).toHaveTextContent("boshlangʻich nuqtadan keyin «Bir soatim qancha?» hisobini yangidan saqlang");
    await user.click(within(p1).getByRole("button", { name: "Natijani oʻlchash" }));
    const r = await within(p1).findByTestId("plan-result");
    expect(r).toHaveTextContent("38 461,54 soʻm → 57 692,31 soʻm / soat");
    expect(r).toHaveTextContent("Farq: 19 230,77 soʻm (50 %)");
    expect(r).toHaveTextContent("Bir soatingiz qiymati oshdi");
    await user.click(within(p1).getByRole("button", { name: "Natijani oʻlchash" }));
    expect(await within(p1).findByText(/bu ayb emas/)).toBeInTheDocument();
    expect(learningPlanResult).toHaveBeenCalledWith("uy", "p1");
  });

  it("boshlangʻich nuqtasiz natija: faqat hozirgi qiymat va betaraf izoh — «oʻsish yoʻq» deyilmaydi", async () => {
    learningPlanResult.mockResolvedValue(ok({ planId: "p1", baseline: null, current: hv, diff: null, changeBp: null, changePercent: null }));
    const user = userEvent.setup();
    wrap(<LearningScreen spaceId="uy" />);
    const p1 = await screen.findByRole("region", { name: "Bilim rejasi: Elektr montaj asoslari" });
    await user.click(within(p1).getByRole("button", { name: "Natijani oʻlchash" }));
    const r = await within(p1).findByTestId("plan-result");
    expect(r).toHaveTextContent("Hozirgi qiymat: 38 461,54 soʻm / soat");
    expect(r).toHaveTextContent("boshlangʻich nuqta yozilmagan edi");
    expect(r).not.toHaveTextContent("ayb emas");
    expect(r).not.toHaveTextContent("oshdi");
  });

  it("«Yangi reja» maʼlumot yuklanmaguncha (yoki xatoda) bosilmaydi", async () => {
    learningOverview.mockResolvedValue(fail("GENERIC"));
    wrap(<LearningScreen spaceId="uy" />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yangi reja" })).toBeDisabled();
  });
  it("yangi reja oynasi va «Ilm zakoti» yozuvi", async () => {
    learningPlanCreate.mockResolvedValue(ok(plan("p4", "Bichish", "ACTIVE")));
    teachingLogAdd.mockResolvedValue(ok({ id: "t2", memberId: "m2", occurredOn: "2026-11-20", learner: null, topic: "Tugma qadash", minutes: 30 }));
    const user = userEvent.setup();
    const { container } = wrap(<LearningScreen spaceId="uy" />);
    expect(await screen.findByTestId("teach-count")).toHaveTextContent("Shu oy: 1 marta oʻrgatildi");
    expect(screen.getByText("Rozetka ulash")).toBeInTheDocument();
    expect(screen.getByText("kimga: hamkasb")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Yangi reja" }));
    const d = screen.getByRole("dialog", { name: "Yangi bilim rejasi" });
    await user.selectOptions(within(d).getByLabelText("Aʼzo"), "m2");
    await user.type(within(d).getByLabelText("Koʻnikma"), "Bichish");
    await user.click(within(d).getByLabelText("Kurs"));
    expect(within(d).getByText("Pullik kurs boʻlsa — toʻlashdan oldin uni tekshiring.")).toBeInTheDocument();
    await user.click(within(d).getByLabelText("Ustoz"));
    await user.type(within(d).getByLabelText("Byudjet (ixtiyoriy)"), "2 000 000");
    await user.type(within(d).getByLabelText("Haftasiga soat"), "4");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(d).getByRole("button", { name: "Rejani ochish" }));
    expect(learningPlanCreate).toHaveBeenCalledWith("uy", { memberId: "m2", skill: "Bichish", purpose: null, paths: ["COURSE", "MENTOR"], budget: "2 000 000", weeklyMinutes: 240, startOn: null, reviewOn: null });
    await screen.findByRole("button", { name: "Oʻrgatganimni yozish" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Oʻrgatganimni yozish" }));
    const td = screen.getByRole("dialog", { name: "Ilm zakoti: oʻrgatish yozuvi" });
    await user.selectOptions(within(td).getByLabelText("Kim oʻrgatdi"), "m2");
    await user.type(within(td).getByLabelText("Nimani oʻrgatdi"), "Tugma qadash");
    await user.type(within(td).getByLabelText("Qancha vaqt, daqiqa (ixtiyoriy)"), "30");
    await user.click(within(td).getByRole("button", { name: "Saqlash" }));
    expect(teachingLogAdd).toHaveBeenCalledWith("uy", { memberId: "m2", occurredOn: null, learner: null, topic: "Tugma qadash", minutes: 30 });
  });
});

describe("vaqt maydonlari (Android bilan bir xil qoida)", () => {
  it("soat ≤ 3 raqam, daqiqa 0–59, kunlar 1–2 raqam; notoʻgʻri — 0", () => {
    expect(toMinutes("9", "30")).toBe(570);
    expect(toMinutes("", "45")).toBe(45);
    expect(toMinutes("1", "")).toBe(60);
    expect(toMinutes("1", "60")).toBe(0);
    expect(toMinutes("1,5", "")).toBe(0);
    expect(toMinutes("1000", "0")).toBe(0);
    expect(parseCount("26", 2)).toBe(26);
    expect(parseCount("260", 2)).toBe(0);
    expect(parseCount("-1", 2)).toBe(0);
    expect(parseCount("1440", 4)).toBe(1440);
  });
});

describe("OfferCheckDialog: kurs turi", () => {
  it("8 savol, «Bilmayman» ham javob; qizil — ikki belgi kurs matni bilan; jobAbroad soʻralmaydi", async () => {
    checkCourse.mockResolvedValue(ok({ verdict: "RED", flags: [{ code: "FAST_RICH", level: "YELLOW" }, { code: "NO_TRIAL_OR_REFUND", level: "YELLOW" }, { code: "TEACHER_UNKNOWN", level: "YELLOW" }, { code: "TWO_SIGNS", level: "RED" }], signs: 2 }));
    const user = userEvent.setup();
    const { container } = wrap(<OfferCheckDialog initialMode="COURSE" onClose={() => {}} />);
    expect(screen.getByRole("button", { name: "Kurs yoki ustoz taklifi" })).toHaveAttribute("aria-pressed", "true");
    const groups = screen.getAllByRole("radiogroup");
    expect(groups).toHaveLength(8);
    expect(screen.queryByText(/chet elda/)).not.toBeInTheDocument();
    const pick = ["Ha", "Yoʻq", "Yoʻq", "Ha", "Bilmayman", "Yoʻq", "Yoʻq", "Yoʻq"];
    for (const [i, g] of groups.entries()) {
      const radio = Array.from(g.querySelectorAll("label")).find((l) => l.textContent === pick[i])?.querySelector("input");
      if (radio) await user.click(radio);
    }
    await user.click(screen.getByRole("button", { name: "Tekshirish" }));
    const r = await screen.findByTestId("offer-result");
    expect(r).toHaveTextContent("Qizil: pul toʻlamang");
    expect(r).toHaveTextContent("Xavf belgilari: 2");
    expect(r).toHaveTextContent("«tez boyish» orzusini sotadiganlarga");
    expect(r).toHaveTextContent("Ikki va undan koʻp xavf belgisi bor — bu kursga pul toʻlamang.");
    expect(r).not.toHaveTextContent("Besh xavf belgisidan");
    expect(checkCourse).toHaveBeenCalledWith({ fastRich: "YES", secretFormula: "NO", incomeGuarantee: "NO", syllabus: "YES", teacherVerifiable: "UNKNOWN", urgency: "NO", recruitment: "NO", trialOrRefund: "NO", jobAbroad: null });
    expect(await axeViolations(container)).toEqual([]);
    // Boshqa turga o'tilsa — javoblar va natija tozalanadi.
    await user.click(screen.getByRole("button", { name: "Sarmoya yoki sheriklik taklifi" }));
    expect(screen.getAllByRole("radiogroup")).toHaveLength(9);
    expect(screen.queryByTestId("offer-result")).not.toBeInTheDocument();
  });
});

const summary = {
  periodStart: "2026-11-01",
  periodEnd: "2026-11-30",
  income: money("12 000 000 soʻm", "1200000000"),
  paidToSelf: money("0 soʻm", "0"),
  obligationsPaid: money("0 soʻm", "0"),
  expenses: money("1 200 000 soʻm", "120000000"),
  byNecessity: { zarur: money("0 soʻm", "0"), kerak: money("1 200 000 soʻm", "120000000"), havas: money("0 soʻm", "0"), sadaqa: money("0 soʻm", "0"), unclassified: money("0 soʻm", "0") },
  vaultNet: money("0 soʻm", "0"),
  balanceDelta: money("0 soʻm", "0"),
  unexplainedGap: money("0 soʻm", "0"),
  monthResult: money("0 soʻm", "0"),
  havasForLimit: money("0 soʻm", "0"),
  selfInvestment: overview.selfInvestment,
};

describe("Xarajat formasi: «Oʻzimga sarmoya»", () => {
  beforeEach(() => {
    categories.mockResolvedValue(ok([{ id: "c1", nameKey: "category.education", customName: "Oʻqish", defaultNecessity: "KERAK" }]));
    monthlySummary.mockResolvedValue(ok(summary));
    recordExpense.mockResolvedValue(ok({}));
  });

  it("Uy: belgi va faqat ochiq rejalar (tanlangan aʼzoniki); reja aʼzosi xarajatga yoziladi", async () => {
    const user = userEvent.setup();
    const { container } = wrap(<ExpensesScreen spaceId="uy" />);
    const box = await screen.findByLabelText("Oʻzimga sarmoya (bilim, malaka)");
    expect(learningOverview).not.toHaveBeenCalled();
    expect(screen.getByText("Toifa oʻzgarmaydi; bu xarajat havas chegarasiga kirmaydi.")).toBeInTheDocument();
    expect(await screen.findAllByText("1 200 000 soʻm")).not.toHaveLength(0);
    await user.click(box);
    await screen.findByRole("option", { name: "Elektr montaj asoslari · Bekzod" });
    const planSelect = screen.getByLabelText("Bilim rejasi (ixtiyoriy)");
    const options = within(planSelect).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["—", "Elektr montaj asoslari · Bekzod", "Buxgalteriya · Bekzod"]);
    await user.selectOptions(screen.getByLabelText("Kimning oʻqishi (ixtiyoriy)"), "m2");
    expect(within(screen.getByLabelText("Bilim rejasi (ixtiyoriy)")).getAllByRole("option")).toHaveLength(1);
    await user.selectOptions(screen.getByLabelText("Kimning oʻqishi (ixtiyoriy)"), "");
    await user.selectOptions(screen.getByLabelText("Bilim rejasi (ixtiyoriy)"), "p1");
    expect(await axeViolations(container)).toEqual([]);
    await user.type(screen.getByLabelText("Summa"), "1 200 000");
    await user.selectOptions(screen.getByLabelText("Kategoriya"), "c1");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(recordExpense).toHaveBeenCalledWith("uy", expect.objectContaining({ amount: "1 200 000", categoryId: "c1", memberId: "m1", selfInvestment: true, learningPlanId: "p1", necessity: null }));
  });

  it("rejalar faqat belgi qoʻyilganda oʻqiladi; belgisiz xarajat — reja va aʼzosiz", async () => {
    const user = userEvent.setup();
    wrap(<ExpensesScreen spaceId="uy" />);
    await screen.findByRole("option", { name: "Oʻqish" });
    expect(screen.getByLabelText("Oʻzimga sarmoya (bilim, malaka)")).not.toBeChecked();
    expect(screen.queryByLabelText("Bilim rejasi (ixtiyoriy)")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Summa"), "50 000");
    await user.selectOptions(screen.getByLabelText("Kategoriya"), "c1");
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(recordExpense).toHaveBeenCalledWith("uy", expect.objectContaining({ selfInvestment: false, learningPlanId: null, memberId: null }));
    expect(learningOverview).not.toHaveBeenCalled();
  });

  it("oylik auditda «Oʻzimga sarmoya» qatori — jami va daromad ulushi", async () => {
    wrap(<AuditScreen spaceId="uy" />);
    expect(await screen.findByText("Oʻzimga sarmoya")).toBeInTheDocument();
    expect(screen.getByText("1 200 000 soʻm — daromadning 10 %")).toBeInTheDocument();
  });
});
