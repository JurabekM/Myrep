import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { useUi } from "../../state/ui";
import { axeViolations } from "../../test/axe";
import { KkEntryDialog } from "./KkEntryDialog";
import { KkLearningScreen } from "./KkLearningScreen";

const kkLearningOverview = vi.fn();
const kkOwnerHourSuggest = vi.fn();
const kkOwnerHourSave = vi.fn();
const kkDelegateCalc = vi.fn();
const kkDelegationSave = vi.fn();
const kkDelegationDelete = vi.fn();
const kkTeachingAdd = vi.fn();
const categories = vi.fn();
const recordExpense = vi.fn();
vi.mock("../../bindings", () => ({
  commands: {
    kkLearningOverview: (...a: unknown[]) => kkLearningOverview(...a),
    kkOwnerHourSuggest: (...a: unknown[]) => kkOwnerHourSuggest(...a),
    kkOwnerHourSave: (...a: unknown[]) => kkOwnerHourSave(...a),
    kkDelegateCalc: (...a: unknown[]) => kkDelegateCalc(...a),
    kkDelegationSave: (...a: unknown[]) => kkDelegationSave(...a),
    kkDelegationDelete: (...a: unknown[]) => kkDelegationDelete(...a),
    kkTeachingAdd: (...a: unknown[]) => kkTeachingAdd(...a),
    categories: (...a: unknown[]) => categories(...a),
    recordExpense: (...a: unknown[]) => recordExpense(...a),
  },
}));

const m = (formatted: string, minor = "1") => ({
  minor,
  currency: "UZS",
  formatted,
  plain: formatted.replace(" soʻm", "").replace(/ /g, ""),
});
const ok = (data: unknown) => ({ status: "ok", data });
const fail = (code: string, field: string | null = null) => ({
  status: "error",
  error: { code, field, message: code },
});

