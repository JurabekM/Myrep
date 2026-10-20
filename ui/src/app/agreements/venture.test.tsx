import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type PartnershipDto,
  type PartnershipsDto,
  type VentureDto,
  commands,
} from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// D13 UI: kassa daftari (yozuv, davr yopish, taqsimot, PDF), taklif detektori, «Hunardan ishga».
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
    listOfferChecks: vi.fn(),
    listHustleTemplates: vi.fn(),
    getAgreementOps: vi.fn(),
    getPartnerships: vi.fn(),
    createPartnership: vi.fn(),
    getVenture: vi.fn(),
    addVentureEntry: vi.fn(),
    attachReceipt: vi.fn(),
    closeVenturePeriod: vi.fn(),
    createPeriodReportPdf: vi.fn(),
    hustlePlan: vi.fn(),
  },
}));

const ITEM: PartnershipDto = {
  id: "p-1",
  agreementId: "a-1",
  title: "Tikuv sexi",
  kind: "MUDARABA",
  myRole: "WORKER",
  status: "SIGNED",
  version: 1,
  parties: [
    {
      partyId: "P1",
      name: "Anvar Karimov",
      role: "mehnat",
      capital: money(0, "0 soʻm"),
      shareBp: 6000,
      isMe: true,
    },
    {
      partyId: "P2",
      name: "Dilshod Rahimov",
      role: "kapital",
      capital: money(500_000_000, "5 000 000 soʻm"),
      shareBp: 4000,
      isMe: false,
    },
  ],
  capitalTotal: money(500_000_000, "5 000 000 soʻm"),
  issues: [],
  gate: "LOCKED",
  gateReasons: [],
  consentMember: "Nodira",
  consentAt: "2026-10-15",
  buyout: null,
  gateOverrideReason: null,
};

const PARTNERSHIPS: PartnershipsDto = { items: [ITEM], gate: "LOCKED", gateReasons: [] };

const VENTURE: VentureDto = {
  partnershipId: "p-1",
  agreementId: "a-1",
  title: "Tikuv sexi",
  status: "SIGNED",
  canWrite: true,
  open: {
    startOn: null,
    income: money(600_000_000, "6 000 000 soʻm"),
    expense: money(250_000_000, "2 500 000 soʻm"),
    net: money(350_000_000, "3 500 000 soʻm"),
    entries: [
      {
        seq: 1,
        kind: "VENTURE_INCOME",
        partyId: "P1",
        amount: money(600_000_000, "6 000 000 soʻm"),
        date: "2026-11-05",
        note: null,
        hash: "a".repeat(64),
      },
    ],
  },
  periods: [],
  spike: false,
  buyoutRemaining: null,
  attachments: [],
};

