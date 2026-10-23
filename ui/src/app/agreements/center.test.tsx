import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type AgreementDto,
  type AgreementOpsDto,
  type CenterDto,
  commands,
} from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

function first(elements: HTMLElement[]): HTMLElement {
  const [element] = elements;
  if (element === undefined) {
    throw new Error("element topilmadi");
  }
  return element;
}

// D13A UI: markaz jadvali (filtr), hodisa (band ko'rsatiladi), ko'rik sessiyasi (belgi + PDF), nizo, oilaviy PIN.
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
    getPartnerships: vi.fn(),
    getAgreementsCenter: vi.fn(),
    listFamilyTemplates: vi.fn(),
    listOfferChecks: vi.fn(),
    listHustleTemplates: vi.fn(),
    createFamilyAgreement: vi.fn(),
    getAgreement: vi.fn(),
    getJournal: vi.fn(),
    getAgreementOps: vi.fn(),
    reportDutyIncident: vi.fn(),
    resolveDutyIncident: vi.fn(),
    openReview: vi.fn(),
    markReview: vi.fn(),
    createReviewPdf: vi.fn(),
    openDispute: vi.fn(),
    decideDispute: vi.fn(),
    createArbiterPdf: vi.fn(),
    confirmUnchanged: vi.fn(),
    confirmFamily: vi.fn(),
  },
}));

const ID = "a-1";
const FAMILY_ID = "a-2";

const SIGNED: AgreementDto = {
  id: ID,
  kind: "PARTNERSHIP",
  title: "Non sexi",
  status: "SIGNED",
  version: 1,
  effectiveFrom: "2026-11-01",
  answers: {
    parties: [
      { id: "P1", name: "Akmal Karimov", role: "sherik", relation: "", isMe: true },
      { id: "P2", name: "Jasur Rahimov", role: "sherik", relation: "", isMe: false },
    ],
    contributions: [],
    duties: [
      {
        id: "d1",
        title: "Yetkazish",
        ownerPartyId: "P2",
        breachClause: "1 kun ichida xabar beradi",
      },
    ],
    hasSchedule: false,
    profitShares: [
      { partyId: "P1", shareBp: 5000 },
      { partyId: "P2", shareBp: 5000 },
    ],
    profitFixedAmount: "",
    profitNotApplicable: null,
    lossText: "Zarar kapitalga mutanosib",
    lossNotApplicable: null,
    custodyLocation: "Umumiy karta",
    keeperPartyId: "P1",
    reviewEveryDays: 30,
    exitNoticeDays: 30,
    exitValuation: "Oxirgi ko'rik bo'yicha",
    exitPayout: "3 oy ichida",
    exitAssets: "",
    exitNotApplicable: null,
    arbiterName: "Shavkat aka",
    arbiterRole: "mahalla oqsoqoli",
    termMonths: 12,
    reviewDate: "2026-12-20",
  },
  completeness: { complete: true, missing: [], errors: [] },
  signatures: [],
  journalCount: 1,
  chainHead: "a".repeat(64),
  chainOk: true,
  canWriteJournal: true,
};

const OPS: AgreementOpsDto = {
  agreementId: ID,
  status: "SIGNED",
  version: 1,
  reviewDate: "2026-12-20",
  reviewDue: true,
  incidents: [],
  reviews: [],
  disputes: [],
  versionNotes: [],
  family: null,
};

const INCIDENT = {
  id: "i-1",
  dutyId: "d1",
  dutyTitle: "Yetkazish",
  breachClause: "1 kun ichida xabar beradi",
  partyId: "P2",
  partyName: "Jasur Rahimov",
  reason: "mashina buzildi",
  proposedFix: "kuryer",
  occurredOn: "2026-12-01",
  resolved: false,
};

const REVIEW = {
  id: "r-1",
  agreementId: ID,
  periodStart: "2026-11-01",
  periodEnd: "2026-12-01",
  entries: [
    {
      seq: 1,
      kind: "OPENING_BALANCE",
      partyId: "P1",
      amount: money(300_000_000, "3 000 000 soʻm"),
      date: "2026-11-01",
      note: null,
      hash: "a".repeat(64),
    },
  ],
  summary: [{ label: "Hissalar", amount: money(300_000_000, "3 000 000 soʻm") }],
  incidents: [INCIDENT],
  chainOk: true,
  chainHead: "a".repeat(64),
  marks: [
    { partyId: "P1", name: "Akmal Karimov", decision: null, comment: null },
    { partyId: "P2", name: "Jasur Rahimov", decision: null, comment: null },
  ],
  complete: false,
  createdOn: "2026-12-01",
};