// kasbkor/SPEC 8A.1 (Feruza): 5 000 000 + 3 100 000 = 8 100 000; 260 soat → 31 153,85.
const hour = {
  id: "h1",
  income: m("8 100 000 soʻm", "810000000"),
  incomeSource: "AUTO",
  months: 1,
  minutesPerDay: 600,
  days: 26,
  monthlyMinutes: 15600,
  hourValue: m("31 153,85 soʻm", "3115385"),
  doubleTarget: m("62 307,70 soʻm", "6230770"),
  overCeiling: false,
  computedOn: "2026-12-02",
};
const result = {
  ownerHourValue: m("31 153,85 soʻm", "3115385"),
  monthlyBenefit: m("323 077 soʻm", "32307700"),
  trainingTimeCost: m("311 538,50 soʻm", "31153850"),
  fullCost: m("811 538,50 soʻm", "81153850"),
  paybackMonths: 3,
  verdict: "DELEGATE",
};
const overview = (over: Record<string, unknown> = {}) => ({
  periodStart: "2026-12-01",
  periodEnd: "2027-01-01",
  hourValue: hour,
  delegations: [
    {
      id: "d1",
      task: "Mato qabul qilish",
      agreementId: "s1",
      staffName: "Sardor",
      taskMinutes: 1200,
      helperHourCost: m("15 000 soʻm", "1500000"),
      trainingMoney: m("500 000 soʻm", "50000000"),
      trainingMinutes: 600,
      decidedOn: "2026-12-02",
      result,
    },
  ],
  staff: [{ id: "s1", name: "Sardor" }],
  teachingCount: 1,
  teaching: [
    {
      id: "t1",
      occurredOn: "2026-12-02",
      agreementId: "s1",
      learner: "Sardor",
      topic: "Buyurtma qabul qilish",
      minutes: 90,
    },
  ],
  selfInvestment: m("300 000 soʻm", "30000000"),
  ...over,
});
const suggestion = {
  months: [
    {
      periodStart: "2026-11-01",
      periodEnd: "2026-11-30",
      ownerLabor: m("5 000 000 soʻm"),
      trueProfit: m("3 100 000 soʻm"),
      earnings: m("8 100 000 soʻm", "810000000"),
    },
  ],
  average: m("8 100 000 soʻm", "810000000"),
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Kasb-kor: Oʻzimga sarmoya (K9)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useUi.setState({ offerOpen: false, offerMode: "OFFER" });
    kkLearningOverview.mockResolvedValue(ok(overview()));
    kkOwnerHourSuggest.mockResolvedValue(ok(suggestion));
  });

  it("egasining soati: yopilgan oylar, maosh qo'shilmasligi, AUTO saqlash; axe toza", async () => {
    kkOwnerHourSave.mockResolvedValue(ok(hour));
    const { container } = wrap(<KkLearningScreen spaceId="kk" />);
    const card = await screen.findByTestId("kkl-hour");
    expect(within(card).getByTestId("kkl-hour-value")).toHaveTextContent("31 153,85 soʻm");
    expect(within(card).getByTestId("kkl-hour-double")).toHaveTextContent("62 307,70 soʻm");
    expect(await within(card).findByTestId("kkl-months")).toHaveTextContent("8 100 000 soʻm");
    expect(card).toHaveTextContent("maosh qoʻshilmaydi");
    expect(screen.getByTestId("kkl-self-investment")).toHaveTextContent("300 000 soʻm");
    await userEvent.click(within(card).getByRole("button", { name: "Hisoblash va saqlash" }));
    expect(kkOwnerHourSave).toHaveBeenCalledWith("kk", {
      income: null,
      minutesPerDay: 600,
      days: 26,
    });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("o'zim qilaymi: hisob yadrodan, qoplanish muddati; arzonroq bo'lsa — maslahat; saqlash xodim bilan", async () => {
    kkDelegateCalc.mockResolvedValueOnce(ok(result));
    const user = userEvent.setup();
    wrap(<KkLearningScreen spaceId="kk" />);
    const form = await screen.findByRole("form", {
      name: "Oʻzim qilaymi yoki oʻrgatib topshiraymi?",
    });
    await user.type(within(form).getByLabelText("Ish turi"), "Mato qabul qilish");
    await user.selectOptions(within(form).getByLabelText("Xodim kartochkasi (ixtiyoriy)"), "s1");
    await user.type(within(form).getByLabelText("Yordamchi yoki xodimning 1 soati narxi"), "15 000");
    await user.type(within(form).getByLabelText("Bu ishga oyiga, soat"), "20");
    await user.type(within(form).getByLabelText("Oʻrgatishga ketadigan vaqtingiz, soat"), "10");
    await user.type(within(form).getByLabelText("Bir martalik oʻrgatish xarajati (ixtiyoriy)"), "500 000");
    await user.click(within(form).getByRole("button", { name: "Hisoblash" }));
    const input = {
      task: "Mato qabul qilish",
      agreementId: "s1",
      ownerHourValue: null,
      taskMinutes: 1200,
      helperHourCost: "15 000",
      trainingMoney: "500 000",
      trainingMinutes: 600,
    };
    expect(kkDelegateCalc).toHaveBeenCalledWith("kk", input);
    expect(await screen.findByTestId("kkl-payback")).toHaveTextContent("3 oy");
    expect(screen.getByTestId("kkl-benefit")).toHaveTextContent("323 077 soʻm");

    kkDelegateCalc.mockResolvedValueOnce(
      ok({
        ...result,
        monthlyBenefit: m("−100 000 soʻm", "-10000000"),
        paybackMonths: null,
        verdict: "SELF_CHEAPER",
      }),
    );
    await user.click(within(form).getByRole("button", { name: "Hisoblash" }));
    expect(await screen.findByTestId("kkl-verdict")).toHaveTextContent("Hozircha oʻzingiz qilganingiz arzon");
    expect(screen.queryByTestId("kkl-payback")).toBeNull();

    kkDelegationSave.mockResolvedValue(ok(overview().delegations[0]));
    await user.click(within(form).getByRole("button", { name: "Qarorni saqlash" }));
    expect(kkDelegationSave).toHaveBeenCalledWith("kk", input);
    const saved = screen.getByRole("listitem", {
      name: "Qaror: Mato qabul qilish",
    });
    expect(saved).toHaveTextContent("Sardor");
    await user.click(within(saved).getByRole("button", { name: "Oʻchirish" }));
    // Avval tasdiq: bekor qilinsa — o'chirilmaydi.
    expect(kkDelegationDelete).not.toHaveBeenCalled();
    await user.click(within(saved).getByRole("button", { name: "Bekor qilish" }));
    await user.click(within(saved).getByRole("button", { name: "Oʻchirish" }));
    expect(within(saved).getByRole("group", { name: "«Mato qabul qilish» qarorini oʻchirasizmi?" })).toBeInTheDocument();
    await user.click(within(saved).getByRole("button", { name: "Ha, oʻchirish" }));
    expect(kkDelegationDelete).toHaveBeenCalledWith("kk", "d1");
  });

  it("soat qiymati yo'q: yadro xatosi ko'rsatiladi", async () => {
    kkLearningOverview.mockResolvedValue(ok(overview({ hourValue: null, delegations: [] })));
    kkDelegateCalc.mockResolvedValue(fail("KK_NO_HOUR_VALUE", "ownerHourValue"));
    const user = userEvent.setup();
    wrap(<KkLearningScreen spaceId="kk" />);
    expect(await screen.findByText(/Hali hisoblanmagan/)).toBeInTheDocument();
    const form = screen.getByRole("form", {
      name: "Oʻzim qilaymi yoki oʻrgatib topshiraymi?",
    });
    await user.click(within(form).getByRole("button", { name: "Hisoblash" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("egasining bir soati");
  });

  it("ilm zakoti: xodim kartochkasidan yoki boshqa kishi; kurs tekshiruvi COURSE turida", async () => {
    kkTeachingAdd.mockResolvedValue(ok(overview().teaching[0]));
    const user = userEvent.setup();
    wrap(<KkLearningScreen spaceId="kk" />);
    expect(await screen.findByTestId("kkl-teach-count")).toHaveTextContent("1");
    await user.click(screen.getByRole("button", { name: "Oʻrgatganimni yozish" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Nimani oʻrgatdi"), "Narx yorligʻi yozish");
    await user.click(within(dialog).getByRole("button", { name: "Saqlash" }));
    expect(kkTeachingAdd).toHaveBeenCalledWith("kk", {
      occurredOn: null,
      agreementId: "s1",
      learner: null,
      topic: "Narx yorligʻi yozish",
      minutes: null,
    });

    await user.click(screen.getByRole("button", { name: "Oʻrgatganimni yozish" }));
    const d2 = screen.getByRole("dialog");
    await user.selectOptions(within(d2).getByLabelText("Kimga: xodim"), "");
    await user.type(within(d2).getByLabelText("Ism (ixtiyoriy)"), "Qizi");
    await user.type(within(d2).getByLabelText("Nimani oʻrgatdi"), "Tugma qadash");
    await user.click(within(d2).getByRole("button", { name: "Saqlash" }));
    expect(kkTeachingAdd).toHaveBeenLastCalledWith("kk", {
      occurredOn: null,
      agreementId: null,
      learner: "Qizi",
      topic: "Tugma qadash",
      minutes: null,
    });

    await user.click(screen.getByRole("button", { name: "Kursni tekshirish" }));
    expect(useUi.getState()).toMatchObject({
      offerOpen: true,
      offerMode: "COURSE",
    });
  });

  it("chiqim oynasi: «Sarmoya (o'qish)» belgisi yadroga boradi", async () => {
    categories.mockResolvedValue(ok([{ id: "c1", nameKey: "category.kk.other", customName: null }]));
    recordExpense.mockResolvedValue(ok({}));
    const user = userEvent.setup();
    wrap(<KkEntryDialog spaceId="kk" mode="EXPENSE" onClose={() => undefined} />);
    await user.type(screen.getByLabelText("Summa"), "300 000");
    await screen.findByRole("option");
    await user.click(screen.getByRole("checkbox", { name: /Sarmoya \(oʻqish\)/ }));
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(recordExpense).toHaveBeenCalledWith(
      "kk",
      expect.objectContaining({
        amount: "300 000",
        categoryId: "c1",
        selfInvestment: true,
      }),
    );
  });
});