const CLOSED: VentureDto = {
  ...VENTURE,
  open: { ...VENTURE.open, entries: [], income: money(0, "0 soʻm"), net: money(0, "0 soʻm") },
  periods: [
    {
      id: "per-1",
      startOn: "2026-11-01",
      endOn: "2026-11-30",
      income: money(600_000_000, "6 000 000 soʻm"),
      expense: money(250_000_000, "2 500 000 soʻm"),
      net: money(350_000_000, "3 500 000 soʻm"),
      chainHead: "b".repeat(64),
      closedAt: "2026-12-01",
      forceMajeureNote: null,
      distribution: [
        {
          partyId: "P1",
          name: "Anvar Karimov",
          shareBp: 6000,
          amount: money(210_000_000, "2 100 000 soʻm"),
          buyoutDeduction: money(100_000_000, "1 000 000 soʻm"),
        },
        {
          partyId: "P2",
          name: "Dilshod Rahimov",
          shareBp: 4000,
          amount: money(140_000_000, "1 400 000 soʻm"),
          buyoutDeduction: null,
        },
      ],
    },
  ],
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue({
    name: "Baraka Daftari",
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
  vi.mocked(commands.listOfferChecks).mockResolvedValue({ status: "ok", data: { items: [] } });
  vi.mocked(commands.listHustleTemplates).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getPartnerships).mockResolvedValue({ status: "ok", data: PARTNERSHIPS });
  vi.mocked(commands.getVenture).mockResolvedValue({ status: "ok", data: VENTURE });
}

describe("kassa daftari, detektor va hunardan ishga", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "partnerships", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("yozuv qo'shiladi, davr yopiladi va taqsimot bilan PDF ko'rsatiladi", async () => {
    vi.mocked(commands.addVentureEntry).mockResolvedValue({ status: "ok", data: VENTURE });
    vi.mocked(commands.closeVenturePeriod).mockResolvedValue({ status: "ok", data: CLOSED });
    vi.mocked(commands.createPeriodReportPdf).mockResolvedValue({
      status: "ok",
      data: "C:\\reports\\davr-1.pdf",
    });
    render(<App />);
    const card = await screen.findByRole("region", { name: "Kassa daftari" }, { timeout: 5000 });
    expect(within(card).getByText("3 500 000 soʻm")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.selectOptions(within(card).getByLabelText("Yozuv turi"), "VENTURE_EXPENSE");
    await user.type(within(card).getByLabelText("Summa"), "2 500 000");
    await user.click(within(card).getByRole("button", { name: "Yozish" }));
    expect(commands.addVentureEntry).toHaveBeenCalledWith({
      partnershipId: "p-1",
      kind: "VENTURE_EXPENSE",
      partyId: "P1",
      amount: "2 500 000",
      date: null,
      note: null,
    });

    const end = within(card).getByLabelText("Davr oxiri");
    await user.type(end, "2026-11-30");
    await user.click(within(card).getByRole("button", { name: "Davrni yopish va taqsimlash" }));
    expect(commands.closeVenturePeriod).toHaveBeenCalledWith({
      partnershipId: "p-1",
      endOn: "2026-11-30",
      forceMajeureNote: null,
    });
    expect(await within(card).findByText("2026-11-01 — 2026-11-30")).toBeInTheDocument();
    expect(within(card).getByText(/buyout ayirmasi 1 000 000 soʻm/)).toBeInTheDocument();

    await user.click(within(card).getByRole("button", { name: "Davr hisoboti PDF" }));
    expect(await within(card).findByText(/davr-1\.pdf/)).toBeInTheDocument();
    expect(commands.createPeriodReportPdf).toHaveBeenCalledWith("per-1");
  });

  it("hunardan ishga: uch stsenariy jadvali va sheriklik qoralamasi", async () => {
    vi.mocked(commands.hustlePlan).mockResolvedValue({
      status: "ok",
      data: {
        scenarios: [
          {
            name: "PESSIMISTIC",
            income: money(420_000_000, "4 200 000 soʻm"),
            expense: money(480_000_000, "4 800 000 soʻm"),
            net: money(-60_000_000, "-600 000 soʻm"),
            myNet: money(0, "0 soʻm"),
            paybackMonths: null,
          },
          {
            name: "AVERAGE",
            income: money(600_000_000, "6 000 000 soʻm"),
            expense: money(400_000_000, "4 000 000 soʻm"),
            net: money(200_000_000, "2 000 000 soʻm"),
            myNet: money(120_000_000, "1 200 000 soʻm"),
            paybackMonths: 7,
          },
          {
            name: "OPTIMISTIC",
            income: money(780_000_000, "7 800 000 soʻm"),
            expense: money(360_000_000, "3 600 000 soʻm"),
            net: money(420_000_000, "4 200 000 soʻm"),
            myNet: money(252_000_000, "2 520 000 soʻm"),
            paybackMonths: 4,
          },
        ],
      },
    });
    vi.mocked(commands.createPartnership).mockResolvedValue({
      status: "ok",
      data: { ...PARTNERSHIPS, items: [ITEM, { ...ITEM, id: "p-2", agreementId: "a-2" }] },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Hunar / g'oya"), "Tikuvchilik");
    await user.type(screen.getByLabelText("Boshlang'ich xarajat (CAPEX)"), "8 000 000");
    await user.type(screen.getByLabelText("Oylik kirim"), "6 000 000");
    await user.type(screen.getByLabelText("Oylik xarajat"), "4 000 000");
    await user.clear(screen.getByLabelText("Mening ulushim, %"));
    await user.type(screen.getByLabelText("Mening ulushim, %"), "60");
    await user.click(screen.getByRole("button", { name: "Hisoblash" }));
    const table = await screen.findByRole("table", { name: "Uch stsenariy" });
    expect(within(table).getByText("7 oy")).toBeInTheDocument();
    expect(within(table).getByText("qoplanmaydi")).toBeInTheDocument();
    expect(commands.hustlePlan).toHaveBeenCalledWith({
      capex: "8 000 000",
      monthlyIncome: "6 000 000",
      monthlyExpense: "4 000 000",
      myShareBp: 6000,
    });
    await user.click(screen.getByRole("button", { name: "Sheriklik qoralamasini yaratish" }));
    expect(commands.createPartnership).toHaveBeenCalledWith({
      title: "Tikuvchilik",
      kind: "MUDARABA",
      myRole: "WORKER",
      gateOverride: null,
    });
  });
  it("yozuvga chek rasmi biriktiriladi va miniatyura chiqadi", async () => {
    const image = "data:image/png;base64,iVBORw0KGgo=";
    vi.mocked(commands.attachReceipt).mockResolvedValue({
      status: "ok",
      data: { ...VENTURE, attachments: [{ id: "att-1", seq: 1, image }] },
    });
    render(<App />);
    const card = await screen.findByRole("region", { name: "Kassa daftari" }, { timeout: 5000 });
    expect(within(card).queryByRole("img", { name: "1-yozuv cheki" })).not.toBeInTheDocument();
    const user = userEvent.setup();
    const file = new File([Uint8Array.from([137, 80, 78, 71, 13, 10, 26, 10])], "chek.png", {
      type: "image/png",
    });
    await user.upload(within(card).getByLabelText("1-yozuvga chek rasmi biriktirish"), file);
    const thumb = await within(card).findByRole("img", { name: "1-yozuv cheki" });
    expect(thumb).toHaveAttribute("src", image);
    expect(commands.attachReceipt).toHaveBeenCalledTimes(1);
    const call = vi.mocked(commands.attachReceipt).mock.calls[0]?.[0];
    expect(call?.partnershipId).toBe("p-1");
    expect(call?.seq).toBe(1);
    expect(call?.image.startsWith("data:image/png;base64,")).toBe(true);
  });
});
