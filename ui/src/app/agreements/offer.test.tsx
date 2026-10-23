import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type OfferCheckDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// D16 UI (7-qonun): taklif tekshiruvi 9 savol, besh belgi, va'da hisobi, «to'xta, maslahatlash», piramida, shablon.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
    lock: vi.fn(),
    getHome: vi.fn(),
    listIncomesThisMonth: vi.fn(),
    listRecentIncomes: vi.fn(),
    getVault: vi.fn(),
    getAudit: vi.fn(),
    getWhoseMoney: vi.fn(),
    listCategories: vi.fn(),
    listObligations: vi.fn(),
    listDebts: vi.fn(),
    listChapters: vi.fn(),
    getWeeklyTasks: vi.fn(),
    listAgreements: vi.fn(),
    getAgreementsCenter: vi.fn(),
    listFamilyTemplates: vi.fn(),
    getAgreementOps: vi.fn(),
    getPartnerships: vi.fn(),
    listOfferChecks: vi.fn(),
    listHustleTemplates: vi.fn(),
    checkOffer: vi.fn(),
    decideOffer: vi.fn(),
    pyramidModel: vi.fn(),
    hustlePlan: vi.fn(),
  },
}));

const RED: OfferCheckDto = {
  id: "o-1",
  title: "«Tez Foyda» — tanish taklifi",
  answers: {
    guaranteed: "YES",
    lossShared: "NO",
    realGoods: "UNKNOWN",
    recruitment: "YES",
    pressure: "YES",
    writtenContract: "YES",
    exitEasy: "UNKNOWN",
    license: "UNKNOWN",
    verifiedInPerson: "NO",
  },
  verdict: "RED",
  level: "FLEE",
  signs: [
    {
      code: "GUARANTEED_HIGH_RETURN",
      explanation: "Yuqori foyda kafolatlanmoqda.",
    },
    { code: "URGENCY", explanation: "«Faqat bugun», «joy kam» — qaror uchun vaqt berilmayapti." },
    {
      code: "RECRUITMENT_INCOME",
      explanation: "Daromad yangi qatnashchilar jalb qilishdan keladi.",
    },
    { code: "NO_REAL_BUSINESS", explanation: "Ishning o'zini tekshirib bo'lmaydi." },
  ],
  categories: ["RIBO", "GHARAR", "QIMOR"],
  flags: [
    {
      code: "GUARANTEED_PROFIT",
      question: "guaranteed",
      explanation: "tavakkalsiz kafolatlangan foyda — ribo yoki firibgarlik belgisi",
      red: true,
    },
  ],
  amount: money(1_000_000, "10 000 soʻm"),
  promised: { monthlyBp: 3500, months: 12, simpleMultipleBp: 52_000, compoundMultipleBp: 366_439 },
  advisor: null,
  decision: null,
  checkedOn: "2026-10-20",
  decidedOn: null,
  coolingHoursLeft: 24,
  canAccept: false,
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue({
    name: "Baraka Dastur",
    version: "0.1.0",
    platform: "windows",
    arch: "x86_64",
    buildProfile: "release",
  });
  vi.mocked(commands.getSecurityStatus).mockResolvedValue({
    status: "ok",
    data: { setUp: true, unlocked: true },
  });
  resetFinanceMocks();
  vi.mocked(commands.listAgreements).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getAgreementsCenter).mockResolvedValue({ status: "ok", data: { rows: [] } });
  vi.mocked(commands.listFamilyTemplates).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getPartnerships).mockResolvedValue({
    status: "ok",
    data: { items: [], gate: "LOCKED", gateReasons: [] },
  });
  vi.mocked(commands.listOfferChecks).mockResolvedValue({ status: "ok", data: { items: [] } });
  vi.mocked(commands.listHustleTemplates).mockResolvedValue({
    status: "ok",
    data: [
      {
        id: "FORGE_WELD",
        name: "Temirchilik / payvand ustaxonasi",
        story: "Bekzod: pul hunariga ishlasin.",
        capexLines: ["Payvand apparati va niqob", "Bolgarka, drel"],
        demandQuestion: "Talab bormi? Atrofda qancha uy qurilmoqda?",
      },
    ],
  });
}