const CENTER: CenterDto = {
  rows: [
    {
      id: ID,
      kind: "PARTNERSHIP",
      title: "Non sexi",
      status: "SIGNED",
      version: 1,
      reviewDate: "2026-12-20",
      reviewDue: true,
      openIncidents: 1,
      openDisputes: 0,
      chainOk: true,
      familyPending: 0,
    },
    {
      id: FAMILY_ID,
      kind: "FAMILY",
      title: "Uyda kim nima qiladi",
      status: "DRAFT",
      version: 1,
      reviewDate: null,
      reviewDue: false,
      openIncidents: 0,
      openDisputes: 0,
      chainOk: true,
      familyPending: 1,
    },
  ],
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
  vi.mocked(commands.getPartnerships).mockResolvedValue({
    status: "ok",
    data: { items: [], gate: "LOCKED", gateReasons: [] },
  });
  vi.mocked(commands.getAgreementsCenter).mockResolvedValue({ status: "ok", data: CENTER });
  vi.mocked(commands.listFamilyTemplates).mockResolvedValue({
    status: "ok",
    data: [{ id: "FAMILY_CHORES", title: "Uyda kim nima qiladi", description: "Uy ishlari." }],
  });
  vi.mocked(commands.listOfferChecks).mockResolvedValue({ status: "ok", data: { items: [] } });
  vi.mocked(commands.listHustleTemplates).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getAgreement).mockResolvedValue({ status: "ok", data: SIGNED });
  vi.mocked(commands.getJournal).mockResolvedValue({
    status: "ok",
    data: { entries: [], chainOk: true, firstBroken: null },
  });
  vi.mocked(commands.getAgreementOps).mockResolvedValue({ status: "ok", data: OPS });
}

