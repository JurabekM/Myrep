import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type CeremoniesDto, type ScenarioDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// D11 UI: stsenariylarni taqqoslash, qarzli reja muhokamasiz tasdiqlanmaydi, PDF. Summalar backend'dan.
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
    getCeremonies: vi.fn(),
    createCeremony: vi.fn(),
    addCeremonyScenario: vi.fn(),
    addCeremonyLine: vi.fn(),
    removeCeremonyLine: vi.fn(),
    discussCeremony: vi.fn(),
    confirmCeremony: vi.fn(),
    setCeremonyGoal: vi.fn(),
    createCeremonyPdf: vi.fn(),
  },
}));

const OSH: ScenarioDto["lines"][number] = {
  id: "l-1",
  name: "Osh",
  quantity: 200,
  unitPrice: money(4_500_000, "45 000 soʻm"),
  funding: "SAVINGS",
  total: money(900_000_000, "9 000 000 soʻm"),
};

const BIG: ScenarioDto = {
  id: "s-big",
  name: "Katta",
  guests: 200,
  days: 3,
  lines: [
    OSH,
    {
      id: "l-2",
      name: "Sarpo",
      quantity: 1,
      unitPrice: money(800_000_000, "8 000 000 soʻm"),
      funding: "DEBT",
      total: money(800_000_000, "8 000 000 soʻm"),
    },
  ],
  total: money(1_700_000_000, "17 000 000 soʻm"),
  debtPart: money(800_000_000, "8 000 000 soʻm"),
  savingsPart: money(900_000_000, "9 000 000 soʻm"),
  familyPart: money(0, "0 soʻm"),
  giftsPart: money(0, "0 soʻm"),
  hasDebt: true,
  payoffMonths: 14,
  monthsOfNeeds: 5,
};

const SMALL: ScenarioDto = {
  ...BIG,
  id: "s-small",
  name: "Ixcham",
  guests: 100,
  days: 1,
  lines: [OSH],
  total: money(450_000_000, "4 500 000 soʻm"),
  debtPart: money(0, "0 soʻm"),
  savingsPart: money(450_000_000, "4 500 000 soʻm"),
  hasDebt: false,
  payoffMonths: null,
  monthsOfNeeds: 1,
};

const CEREMONY: CeremoniesDto["items"][number] = {
  id: "c-1",
  kind: "TOY",
  title: "O'g'limizning to'yi",
  eventOn: "2027-03-12",
  status: "PLANNED",
  familyDiscussed: false,
  chosenScenarioId: null,
  goalName: null,
  goalTarget: null,
  hasDebt: true,
  scenarios: [BIG, SMALL],
};

const DATA: CeremoniesDto = { items: [CEREMONY] };

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
  vi.mocked(commands.getCeremonies).mockResolvedValue({ status: "ok", data: DATA });
}

describe("marosimlar", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "ceremonies", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("stsenariylar yonma-yon taqqoslanadi va qarzli reja muhokamasiz tasdiqlanmaydi", async () => {
    vi.mocked(commands.confirmCeremony).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "FAMILY_DISCUSSION_REQUIRED" },
    });
    render(<App />);
    const table = await screen.findByRole("table", { name: "Taqqoslash" });
    expect(within(table).getByText("17 000 000 soʻm")).toBeInTheDocument();
    expect(within(table).getByText("4 500 000 soʻm")).toBeInTheDocument();
    expect(within(table).getByText("14 oy")).toBeInTheDocument();
    expect(within(table).getByText("5 oylik zarur xarajat")).toBeInTheDocument();
    expect(screen.getByText("Buni qarzsiz qanday o'tkazamiz?")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Sanani tasdiqlash" }));
    expect(
      await screen.findByText("Qarzli reja uchun avval oilaviy muhokama o'tkaziladi"),
    ).toBeInTheDocument();
    expect(commands.confirmCeremony).toHaveBeenCalledWith({ id: "c-1", scenarioId: "s-big" });
  });

  it("muhokama belgilanadi, qator qo'shiladi va PDF yo'li ko'rsatiladi", async () => {
    const discussed: CeremoniesDto = {
      items: [{ ...CEREMONY, familyDiscussed: true }],
    };
    vi.mocked(commands.discussCeremony).mockResolvedValue({ status: "ok", data: discussed });
    vi.mocked(commands.addCeremonyLine).mockResolvedValue({ status: "ok", data: discussed });
    vi.mocked(commands.createCeremonyPdf).mockResolvedValue({
      status: "ok",
      data: "C:\\reports\\smeta-1.pdf",
    });
    render(<App />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Oilaviy muhokama o'tkazildi" }));
    expect(await screen.findByText("Muhokama o'tkazilgan ✓")).toBeInTheDocument();

    const small = screen.getByRole("region", { name: "Ixcham" });
    await user.type(within(small).getByLabelText("Qator nomi"), "Xonanda");
    await user.type(within(small).getByLabelText("Birlik narxi"), "6 000 000");
    await user.selectOptions(within(small).getByLabelText("Manba"), "FAMILY");
    await user.click(within(small).getByRole("button", { name: "Qator qo'shish" }));
    expect(commands.addCeremonyLine).toHaveBeenCalledWith({
      scenarioId: "s-small",
      name: "Xonanda",
      quantity: 1,
      unitPrice: "6 000 000",
      funding: "FAMILY",
    });

    await user.click(within(small).getByRole("button", { name: "Smeta PDF" }));
    expect(await within(small).findByText(/smeta-1\.pdf/)).toBeInTheDocument();
    expect(commands.createCeremonyPdf).toHaveBeenCalledWith("c-1", "s-small");
  });
});