describe("7-qonun: taklif tekshiruvi", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "partnerships", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("«Tez Foyda» taklifi: to'rt belgi, uch toifa, va'da yillikka, maslahatsiz «pul qo'yaman» yopiq, rad etish", async () => {
    vi.mocked(commands.checkOffer).mockResolvedValue({ status: "ok", data: RED });
    vi.mocked(commands.decideOffer).mockResolvedValue({
      status: "ok",
      data: { items: [{ ...RED, decision: "DECLINED", decidedOn: "2026-10-20" }] },
    });
    render(<App />);
    const user = userEvent.setup();
    const heading = await screen.findByRole("heading", {
      name: "Taklif tekshiruvi — besh xavf belgisi",
    });
    const card = heading.closest("section") ?? heading.parentElement;
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    await user.type(
      within(card).getByLabelText("Taklif (kim, nima)"),
      "«Tez Foyda» — tanish taklifi",
    );
    await user.type(within(card).getByLabelText("Taxminiy summa"), "10 000");
    await user.type(within(card).getByLabelText("Va'da: oyiga %"), "35");
    await user.click(within(card).getByLabelText("Foyda kafolatlangan deyishadimi?: Ha"));
    await user.click(
      within(card).getByLabelText(
        "Zarar bo'lsa, u ham bo'lishiladimi (tavakkal tan olinadimi)?: Yo'q",
      ),
    );
    await user.click(
      within(card).getByLabelText("Daromad yangi odam olib kelishdan keladimi?: Ha"),
    );
    await user.click(
      within(card).getByLabelText("Shoshirishadimi («faqat bugun», «joy kam»)?: Ha"),
    );
    await user.click(within(card).getByLabelText("Yozma shartnoma bormi?: Ha"));
    await user.click(
      within(card).getByLabelText("Ishni o'z ko'zingiz bilan ko'rdingizmi (ko'rsatishdimi)?: Yo'q"),
    );
    await user.click(within(card).getByRole("button", { name: "Tekshirish" }));
    expect(commands.checkOffer).toHaveBeenCalledWith({
      title: "«Tez Foyda» — tanish taklifi",
      answers: RED.answers,
      amount: "10 000",
      promisedMonthlyBp: 3500,
      advisor: null,
    });
    const status = await within(card).findByRole("status");
    expect(status).toHaveTextContent(/Qizil/);
    expect(status).toHaveTextContent("Besh belgidan 4 tasi bor — voz kechgan ma'qul");
    expect(status).toHaveTextContent(/ribo .* g'arar .* qimor/);
    expect(within(status).getByRole("list", { name: "Topilgan belgilar" }).children).toHaveLength(
      4,
    );
    expect(status).toHaveTextContent("5,2 barobar");
    expect(status).toHaveTextContent("36,6 barobar");
    // Maslahatchisiz «pul qo'yaman» yopiq; sabab matni.
    expect(within(status).getByRole("button", { name: "Pul qo'yaman" })).toBeDisabled();
    expect(status).toHaveTextContent("Avval maslahatchi ismini yozing.");
    await user.type(within(status).getByLabelText("Kim bilan maslahatlashdingiz?"), "Shavkat aka");
    expect(within(status).getByRole("button", { name: "Pul qo'yaman" })).toBeDisabled();
    expect(status).toHaveTextContent("yana 24 soat");
    // Rad etish darhol.
    await user.click(within(status).getByRole("button", { name: "Rad etdim" }));
    expect(commands.decideOffer).toHaveBeenCalledWith({
      id: "o-1",
      decision: "DECLINED",
      advisor: "Shavkat aka",
    });
    expect(await within(card).findByText(/Qaror: rad etildi \(2026-10-20\)/)).toBeInTheDocument();
    expect(within(card).getByRole("list", { name: "Tekshiruvlar tarixi" })).toHaveTextContent(
      "«Tez Foyda» — tanish taklifi",
    );
  });

  it("24 soat o'tgan va maslahatchi bor taklifda «pul qo'yaman» ochiq", async () => {
    const ready: OfferCheckDto = {
      ...RED,
      id: "o-2",
      verdict: "YELLOW",
      level: "CAUTION",
      signs: [RED.signs[1] ?? { code: "URGENCY", explanation: "shoshirish" }],
      categories: [],
      advisor: "Akmal",
      coolingHoursLeft: 0,
      canAccept: true,
      promised: null,
    };
    vi.mocked(commands.listOfferChecks).mockResolvedValue({
      status: "ok",
      data: { items: [ready] },
    });
    vi.mocked(commands.decideOffer).mockResolvedValue({
      status: "ok",
      data: { items: [{ ...ready, decision: "ACCEPTED", decidedOn: "2026-10-21" }] },
    });
    render(<App />);
    const user = userEvent.setup();
    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("24 soat o'tdi — qaror sizniki.");
    const accept = within(status).getByRole("button", { name: "Pul qo'yaman" });
    expect(accept).toBeEnabled();
    await user.click(accept);
    expect(commands.decideOffer).toHaveBeenCalledWith({
      id: "o-2",
      decision: "ACCEPTED",
      advisor: "Akmal",
    });
    expect(await screen.findByText(/Qaror: pul qo'yildi/)).toBeInTheDocument();
  });

  it("piramida hisobi va hunar shabloni", async () => {
    vi.mocked(commands.pyramidModel).mockResolvedValue({
      status: "ok",
      data: {
        recruitsPerPerson: 5,
        population: 1_000_000,
        levels: 10,
        participants: 1_000_000,
        lastLevel: 511_719,
        lastLevelShareBp: 5117,
        lastLevelFull: false,
      },
    });
    render(<App />);
    const user = userEvent.setup();
    const heading = await screen.findByRole("heading", {
      name: "Piramida — qaysi qavatda bo'lasiz?",
    });
    const card = heading.closest("section") ?? heading.parentElement;
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    await user.click(within(card).getByRole("button", { name: "Piramidani hisoblash" }));
    expect(commands.pyramidModel).toHaveBeenCalledWith(5, 1_000_000);
    const status = await within(card).findByRole("status");
    expect(status).toHaveTextContent("10");
    expect(status).toHaveTextContent("51.2 %");
    expect(status).toHaveTextContent(
      "Sxema to'xtaganda qatnashchilarning ko'pchiligi eng pastki qavatda — pulini qaytara olmagan holda qoladi.",
    );

    const hustle = screen.getByRole("heading", { name: "«Hunardan ishga»" });
    const hustleCard = hustle.closest("section") ?? hustle.parentElement;
    if (hustleCard === null) {
      throw new Error("karta topilmadi");
    }
    await user.selectOptions(within(hustleCard).getByLabelText("Hunar shabloni"), "FORGE_WELD");
    expect(within(hustleCard).getByRole("list", { name: "Shablon qatorlari" })).toHaveTextContent(
      "Payvand apparati va niqob",
    );
    expect(within(hustleCard).getByLabelText("Hunar / g'oya")).toHaveValue(
      "Temirchilik / payvand ustaxonasi",
    );
    expect(hustleCard).toHaveTextContent("Talab bormi?");
  });
});