describe("kelishuvlar markazi", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "partnerships", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("jadval filtrlanadi va hodisa band bilan yoziladi", async () => {
    vi.mocked(commands.reportDutyIncident).mockResolvedValue({
      status: "ok",
      data: { ...OPS, incidents: [INCIDENT] },
    });
    render(<App />);
    const table = await screen.findByRole("table", { name: "Kelishuvlar markazi" });
    expect(within(table).getByText("Non sexi")).toBeInTheDocument();
    expect(within(table).getByText("Uyda kim nima qiladi")).toBeInTheDocument();
    expect(within(table).getByText(/yangilash vaqti/)).toBeInTheDocument();
    expect(within(table).getByText("1 tasdiq kutilmoqda")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Holat bo'yicha"), "SIGNED");
    expect(within(table).queryByText("Uyda kim nima qiladi")).not.toBeInTheDocument();

    await user.click(within(table).getByRole("button", { name: "Ochish" }));
    const incidents = await screen.findByRole("heading", {
      name: /Vazifa hodisalari/,
    });
    const card = incidents.closest("section");
    if (card === null) {
      throw new Error("karta topilmadi");
    }
    expect(
      within(card).getByText("Yetkazish: bajarilmasa — 1 kun ichida xabar beradi"),
    ).toBeInTheDocument();
    await user.selectOptions(within(card).getByLabelText("Kim xabar beryapti"), "P2");
    await user.type(within(card).getByLabelText("Sabab"), "mashina buzildi");
    await user.type(within(card).getByLabelText("O'rniga taklif"), "kuryer");
    await user.click(within(card).getByRole("button", { name: "Xabar berish" }));
    expect(commands.reportDutyIncident).toHaveBeenCalledWith({
      agreementId: ID,
      dutyId: "d1",
      partyId: "P2",
      reason: "mashina buzildi",
      proposedFix: "kuryer",
      occurredOn: null,
    });
    expect(await within(card).findByText(/mashina buzildi → kuryer/)).toBeInTheDocument();
  });

  it("ko'rik sessiyasi: belgi va bayonnoma PDF; nizo ochiladi", async () => {
    vi.mocked(commands.getAgreementOps).mockResolvedValue({
      status: "ok",
      data: { ...OPS, reviews: [REVIEW], incidents: [INCIDENT] },
    });
    vi.mocked(commands.markReview).mockResolvedValue({
      status: "ok",
      data: {
        ...OPS,
        reviews: [
          {
            ...REVIEW,
            marks: [
              { partyId: "P1", name: "Akmal Karimov", decision: "AGREE", comment: null },
              { partyId: "P2", name: "Jasur Rahimov", decision: null, comment: null },
            ],
          },
        ],
      },
    });
    vi.mocked(commands.createReviewPdf).mockResolvedValue({
      status: "ok",
      data: "C:\\reports\\korik-1.pdf",
    });
    vi.mocked(commands.openDispute).mockResolvedValue({
      status: "ok",
      data: {
        ...OPS,
        status: "IN_DISPUTE",
        disputes: [
          {
            id: "dsp-1",
            agreementId: ID,
            openedByPartyId: "P2",
            openedByName: "Jasur Rahimov",
            subject: "Xarajat cheki",
            clauses: "6-band",
            claim: "cheklar taqdim etilsin",
            openedOn: "2026-12-01",
            decision: null,
            decidedOn: null,
          },
        ],
      },
    });
    render(<App />);
    const user = userEvent.setup();
    const table = await screen.findByRole("table", { name: "Kelishuvlar markazi" });
    await user.click(first(within(table).getAllByRole("button", { name: "Ochish" })));
    await user.click(await screen.findByRole("button", { name: "Sessiya" }));
    const dialog = await screen.findByRole("dialog", { name: "Hisobni ochiq ko'rish" });
    expect(within(dialog).getByText("Zanjir to'g'ri", { exact: false })).toBeInTheDocument();
    expect(within(dialog).getAllByText("3 000 000 soʻm", { exact: false }).length).toBeGreaterThan(
      0,
    );
    await user.click(first(within(dialog).getAllByRole("button", { name: "Ko'rdim, roziman" })));
    expect(commands.markReview).toHaveBeenCalledWith({
      reviewId: "r-1",
      partyId: "P1",
      decision: "AGREE",
      comment: null,
    });
    expect(await within(dialog).findByText(/Akmal Karimov — ko'rdim, roziman/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Bayonnoma PDF" }));
    expect(await within(dialog).findByText(/korik-1\.pdf/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Yopish" }));

    await user.type(screen.getByLabelText("Mavzu"), "Xarajat cheki");
    await user.type(screen.getByLabelText("Tegishli bandlar"), "6-band");
    await user.type(screen.getByLabelText("Talab"), "cheklar taqdim etilsin");
    await user.click(screen.getByRole("button", { name: "Nizo ochish" }));
    expect(commands.openDispute).toHaveBeenCalledWith({
      agreementId: ID,
      partyId: "P1",
      subject: "Xarajat cheki",
      clauses: "6-band",
      claim: "cheklar taqdim etilsin",
    });
    expect(await screen.findByText(/taqsimot bloklangan/)).toBeInTheDocument();
  });

  it("oilaviy shablon yaratiladi va PIN bilan tasdiqlanadi", async () => {
    const family: AgreementDto = {
      ...SIGNED,
      id: FAMILY_ID,
      kind: "FAMILY",
      title: "Uyda kim nima qiladi",
      status: "DRAFT",
      journalCount: 0,
      chainHead: null,
      canWriteJournal: false,
    };
    vi.mocked(commands.createFamilyAgreement).mockResolvedValue({ status: "ok", data: family });
    vi.mocked(commands.getAgreement).mockResolvedValue({ status: "ok", data: family });
    vi.mocked(commands.getAgreementOps).mockResolvedValue({
      status: "ok",
      data: {
        ...OPS,
        agreementId: FAMILY_ID,
        status: "DRAFT",
        reviewDate: null,
        reviewDue: false,
        family: {
          adults: [{ memberId: "m-1", name: "O'zim", hasPin: true, confirmed: false }],
          complete: false,
        },
      },
    });
    vi.mocked(commands.confirmFamily).mockResolvedValue({
      status: "ok",
      data: {
        ...OPS,
        agreementId: FAMILY_ID,
        status: "SIGNED",
        reviewDate: null,
        reviewDue: false,
        family: {
          adults: [{ memberId: "m-1", name: "O'zim", hasPin: true, confirmed: true }],
          complete: true,
        },
      },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Shablondan yaratish" }));
    expect(commands.createFamilyAgreement).toHaveBeenCalledWith("FAMILY_CHORES");
    const pinField = await screen.findByLabelText("PIN");
    await user.type(pinField, "246813");
    await user.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    expect(commands.confirmFamily).toHaveBeenCalledWith({
      agreementId: FAMILY_ID,
      memberId: "m-1",
      pin: "246813",
    });
    expect(
      await screen.findByText("Barcha kattalar tasdiqladi — kelishuv kuchga kirdi."),
    ).toBeInTheDocument();
  });
});
