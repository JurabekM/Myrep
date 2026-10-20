import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type PartnershipDto, type PartnershipsDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";
import { shareText } from "./PartnershipsCard";

// D12 UI: darvoza yopiq — kapital kirituvchi yaratolmaydi; rozilik; buyout jadvali va to'lov.
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
    createAgreement: vi.fn(),
    getAgreement: vi.fn(),
    getPartnerships: vi.fn(),
    createPartnership: vi.fn(),
    setBuyout: vi.fn(),
    payBuyout: vi.fn(),
    consentPartnership: vi.fn(),
    listMembers: vi.fn(),
  },
}));

const ITEM: PartnershipDto = {
  id: "p-1",
  agreementId: "a-1",
  title: "Tikuv sexi",
  kind: "MUDARABA",
  myRole: "WORKER",
  status: "DRAFT",
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
  issues: ["FAMILY_CONSENT_REQUIRED"],
  gate: "LOCKED",
  gateReasons: ["RESERVE_BELOW_TARGET"],
  consentMember: null,
  consentAt: null,
  gateOverrideReason: null,
  buyout: {
    total: money(900_000_000, "9 000 000 soʻm"),
    months: 3,
    startOn: "2026-11-15",
    paid: money(300_000_000, "3 000 000 soʻm"),
    remaining: money(600_000_000, "6 000 000 soʻm"),
    remainingShareBp: 6667,
    rows: [
      {
        seq: 1,
        dueOn: "2026-11-15",
        amount: money(300_000_000, "3 000 000 soʻm"),
        remainingShareBp: 6667,
        paid: true,
      },
      {
        seq: 2,
        dueOn: "2026-12-15",
        amount: money(300_000_000, "3 000 000 soʻm"),
        remainingShareBp: 3333,
        paid: false,
      },
      {
        seq: 3,
        dueOn: "2027-01-15",
        amount: money(300_000_000, "3 000 000 soʻm"),
        remainingShareBp: 0,
        paid: false,
      },
    ],
  },
};

const DATA: PartnershipsDto = {
  items: [ITEM],
  gate: "LOCKED",
  gateReasons: ["RESERVE_BELOW_TARGET"],
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
  vi.mocked(commands.getPartnerships).mockResolvedValue({ status: "ok", data: DATA });
  vi.mocked(commands.listMembers).mockResolvedValue({
    status: "ok",
    data: [
      { id: "m-1", name: "Anvar", role: "ADULT", hasPin: true },
      { id: "m-2", name: "Bola", role: "CHILD", hasPin: false },
    ],
  });
}

describe("sheriklik", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "partnerships", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("ulush matni", () => {
    expect(shareText(6667)).toBe("66,6 %");
    expect(shareText(10000)).toBe("100,0 %");
  });

  it("buyout jadvali, rozilik muammosi va darvoza yopiqligi ko'rsatiladi; rozilik yuboriladi", async () => {
    vi.mocked(commands.consentPartnership).mockResolvedValue({
      status: "ok",
      data: {
        ...DATA,
        items: [{ ...ITEM, issues: [], consentMember: "Nodira", consentAt: "2026-10-15" }],
      },
    });
    render(<App />);
    const block = await screen.findByRole("region", { name: "Tikuv sexi" });
    expect(within(block).getByText("Oilaviy rozilik kerak")).toBeInTheDocument();
    const table = within(block).getByRole("table", { name: "Bosqichma-bosqich sotib olish" });
    expect(within(table).getAllByText("3 000 000 soʻm")).toHaveLength(3);
    expect(within(block).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "3333");
    expect(screen.getByText(/Darvoza yopiq/)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(within(block).getByLabelText("Rozilik bergan a'zo"), "Nodira");
    await user.click(within(block).getByRole("button", { name: "Rozilikni yozish" }));
    expect(await within(block).findByText(/Nodira/)).toBeInTheDocument();
    expect(commands.consentPartnership).toHaveBeenCalledWith({ id: "p-1", memberName: "Nodira" });
  });

  it("darvoza yopiq bo'lsa kapital kirituvchi ongli chetlab o'tish bilan yaratadi", async () => {
    vi.mocked(commands.createPartnership).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "READINESS_GATE_LOCKED" },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Sheriklik nomi"), "Non sexi");
    await user.selectOptions(screen.getByLabelText("Mening rolim"), "CAPITAL_PROVIDER");
    // Darvoza yopiq: sabab + a'zo + PIN maydonlari chiqadi, tugma sababsiz o'chiq.
    expect(await screen.findByText("Darvoza yopiq — ongli chetlab o'tish")).toBeInTheDocument();
    const create = screen.getByRole("button", { name: "Sheriklik yaratish" });
    expect(create).toBeDisabled();
    await user.type(screen.getByLabelText("Sabab (kamida 20 belgi)"), "Qisqa");
    expect(create).toBeDisabled();
    await user.clear(screen.getByLabelText("Sabab (kamida 20 belgi)"));
    await user.type(
      screen.getByLabelText("Sabab (kamida 20 belgi)"),
      "Ota-onamning do'konini qo'llab-quvvatlash uchun",
    );
    await user.type(screen.getByLabelText("A'zo PIN'i"), "123456");
    expect(create).toBeEnabled();
    // Faqat katta a'zolar ro'yxatda.
    expect(screen.getByRole("option", { name: "Anvar" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Bola" })).not.toBeInTheDocument();
    await user.click(create);
    expect(
      await screen.findByText("Tayyorgarlik darvozasi yopiq: avval 6 oylik zaxira va qarz rejasi"),
    ).toBeInTheDocument();
    expect(commands.createPartnership).toHaveBeenCalledWith({
      title: "Non sexi",
      kind: "MUDARABA",
      myRole: "CAPITAL_PROVIDER",
      gateOverride: {
        memberId: "m-1",
        pin: "123456",
        reason: "Ota-onamning do'konini qo'llab-quvvatlash uchun",
      },
    });
  });

  it("ongli chetlab o'tilgan sheriklik kartasida sabab ko'rinadi", async () => {
    vi.mocked(commands.getPartnerships).mockResolvedValue({
      status: "ok",
      data: {
        ...DATA,
        items: [{ ...ITEM, gateOverrideReason: "Oilaviy do'kon uchun zarur kapital" }],
      },
    });
    render(<App />);
    expect(
      await screen.findByText("Darvoza ongli chetlab o'tilgan: Oilaviy do'kon uchun zarur kapital"),
    ).toBeInTheDocument();
  });
});
